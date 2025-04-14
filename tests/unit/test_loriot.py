import time
from unittest.mock import MagicMock
import pytest
from lib.schemas import Frame
from pytest import MonkeyPatch
import main
from lib.loriot import parse_loriot
import json
import os



frame = {"raw": bytes.fromhex("152f000408630b3e81000c000000060000180000000400010000d0001c0003c000d0001b00038000"), "devEUI":"BCAF9100004DA780","fPort":138,"received_time":10}
raw_msg = json.load(open("payload/payload_loriot_fragment1.json"))


def test_parse_loriot(monkeypatch: MonkeyPatch):   
    monkeypatch.setattr(time, 'time', MagicMock(return_value=10)) # patch time right now

    assert parse_loriot(raw_msg) == frame


def test_parse_loriot_weird_frame(monkeypatch: MonkeyPatch):   
    monkeypatch.setattr(time, 'time', MagicMock(return_value=10)) # patch time right now

    assert parse_loriot({"weird":"frame"}) == None

