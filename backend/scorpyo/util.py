import logging
import time

from configparser import ConfigParser
from typing import Optional

LOGGER = logging.getLogger("scorpyo")
DEFAULT_CONFIG_DIR = "/Users/padraicflanagan/.config/scorpyo/scorpyo.ini"


logging.basicConfig(level=logging.INFO)


def load_config(config_source: Optional[str] = None):
    if not config_source:
        config_source = DEFAULT_CONFIG_DIR
    if isinstance(config_source, str):
        config = ConfigParser()
        config.read(config_source)
        return config
    elif isinstance(config_source, ConfigParser):
        return config_source
    else:
        raise ValueError("unknown config type passed to client: ", config_source)


def try_int_convert(value):
    try:
        return int(value)
    except ValueError:
        return value


def identity(value):
    return value


def switch_strike(striker, non_striker):
    temp = non_striker
    new_non_striker = striker
    new_striker = temp
    return new_striker, new_non_striker


def get_current_time() -> time:
    return time.time()


def balls_to_overs(balls: int) -> str:
    balls_in_over = balls % 6
    overs_completed = balls // 6
    return f"{overs_completed}.{balls_in_over}"
