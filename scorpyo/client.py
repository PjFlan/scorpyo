from scorpyo.engine import MatchEngine, EngineState
from scorpyo.registrar import EntityRegistrar


# This module is a skeleton for now but will flesh out with the gory details
class MatchClient:
    def __init__(self, engine: MatchEngine):
        self.engine = engine
        self.registrar = EntityRegistrar()
        self.sources = []

    def read(self):
        # go to various input sources and query for new data
        # there should be a hierarchy of which gets read first (e.g. entity before
        # events) but should also be away for our sources to forward new data
        pass

    def parse(self):
        # interpret new data and prepare it to be sent to the engine or otherwise
        pass

    def register_source(self, source: "InputSource"):
        self.sources.append(source)

    def on_entity_message(self):
        # prepare message and all appropriate registrar method
        pass

    def on_event_message(self):
        # pass to the engine for processing and confirm the engine acked the message
        assert (
            self.engine.state == EngineState.RUNNNING
        ), "engine is not running, cannot accept new messages"
        pass

    @property
    def is_match_ready(self):
        # do we have appropriate entity data to begin a match with
        # or should we continue reading for more
        # if we try to interpret an event message while this is still false
        # then we have an issue
        pass


class InputSource:

    # Mostly a wrapper around various sources of match messages (files, command line,
    # web etc.)
    def __init__(self):
        self.messages = []
        self.is_connected = False

    def query(self):
        # do we have new data available to pass to the reader
        pass

    def connect(self):
        # open a connection to the underlying stream
        pass

    def read(self):
        # read from the stream until the internal buffer is full and cache data that
        # has yet to be read upstream
        pass
