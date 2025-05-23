import json
import threading
import time
from copy import deepcopy
from unittest.mock import MagicMock

import lib.self_broker
import lib.ttn
import main
import paho.mqtt.client as mqtt
import pytest
import requests

# Project import
from lib.schemas import InvalidFrame
from paho.mqtt.enums import CallbackAPIVersion

from tests.static import DATAFORMAT2_DECODED, EXAMPLE_CONFIG, wait_until


# TODO : Move this one to integration since it uses parse
def test_mqtt_input_frame_not_known(monkeypatch, mock_config):
    """Test : Received MQTT JSON is not a known frame"""

    monkeypatch.setattr(json, "loads", MagicMock(return_value=1))
    monkeypatch.setattr(lib.ttn, "parse_ttn", MagicMock(return_value=None))

    mess = mqtt.MQTTMessage(topic=b"input")
    mess.payload = b"whateverformat"

    with pytest.raises(InvalidFrame):
        main.parse_mqtt(mess)


def test_monitor_page_complete(mock_frame_buffer):
    """Test : Check that monitor page return something"""

    client = main.flask_app.test_client()

    res = client.get("/monitor")
    assert res.status_code == 200

    # Assert that one the frame are found in response HTML
    assert main.frame_buffer["CAFE"][0]["devEUI"] in res.text


@pytest.mark.usefixtures("start_self_broker")
class TestMqttInteg:
    def test_mqtt_output_sending_good(self, mock_config):
        """Check that sending works"""

        main.client_mqtt_output.connect("localhost")

        status_code = main.send_mqtt_message("CAFE", DATAFORMAT2_DECODED)
        assert status_code is True

    def test_init_input_mqtt_success(self):
        """Check that input MQTT successfully connect"""
        main.config["input"]["mqtt"]["enable"] = True
        main.config["input"]["mqtt"]["host"] = "localhost"
        main.config["input"]["mqtt"]["port"] = 1883

        client = main.init_input()
        assert client is not None
        assert wait_until(client.is_connected)

    def test_init_output_mqtt_connected(self):
        """Check that mqtt output is well connected."""

        main.config["output"]["mqtt"]["enable"] = True

        assert not main.client_mqtt_output.is_connected()
        main.init_output()
        assert wait_until(main.client_mqtt_output.is_connected)

    def test_mqtt_output_sending_no_conn(self):
        """Check that sending fails when if no connection"""

        # client is not initialized on purpose (no connection)
        main.client_mqtt_output = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2
        )

        status_code = main.send_mqtt_message("CAFE", DATAFORMAT2_DECODED)
        assert not status_code


def test_init_broker_start_stop(mock_config):
    """Check that broker is started right, then stopped."""
    mosquitto_process = main.init_self_broker()
    assert mosquitto_process is not None
    lib.self_broker.stop_mosquitto(mosquitto_process)
    assert wait_until(lambda: mosquitto_process.poll() is not None)


def test_init_http_server(mock_config):
    """Check that init HTTP works"""

    main.init_http_server()
    time.sleep(0.2)
    assert (
        requests.get(
            f"http://localhost:{main.config['input']['http']['port']}/monitor"
        ).status_code
        == 200
    )

    main.http_server.should_exit = True
    main.flask_thread.join()


def test_launch(monkeypatch):
    """Check that launch func launch every services"""
    monkeypatch.setattr(
        main, "export_config", MagicMock(return_value=deepcopy(EXAMPLE_CONFIG))
    )

    t = threading.Thread(target=main.launch)
    t.start()
    time.sleep(2)
    assert wait_until(lambda: main.js_worker_process is not None)
    assert requests.get(
        f"http://localhost:{main.config['input']['http']['port']}/monitor"
    )

    main.exit_event.set()
    main.http_server.should_exit = True
    main.flask_thread.join()


def test_shutdown(mock_config):
    """Check that input MQTT successfully connect"""

    ######## CONFIG
    main.init_javascript()
    mosquitto_process = main.init_self_broker()
    main.init_input()
    main.init_http_server()
    main.init_output()
    main.init_timeout_checker()

    with pytest.raises(SystemExit) as exc_info:
        main.shutdown(mosquitto_process)

    assert exc_info.value.code == 0
