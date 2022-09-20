from fastapi import FastAPI
from pydantic import BaseModel

from scorpyo import util
from scorpyo.client.client import EngineClient
from scorpyo.registrar import EntityRegistrar


app = FastAPI()


client = None
registrar = None


class Command(BaseModel):
    event: str
    body: dict
    message_id: int
    is_snapshot: bool


def get_registrar():
    global registrar
    if registrar is not None:
        return registrar
    config = util.load_config()
    registrar = EntityRegistrar(config)
    return registrar


def get_client():
    global client
    if client is not None:
        return client
    reg = get_registrar()
    client = EngineClient(reg)
    return client


@app.get("/clubs")
def get_clubs():
    return {"players": []}


@app.get("/players/")
def get_players():
    return {"players": []}


@app.post("/command/")
def add_players(command: Command):
    scorpyo_client = get_client()
    resp = scorpyo_client.on_event_command(command)
    return resp
