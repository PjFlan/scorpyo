import json
from io import IOBase
from typing import MutableSequence


def json_reader(file_handler: IOBase, command_buffer: MutableSequence[str]):
    commands = json.loads(file_handler.read())
    for command in commands:
        command_buffer.append(command)


def plain_reader(file_handler: IOBase, command_buffer: MutableSequence[str]):
    for line in file_handler:
        command_buffer.append(line.strip())
