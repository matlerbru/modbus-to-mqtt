import logging
import paho.mqtt.client as mqtt

from configuration import config


class Mqtt:

    def __init__(self) -> None:
        self._paho = mqtt.Client()

    def connect(self) -> None:
        self._paho.connect(config.mqtt.address, config.mqtt.port)
        logged = False
        while True:
            try:
                self._paho.connect(config.mqtt.address, config.mqtt.port)
                logging.info("Connected to mqtt broker")
                break
            except OSError:
                if not logged:
                    logging.error("Failed to connect to mqtt broker")
                    logged = True

    def publish(self, topic: str, message: str) -> None:
        status = self._paho.publish(topic.lower(), message)
        if status[0] != 0:
            logging.critical("Failed to send message, error code: " + str(status[0]))

    def on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            logging.info("Mqtt connected, error code: " + str(rc))
        else:
            logging.error("Failed to connect to mqtt broker, error code: " + str(rc))
            exit()

    def on_disconnect(self, client, userdata, rc) -> None:
        logging.error("Disconnected from mqtt broker, error code: " + str(rc))
        self.connect()
