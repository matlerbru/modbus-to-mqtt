import yaml
import pydantic
import enum
import typing
import logging


class NoConfigurationError(BaseException):
    pass


class Log_level(enum.Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"


class Mqtt(pydantic.BaseModel):
    address: str
    port: int
    repeat_time: int
    main_topic: str = "modbus-to-mqtt"


class FieldbusRead(pydantic.BaseModel):
    type: str
    start: int
    count: int


class Fieldbus(pydantic.BaseModel):
    address: str
    read: list[FieldbusRead]
    scan_time: int
    long_press_time: int


class Config(pydantic.BaseModel):
    log_level: Log_level
    mqtt: Mqtt
    fieldbus: Fieldbus


def config_loader(paths: list[str]) -> Config:
    for path in paths:
        try:
            with open(path, "r") as stream:
                parsed_yaml = typing.cast(dict, yaml.safe_load(stream))
                logging.info(f"Loading configfile: {path}")
                return Config.model_validate(parsed_yaml)
        except yaml.scanner.ScannerError as e:
            logging.error(f"Unable to parse file {path}: {str(e)}.")
        except yaml.scanner.ScannerError:
            pass
    else:
        raise Exception("Not able to load configfile.")


config = config_loader(["config.yaml", "/modbus-to-mqtt/config.yaml"])
