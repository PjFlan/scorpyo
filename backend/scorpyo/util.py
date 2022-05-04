import logging
import time

import configparser


LOGGER = logging.getLogger("scorpyo")
logging.basicConfig(level=logging.INFO)


EVENT_ERROR_SENTINEL = "EVENT_ERROR"


def load_config(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config


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
