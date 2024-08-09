import logging
import time

import sys
from configuration import config
import modbus


def setup_logging(level: int) -> None:
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s.%(msecs)03d %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=level,
    )


def main() -> None:
    setup_logging(logging.getLevelNamesMapping()[config.log_level.value])

    logging.info("Service started")

    fieldbus = modbus.Fieldbus(config.fieldbus.address)
    fieldbus.start()

    try:
        while True:
            time.sleep(1000)
    except Exception as e:
        logging.fatal(e)


if __name__ == "__main__":
    try:

        LOGNAME = "modbus-to-mqtt.log"
        main()
    except KeyboardInterrupt:
        pass
