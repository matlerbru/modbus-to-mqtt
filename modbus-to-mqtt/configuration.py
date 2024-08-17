import os
import yaml
import pydantic
import enum
import typing


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

if os.path.isfile("config.yaml"):
    with open("config.yaml", "r") as stream:
        parsed_yaml = typing.cast(dict, yaml.safe_load(stream))
        conf = Config.model_validate(parsed_yaml)

elif os.path.isfile("/modbus-to-mqtt/config.yaml"):

    with open("/modbus-to-mqtt/config.yaml", "r") as venv_stream:
        try:
            parsed_yaml = typing.cast(dict, yaml.safe_load(venv_stream))
            conf = Config.model_validate(parsed_yaml)

        except yaml.YAMLError:
            pass
else:
    raise NoConfigurationError

config = conf
