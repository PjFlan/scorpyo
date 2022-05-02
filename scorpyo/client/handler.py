import abc
import json
import os
import logging
from collections import deque

from websocket_server import WebsocketServer, WebSocketHandler

from scorpyo.client.cli_nodes import (
    process_node_input,
    prepare_nested_payload,
    check_triggers,
    file_input_reader,
    get_starting_event_nodes,
    create_nodes,
)
from scorpyo.client.reader import json_reader, plain_reader
from scorpyo.entity import EntityType
from scorpyo.event import EventType
from scorpyo.registrar import EntityRegistrar


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ClientHandler(abc.ABC):
    """Mostly a wrapper around various sources of match commands (files, command line,
    web, database etc.)"""

    def __init__(self, config: dict, registrar: EntityRegistrar):
        try:
            self.root_dir = config["CLIENT"]["root_dir"]
        except KeyError:
            self.root_dir = "../"
        self.registrar = registrar
        self.is_connected = False
        self.command_buffer: deque = deque()

    @property
    def is_open(self):
        return False

    def query(self):
        """clear the current cache"""
        while self.command_buffer:
            yield self.command_buffer.popleft()

    @abc.abstractmethod
    def connect(self):
        """open a connection to the underlying source"""
        pass

    @abc.abstractmethod
    def close(self):
        """close the connection to the underlying source"""
        pass

    @abc.abstractmethod
    def read(self):
        """read from the source until the internal buffer is full and cache data that
        has yet to be processed upstream"""
        pass

    @abc.abstractmethod
    def on_message(self, message: dict):
        pass

    @property
    def has_data(self):
        return self.command_buffer


class FileHandler(ClientHandler):
    def __init__(self, config: dict, registrar: EntityRegistrar):
        super().__init__(config, registrar)
        self.config = config["FILE_HANDLER"]
        self.url: str = os.path.join(self.root_dir, self.config["url"])
        self.reader_func = {"json": json_reader, "plain": plain_reader}[
            self.config["reader"]
        ]
        self.file_handler = None

    @property
    def is_open(self):
        return not self.file_handler.closed

    def connect(self):
        try:
            self.file_handler = open(self.url, "r")
        except IOError:
            raise ConnectionError(f"error connecting to file source {self.url}")

    def close(self):
        if self.is_open:
            self.file_handler.close()

    def read(self):
        self.reader_func(self.file_handler, self.command_buffer)
        self.close()

    def on_message(self, message: dict):
        print(json.dumps(message, indent=4))


class CommandLineHandler(ClientHandler):
    def __init__(self, config, registrar: EntityRegistrar):
        super().__init__(config, registrar)
        self.config = config["COMMAND_LINE_HANDLER"]
        self.active = True
        self.event_nodes = create_nodes()
        self.starting_nodes_map = get_starting_event_nodes(self.event_nodes)
        self.input_reader = input

    @property
    def is_open(self):
        return self.active

    def connect(self):
        self.active = True
        self.on_connected()

    def on_connected(self):
        if self.config["use_file"]:
            file_source = os.path.join(self.root_dir, self.config["input_source"])
            with open(file_source) as fh:
                lines = [x.strip() for x in fh]
            self.input_reader = file_input_reader(lines)
        print(
            "\nWelcome to the scorpyo CLI. Type 'help' for a list of valid "
            "instructions, or 'quit' to exit."
        )

    def close(self):
        self.active = False

    def read(self):
        next_command = self.input_reader("\n> ")
        if next_command == "help":
            self.show_help()
            return
        elif next_command == "quit":
            self.close()
            return
        elif next_command in {"player", "team"}:
            entity_type = EntityType[next_command.upper()]
            self.show_entities(entity_type)
            return
        else:
            try:
                event_type = EventType(next_command)
            except AttributeError:
                print("Not a valid command. Type 'help' for usage instructions.")
                return
        node_tree = deque()
        body = {}
        starting_node = self.starting_nodes_map.get(event_type)
        if starting_node:
            node_tree.append(starting_node)
        active_triggers = set()
        while True:
            try:
                node = node_tree.pop()
            except IndexError:
                break
            if node.triggered_by and not node.triggered_by.issubset(active_triggers):
                continue
            if node.is_list:
                input_value = []
                print(node.prompt)
                raw_val = self.input_reader("> ")
                while raw_val != "F":
                    value = process_node_input(node, raw_val)
                    input_value.append(value)
                    raw_val = self.input_reader("> ")
            else:
                input_value = process_node_input(node, self.input_reader(node.prompt))
            if input_value is None:
                # inform the user of mistake and go again with the same node
                node_tree.append(node)
                continue
            if "." in node.payload_key:
                payload_section, payload_key = prepare_nested_payload(
                    body, node.payload_key
                )
            else:
                payload_section, payload_key = body, node.payload_key
            payload_value = input_value
            payload_section[payload_key] = payload_value
            if len(node.next_nodes) > 0:
                node_tree.extend(node.next_nodes)
            check_triggers(node, payload_value, active_triggers)
        command = {"event": event_type.value, "body": body}
        self.command_buffer.append(command)

    def on_message(self, message: dict):
        print(json.dumps(message, indent=4))

    def show_help(self):
        print(
            "Enter an event command using one of the following shortcodes ("
            "or type 'quit' to exit the client). To get all entities of a certain type "
            "and their unique ID, enter the entity type e.g. 'player' or 'team'."
        )
        for event in EventType:
            print(f"{event.value}={event.name}")

    def show_entities(self, entity_type: EntityType):
        for ent in self.registrar.get_all_of_type(entity_type):
            print(f"{ent.unique_id} - {ent.name}")


class WSHandler(ClientHandler):
    def __init__(self, config, registrar: EntityRegistrar):
        super().__init__(config, registrar)
        self.config = config["WEB_SOCKET_HANDLER"]
        self.host = self.config["host"]
        self.port = int(self.config["port"])
        self._server = None
        logger.setLevel(logging.INFO)
        logger.info("setting up web socket handler")

    def connect(self):
        self._server = self._setup_server()
        self._server.run_forever(threaded=True)
        self.on_connected()

    def on_connected(self):
        logger.info(f"connected to engine at {self.host}:{self.port}")
        self._server.set_fn_message_received(self._on_socket_message)

    def is_open(self):
        return self._server is not None

    def close(self):
        logger.info("web socket server shut down")
        self._server.shutdown_gracefully()
        self._server = None

    def read(self):
        # nothing to do as new messages are automatically queued by the socket handler
        pass

    def on_message(self, message: dict):
        logger.info("Sending reply from engine to clients")
        self._server.send_message_to_all(json.dumps(message))

    def _setup_server(self) -> WebsocketServer:
        server = WebsocketServer(host=self.host, port=self.port, loglevel=logging.INFO)
        return server

    def _on_socket_message(self, client: dict, server: WebSocketHandler, msg: str):
        logger.info("Received message from client: " + msg)
        json_msg = json.loads(msg)
        self.command_buffer.append(json_msg)
