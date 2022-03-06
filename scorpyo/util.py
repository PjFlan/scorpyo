import time

import configparser


def load_config(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config


def try_int_convert(input):
    try:
        return int(input)
    except ValueError:
        return input


def identity(input):
    return input


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
