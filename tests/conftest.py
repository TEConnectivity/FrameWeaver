import time
import os
import sys
from copy import deepcopy
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

# Ajouter le dossier src/app au sys.path pour les imports relatifs
sys.path.insert(
    0, os.path.abspath(path=os.path.join(os.path.dirname(__file__), "..", "src/app"))
)

# Put the interpreter at the right place to resolve imports
os.chdir(os.path.dirname(__file__))

os.environ["ENV"] = "test"

import lib.js_fetcher
import lib.self_broker
import main
from main import exit_event, frame_buffer
from .static import EXAMPLE_CONFIG, DATAFORMAT2_BYTES, Frame, DATAFORMAT2_DECODED, is_mosquitto_process_alive, kill_existing_mosquitto, wait_until


@pytest.fixture(autouse=True)
def clear_frame_buffer():
    """
    Vide le frame_buffer avant chaque test pour garantir un état propre.
    """
    frame_buffer.clear()
    yield


@pytest.fixture(autouse=True)
def exit_event_unset():
    """
    Clear le thread event stop avant chaque test pour garantir un état propre.
    """
    exit_event.clear()
    yield


@pytest.fixture
def mock_config():
    main.config.update(deepcopy(EXAMPLE_CONFIG))


@pytest.fixture
def mock_patch_reassemble(request: pytest.FixtureRequest, monkeypatch: MonkeyPatch):
    """Mock frame reassembled. Can be parametrized."""

    marker = request.node.get_closest_marker("mock_patch_reassemble")
    if marker:
        result = marker.args[0]
    else:
        result = DATAFORMAT2_BYTES
    # Data format 2

    monkeypatch.setattr(main, "reassemble_frame", MagicMock(return_value=result))


@pytest.fixture
def mock_frame_buffer() -> dict[str, list[Frame]]:
    # Prepare mock data in frame_buffer
    main.frame_buffer.clear()  # Clear any existing data
    main.frame_buffer["CAFE"] = [
        {
            "raw": b"152f000408630b3e81000c000000060000180000000400010000",
            "devEUI": "CAFE",
            "fPort": 138,
            "received_time": 10,
        },
        {
            "raw": b"d0001c0003c000d0001b00038000d0001a800360014200288005",
            "devEUI": "CAFE",
            "fPort": 138,
            "received_time": 20,
        },
        {
            "raw": b"1800cd0019c0033c00cd0019b0033800cd0019a8033600",
            "devEUI": "CAFE",
            "fPort": 202,
            "received_time": 30,
        },
    ]

    main.frame_buffer["BB"] = [
        {
            "raw": b"152f000408630b3e81000c000000060000180000000400010000",
            "devEUI": "CAFE",
            "fPort": 138,
            "received_time": 10,
        }
    ]
    return main.frame_buffer


@pytest.fixture
def mock_patch_jsdecode(monkeypatch: MonkeyPatch):
    # Mock the js_fetcher.decode method

    monkeypatch.setattr(
        lib.js_fetcher, "decode", MagicMock(return_value=DATAFORMAT2_DECODED)
    )


@pytest.fixture(scope="class")
def start_self_broker():

    kill_existing_mosquitto()
    process = lib.self_broker.start_mosquitto()
    if process is None:
        pytest.fail("Failed to start the Mosquitto broker. Aborting test setup.")
        exit(1)

    time.sleep(2)

    yield

    lib.self_broker.stop_mosquitto(process=process)
    wait_until(is_mosquitto_process_alive)


@pytest.fixture(scope="class")
def monkeymodule():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="class")
def start_system(monkeymodule):
    monkeymodule.setattr(
        main, "export_config", MagicMock(return_value=deepcopy(EXAMPLE_CONFIG))
    )  # type: ignore

    main.load_config()
    main.init_javascript()
    mosquitto_process = main.init_self_broker()
    main.init_input()
    main.init_http_server()
    main.init_output()
    main.init_timeout_checker()

    # server started
    time.sleep(1)

    yield mosquitto_process

    with pytest.raises(SystemExit):
        main.shutdown(mosquitto_process)