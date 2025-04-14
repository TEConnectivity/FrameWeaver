from typing import TypedDict


class Frame(TypedDict):
    raw: bytes
    devEUI: str
    fPort: int
    received_time: float

class InvalidJSON(Exception):
    pass


class InvalidFrame(Exception):
    pass

class JSWorkerFail(Exception):
    pass