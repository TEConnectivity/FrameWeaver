from unittest.mock import MagicMock
import pytest
from lib.schemas import Frame
from pytest import MonkeyPatch
import main
from main import frame_buffer, config
import lib.js_fetcher

test_config = {
            "log": {"level": "debug"},
            "frame": {
                "timeout": 0.001,
                "max_chunks": 10,
                "lns": "ttn"
            },
            "output": {
                "mqtt": {"enable": False},
                "http": {"enable": False}
            },
            "input": {
                "mqtt": {"enable": False},
                "http": {"enable": False}
            },
            "local-broker": {"enable": False}
        }

test_decoded = {"test": "titi"}

@pytest.fixture
def mock_config():
    config.update(test_config)




@pytest.fixture
def mock_frame_buffer() -> dict[str, list[Frame]]:
    # Prepare mock data in frame_buffer
    frame_buffer.clear()  # Clear any existing data
    frame_buffer["AA"] = [{"raw": b"AABB", "devEUI":"AA","fPort":138,"received_time":10000}]  # Example mock data
    return frame_buffer

@pytest.fixture
def mock_decode(monkeypatch):
    # Mock the js_fetcher.decode method
         
    monkeypatch.setattr(lib.js_fetcher, 'decode', MagicMock(return_value=test_decoded))


def test_reassemble(monkeypatch: MonkeyPatch, mock_frame_buffer, mock_decode, mock_config):
    assert main.process_frame("AA") == test_decoded

def test_my_function(monkeypatch: MonkeyPatch):
    
    monkeypatch.setattr(main, 'load_config', MagicMock(return_value = config))
    assert main.load_config() == test_config
