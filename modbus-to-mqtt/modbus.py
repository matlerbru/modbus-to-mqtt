import collections
import json
import logging
import math
import threading
import time
import functools
import mqtt

from pyModbusTCP.client import ModbusClient
from configuration import config


class MqttPublisher:

    def __init__(self) -> None:
        self._mqtt = mqtt.Mqtt()
        self._mqtt.connect()
        self._status: dict[str, str | int] = {}
        self._main_topic = config.mqtt.main_topic

        self._thread_resend_status()

    def _thread_resend_status(self) -> None:
        threading.Timer(
            (config.mqtt.repeat_time / 60) / 1000, self._thread_resend_status
        ).start()
        if len(self._status) > 0:
            logging.debug(f"Sending message: {json.dumps(self._status)}.")
            self._mqtt.publish(f"{self._main_topic}/status", json.dumps(self._status))
            logging.debug(f"Message send: {json.dumps(self._status)}.")

    def update_status(
        self, message: dict[str, str | int | bool], log: bool = True
    ) -> None:
        if log:
            logging.info(f"Status changed: {json.dumps(message)}.")
        self._status.update(message)

    def publish_change(self, topic: str, message: dict[str, str | int | bool]) -> None:
        logging.info(f"Sending message: {json.dumps(message)}.")
        self._mqtt.publish(f"{self._main_topic}/{topic}", json.dumps(message))
        logging.debug(f"Message send: {json.dumps(message)}.")


class Coil:

    def __init__(
        self,
        start: int,
        count: int,
        modbus_client: ModbusClient,
        mqtt_publisher: MqttPublisher,
    ) -> None:
        self.previous_values: collections.deque = collections.deque(
            maxlen=self.get_long_press_scans()
        )
        self._last_send_message = 0
        self._started = False
        self._start = start
        self._count = count
        self._modbus_client = modbus_client
        self._mqtt_publisher = mqtt_publisher
        self._counter = 0

    def evaluate(self) -> None:

        data = self._read()
        self._counter += 1

        try:
            if self.get_long_press_scans() != len(self.previous_values):
                self.previous_values = collections.deque(
                    list(self.previous_values), maxlen=self.get_long_press_scans()
                )

            if not self._started:
                logging.info(f"Module is polling.")
                self._started = True

            val = [(1 if n else 0) for n in data]

            val = [1]

            self.previous_values.append(val)
            for index in range(len(data)):
                previous_values = "".join(
                    [str(pv[index]) for pv in self.previous_values]
                )

                # long click
                if "1" * (self.get_long_press_scans()) in previous_values:
                    self._mqtt_publisher.publish_change(
                        "output", {"address": self._start + index, "press": "long"}
                    )
                    self._last_send_message = self._counter
                    self.queue_reset_button(index)
                    continue

                # click
                if "10" in previous_values:
                    if self._counter > self._last_send_message + 1:
                        self._mqtt_publisher.publish_change(
                            "output", {"address": self._start + index, "press": "short"}
                        )
                    self._last_send_message = self._counter
                    self.queue_reset_button(index)
                    continue
        except Exception as e:
            logging.info(e)

    def _read(self) -> list[bool]:
        return self._modbus_client.read_coils(self._start, self._count)

    @functools.cache
    def get_long_press_scans(self) -> int:
        return math.ceil(config.fieldbus.long_press_time / config.fieldbus.scan_time)

    def queue_reset_button(self, index: int) -> None:
        for previous_value in self.previous_values:
            del previous_value[index]
            previous_value.insert(index, "0")


class Fieldbus:

    def __init__(self, ip: str) -> None:

        self._run_time_min = 100000.0
        self._run_time_max = 0.0

        self._stop_flag = False
        self._connected = False
        self._overtime_count = 0.0
        self.scan_count = 0
        self.online = False

        self.ip = ip
        self.client = ModbusClient(
            host=self.ip, auto_open=True, auto_close=True, timeout=1
        )

        self.mqtt_publisher = MqttPublisher()

        self.mqtt_publisher.update_status({"overtime_count": 0})

        self.scan_time = config.fieldbus.scan_time
        self.mqtt_publisher.update_status({"scan_time": self.scan_time})
        self.mqtt_publisher.update_status(
            {"long_click_time": config.fieldbus.long_press_time}
        )

        self._blocks: list[Coil] = []
        for read in config.fieldbus.read:
            if read.type == "coil":
                coil = Coil(read.start, read.count, self.client, self.mqtt_publisher)
                self._blocks.append(coil)

    def start(self) -> None:
        self._thread_function()

    def stop(self) -> None:
        self._stop_flag = True

    def _thread_function(self) -> None:
        threading.Timer(self.scan_time / 1000, self._thread_function).start()
        try:
            self.scan_count += 1
            start_time = time.perf_counter()

            for block in self._blocks:
                try:
                    block.evaluate()
                    self.online = True
                except Exception:
                    self.online = False

            if self._stop_flag:
                self._stop_flag = False
                return
            stop_time = time.perf_counter()
            self.run_time((stop_time - start_time) * 1000)

        except Exception as e:
            logging.error(f"Failed scan: {e}")

    def run_time(self, time: float) -> None:
        time = float("{:.2f}".format(time))

        if time > self.scan_time:
            self._overtime_count += 1
            self.mqtt_publisher.update_status({"overtime_count": self._overtime_count})

        if time > self._run_time_max:
            self._run_time_max = time
            self.mqtt_publisher.update_status({"highest_scan_time": self._run_time_max})

        if time < self._run_time_min:
            self._run_time_min = time
            self.mqtt_publisher.update_status({"lowest_scan_time": self._run_time_min})

        self.mqtt_publisher.update_status({"scans": self.scan_count}, log=False)

    @property
    def online(self) -> bool:
        return self._connected

    @online.setter
    def online(self, connected: bool) -> None:

        if connected != self._connected:
            self.mqtt_publisher.update_status({"online": connected})
            self._connected = connected
