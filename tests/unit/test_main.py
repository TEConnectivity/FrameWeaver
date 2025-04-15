import json
import logging
import time
from typing import Any, Callable
from unittest.mock import MagicMock
import pytest
from lib.schemas import Frame, InvalidFrame, InvalidJSON
from pytest import MonkeyPatch
import main
import lib.js_fetcher
import lib.ttn
import threading
import paho.mqtt.client as mqtt
import requests
import lib.self_broker
from copy import deepcopy

EXAMPLE_CONFIG = {
    "input": {
        "mqtt": {
            "enable": True,
            "host": "localhost",
            "port": 1883,
            "topic": "input",
            "auth": {
                "username": "username",
                "password": "password"
            }
        },
        "http": {
            "enable": False,
            "host": "0.0.0.0",
            "port": 8080
        }
    },
    "output": {
        "mqtt": {
            "enable": True,
            "host": "localhost",
            "port": 1883,
            "topic": "output"
        },
        "http": {
            "enable": False,
            "url": "http://example.com"
        }
    },
    "local-broker": {
        "enable": True
    },
    "frame": {
        "max_chunks": 15,
        "timeout": 48,
        "lns": "ttn"
    },
    "log": {
        "level": "debug"
    }
}
DATAFORMAT2_HEX = "152f000408630b3e81000c000000060000180000000400010000d0001c0003c000d0001b00038000d0001a8003600142002880051800cd0019c0033c00cd0019b0033800cd0019a8033600"
DATAFORMAT2_BYTES = bytes.fromhex(DATAFORMAT2_HEX)
DATAFORMAT2_DECODED = {
 "data": {
  "size": 75,
  "devtype": {
   "Platform": "Platform_21",
   "Sensor": "Vibration 3-axis",
   "Wireless": "BLE/LoRaWAN",
   "Output": "N/A",
   "Unit": "g"
  },
  "cnt": 4,
  "devstat": [
   "PrelPhase"
  ],
  "bat": 99,
  "temp": "28.78",
  "vibration_information": {
   "frame_format": 2,
   "rotating_mode": 0,
   "axis": [
    "z"
   ]
  },
  "preset_id": 0,
  "bw_mode": 12,
  "vibration_data": {
   "spectrum_rms": 0,
   "time_p2p": 6,
   "velocity": 0,
   "peak_cnt": 24,
   "peaks": [
    {
     "bin_index": 0,
     "frequency": 0,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 1,
     "frequency": 10,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 2,
     "frequency": 20,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 13,
     "frequency": 130,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 14,
     "frequency": 140,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 15,
     "frequency": 150,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 26,
     "frequency": 260,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 27,
     "frequency": 270,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 28,
     "frequency": 280,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 52,
     "frequency": 520,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 53,
     "frequency": 530,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 54,
     "frequency": 540,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 161,
     "frequency": 1610,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 162,
     "frequency": 1620,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 163,
     "frequency": 1630,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 205,
     "frequency": 2050,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 206,
     "frequency": 2060,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 207,
     "frequency": 2070,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 410,
     "frequency": 4100,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 411,
     "frequency": 4110,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 412,
     "frequency": 4120,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 820,
     "frequency": 8200,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 821,
     "frequency": 8210,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    },
    {
     "bin_index": 822,
     "frequency": 8220,
     "magnitude_compressed": 0,
     "magnitude_rms": 0
    }
   ]
  }
 },
 "errors": []
}
FRAME_EXAMPLE: Frame = {"raw": b"152f000408630b3e81000c000000060000180000000400010000", "devEUI":"CAFE","fPort":138,"received_time":10}

####### FIXTURE


@pytest.fixture
def mock_config():
    main.config.update(deepcopy(EXAMPLE_CONFIG))
    # print("mockbefore",main.config)
    # deep_update(main.config,EXAMPLE_CONFIG)
    # print("ref",EXAMPLE_CONFIG)
    # print("mock",main.config)

    

@pytest.fixture
def mock_patch_reassemble(request: pytest.FixtureRequest, monkeypatch: MonkeyPatch):
    """Mock frame reassembled. Can be parametrized."""

    marker = request.node.get_closest_marker("mock_patch_reassemble")
    if marker:
        result = marker.args[0]
    else:
        result = DATAFORMAT2_BYTES
    # Data format 2

    monkeypatch.setattr(main, 'reassemble_frame', MagicMock(return_value=result))

@pytest.fixture
def mock_frame_buffer() -> dict[str, list[Frame]]:
    # Prepare mock data in frame_buffer
    main.frame_buffer.clear()  # Clear any existing data
    main.frame_buffer["CAFE"] = [{"raw": b"152f000408630b3e81000c000000060000180000000400010000", "devEUI":"CAFE","fPort":138,"received_time":10},
                          {"raw": b"d0001c0003c000d0001b00038000d0001a800360014200288005", "devEUI":"CAFE","fPort":138,"received_time":20},
                          {"raw": b"1800cd0019c0033c00cd0019b0033800cd0019a8033600", "devEUI":"CAFE","fPort":202,"received_time":30}]

    main.frame_buffer["BB"] = [{"raw": b"152f000408630b3e81000c000000060000180000000400010000", "devEUI":"CAFE","fPort":138,"received_time":10}]
    return main.frame_buffer

@pytest.fixture
def mock_patch_jsdecode(monkeypatch: MonkeyPatch):
    # Mock the js_fetcher.decode method
         
    monkeypatch.setattr(lib.js_fetcher, 'decode', MagicMock(return_value=DATAFORMAT2_DECODED))


@pytest.fixture(scope="module")
def start_self_broker():
    # Mock the js_fetcher.decode method
         
    process = lib.self_broker.start_mosquitto()
    time.sleep(1)
    yield
    lib.self_broker.stop_mosquitto(process=process)



######## TEST


@pytest.mark.usefixtures("mock_config")
class TestReassembleFrame:
    def test_reassemble(self, mock_frame_buffer):
        res = main.reassemble_frame("CAFE") # return b'152...'
        assert res is not None
        assert res.decode() == DATAFORMAT2_HEX
    def test_reassemble_no_frame(self):
        """Frame buffer is empty"""
        res = main.reassemble_frame("CAFE")
        assert res is None

@pytest.mark.usefixtures("mock_config")
class TestProcessFrame:
    @pytest.mark.mock_patch_reassemble(DATAFORMAT2_BYTES)
    def test_process_frame_decoded(self, mock_patch_jsdecode,mock_patch_reassemble):
        assert main.process_frame("CAFE") == DATAFORMAT2_DECODED

    @pytest.mark.mock_patch_reassemble(None)
    def test_process_frame_empty(self, mock_patch_jsdecode,mock_patch_reassemble):
        assert main.process_frame("CAFE") == -1





@pytest.mark.usefixtures("mock_frame_buffer","mock_config")
class TestTimeoutChecker:

    @pytest.mark.parametrize("dynamic_config", [{},
                                                                    {"frame":{"max_chunks":1,"timeout": 1000000000000,"lns": "ttn"}}
                                                                    ])
    def test_deletion(self,monkeypatch, dynamic_config):
        """Test : deletion cuz timeout, cuz max chunk"""
        main.config.update(dynamic_config)

        monkeypatch.setattr(time, 'sleep', MagicMock(return_value=None))
        
        assert "CAFE" in main.frame_buffer
        
        t = threading.Thread(target=main.frame_timeout_checker)
        t.start()
        main.exit_event.set()
        t.join()

        assert "CAFE" not in main.frame_buffer

    def test_no_del(self,monkeypatch):
        """Test : no deletion"""
        main.config.update( {"frame":{"max_chunks":10,"timeout": 1000000000000,"lns": "ttn"}})

        monkeypatch.setattr(time, 'sleep', MagicMock(return_value=None))
        
        assert "CAFE" in main.frame_buffer
        
        t = threading.Thread(target=main.frame_timeout_checker)
        t.start()
        main.exit_event.set()
        t.join()

        assert "CAFE" in main.frame_buffer

                                                                           


@pytest.mark.usefixtures("mock_config")
class TestMQTTInput:

    def test_parse_mqtt(self,monkeypatch):
        """Test : Received MQTT Chunk is not JSON"""
        
        mess = mqtt.MQTTMessage(topic=b"input")
        mess.payload = b"badformat"

        with pytest.raises(InvalidJSON):
            main.parse_mqtt( mess)


    # TODO : Move this one to integration since it uses parse
    def test_mqtt_input_frame_not_known(self,monkeypatch):
        """Test : Received MQTT JSON is not a known frame"""

        monkeypatch.setattr(json, 'loads', MagicMock(return_value=1))
        monkeypatch.setattr(lib.ttn, 'parse_ttn', MagicMock(return_value=None))

        
        mess = mqtt.MQTTMessage(topic=b"input")
        mess.payload = b"whateverformat"
        
        with pytest.raises(InvalidFrame):
            main.parse_mqtt( mess)



    def test_mqtt_input_valid_frame(self,monkeypatch):
        """Test : Received MQTT JSON is a known frame"""

        monkeypatch.setattr(json, 'loads', MagicMock(return_value=1))
        monkeypatch.setattr(main, 'parse_ttn', MagicMock(return_value=FRAME_EXAMPLE))

        mess = mqtt.MQTTMessage(topic=b"input")
        mess.payload = b"whateverformat" # function is patched anyway
        
        assert FRAME_EXAMPLE["devEUI"] not in main.frame_buffer

        main.on_mqtt_message(None,None, mess)

        assert FRAME_EXAMPLE["devEUI"] in main.frame_buffer

    def test_mqtt_input_valid_frame_wrong_fport(self,monkeypatch):
        """Test : Received MQTT JSON is not a known frame"""

        monkeypatch.setattr(json, 'loads', MagicMock(return_value=1))
        wrong_fport = FRAME_EXAMPLE
        wrong_fport["fPort"] = 1
        monkeypatch.setattr(main, 'parse_ttn', MagicMock(return_value=wrong_fport))

        mess = mqtt.MQTTMessage(topic=b"input")
        mess.payload = b"whateverformat"
        
        assert FRAME_EXAMPLE["devEUI"] not in main.frame_buffer

        main.on_mqtt_message(None,None, mess)

        assert FRAME_EXAMPLE["devEUI"] not in main.frame_buffer






@pytest.mark.usefixtures("mock_config")
class TestFlaskApp:

    def test_monitor_page_mocked(self,monkeypatch):
        """Test : Check that monitor page return something"""

        HTML_EXPECTED_VALUE = "test_html"
        monkeypatch.setattr(main, 'render_template', MagicMock(return_value=HTML_EXPECTED_VALUE))


        client = main.flask_app.test_client()

        res = client.get("/monitor")
        assert res.status_code == 200
        assert res.text == HTML_EXPECTED_VALUE

    def test_monitor_page_complete(self,mock_frame_buffer):
        """Test : Check that monitor page return something"""
        # TODO : Move to integration test

        client = main.flask_app.test_client()

        res = client.get("/monitor")
        assert res.status_code == 200

        # Assert that one the frame are found in response HTML
        assert main.frame_buffer["CAFE"][0]["devEUI"] in res.text



@pytest.mark.usefixtures("mock_config", "start_self_broker")
class TestMQTTOutput:

    def test_mqtt_output_sending_no_conn(self):
        """Check that sending fails when if no connection"""

        # client has not been initialized
        status_code = main.send_mqtt_message("CAFE", DATAFORMAT2_DECODED)
        assert status_code == False

    def test_mqtt_output_sending_good(self):
        """Check that sending works"""

        # TODO : Move integration

        main.client_mqtt_output.connect("localhost")

        status_code = main.send_mqtt_message("CAFE", DATAFORMAT2_DECODED)
        assert status_code == True



class TestLoadConfig:

    def test_load_config_ok(self,monkeypatch):
        """Check that config successfuly loaded"""

        monkeypatch.setattr(main, 'export_config', MagicMock(return_value=deepcopy(EXAMPLE_CONFIG)))
        assert main.load_config() == EXAMPLE_CONFIG

    def test_load_config_nofile(self):
        """Check that program exit when config fail parsing"""

        # config file cannot be found for example in our case
        with pytest.raises(SystemExit):
            main.load_config()


@pytest.mark.parametrize("dynamic_config", [{"log":{"level":"info"}},
                                                                {"log":{"level":"warning"}}
                                                                    ])
def test_init_logging(mock_config, dynamic_config):
    """Check log level is correctly initialized depending on config"""

    main.config.update(dynamic_config)

    main.init_logging()
    if dynamic_config["log"]["level"] == "info":
        assert main.logger.level == logging.INFO
    elif dynamic_config["log"]["level"] == "warning":
        assert main.logger.level == logging.WARNING


def test_init_javascript(mock_config):
    """Check that JS Worker is properly started"""

    assert (main.js_worker_process, main.task_queue, main.result_queue) == (None, None, None)
    main.init_javascript()
    assert (main.js_worker_process, main.task_queue, main.result_queue) != (None, None, None)
    lib.js_fetcher.stop_js_worker(main.task_queue,main.js_worker_process)



class TestInitSelfBroker:
    def test_init_broker_start_stop(self, mock_config):
        """Check that broker is started right, then stopped."""
        # TODO : Move to integration
        mosquitto_process = main.init_self_broker()
        assert mosquitto_process != None
        lib.self_broker.stop_mosquitto(mosquitto_process)
        assert wait_until(lambda: mosquitto_process.poll() is not None)

    def test_init_broker_disabled(self, mock_config):
        """Check that broker is not started if config is false"""
        main.config.update({"local-broker":{"enable":False}})

        mosquitto_process = main.init_self_broker()
        assert mosquitto_process == None

        
@pytest.mark.usefixtures("mock_config")
class TestInitInput:
    def test_init_input_noselection(self):
        """Check that program exit when no input is selected in conf."""

        main.config["input"]["http"]["enable"] = False
        main.config["input"]["mqtt"]["enable"] = False

        with pytest.raises(SystemExit):
            main.init_input()

    def test_init_input_mqtt_failed(self):
        """Check that input MQTT fail to init if host is not present"""

        main.config["input"]["mqtt"]["enable"] = True
        main.config["input"]["mqtt"]["host"] = "localhost"
        main.config["input"]["mqtt"]["port"] = 1500

        with pytest.raises(SystemExit):
            main.init_input()

    def test_init_input_mqtt_success(self, start_self_broker):
        """Check that input MQTT successfully connect"""
        # TODO : Move to integration
        main.config["input"]["mqtt"]["enable"] = True
        main.config["input"]["mqtt"]["host"] = "localhost"
        main.config["input"]["mqtt"]["port"] = 1883

        client = main.init_input()
        assert client is not None
        assert wait_until(client.is_connected)


      
@pytest.mark.usefixtures("mock_config")
class TestInitOutput:
    def test_init_output(self):
        """Check that program exit when no output is selected in conf."""

        main.config["output"]["http"]["enable"] = False
        main.config["output"]["mqtt"]["enable"] = False

        with pytest.raises(SystemExit):
            main.init_output()

    def test_init_output_mqtt_connected(self,start_self_broker):
        """Check that mqtt output is well connected."""

        main.config["output"]["mqtt"]["enable"] = True

        assert main.client_mqtt_output.is_connected() == False
        main.init_output()
        assert wait_until(main.client_mqtt_output.is_connected)

    def test_init_output_mqtt_noconnection(self):
        """Check that mqtt output cannot connect."""

        main.config["output"]["mqtt"]["enable"] = True
        main.config["input"]["mqtt"]["host"] = "localhost"
        main.config["output"]["mqtt"]["port"] = 1500

        with pytest.raises(SystemExit):
            main.init_output()
 



def test_init_http_server():
    """Check that input MQTT successfully connect"""
    # TODO : Move to integration

    main.init_http_server()
    res = main.flask_app.test_client().get("/monitor")
    assert res.status_code == 200


def test_launch(monkeypatch):
    """Check that input MQTT successfully connect"""
    # TODO : Move to integration
    monkeypatch.setattr(main, 'export_config', MagicMock(return_value=deepcopy(EXAMPLE_CONFIG)))

    t = threading.Thread(target=main.launch)
    t.start()
    time.sleep(2)
    assert wait_until(lambda: main.js_worker_process is not None)
    assert requests.get(f'http://localhost:{main.config["input"]["http"]["port"]}/monitor')
    
    main.exit_event.set()



def test_shutdown(mock_config):
    """Check that input MQTT successfully connect"""
    # TODO : Move to integration

    print("TOOOO", main.config)


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






def wait_until(
    func: Callable[[], Any],
    expected: Any = True,
    timeout: float = 5.0,
    interval: float = 0.1
) -> bool:
    """
    Wait until `func()` returns the expected value or timeout is reached.

    Args:
        func (Callable[[], Any]): Function to call repeatedly.
        expected (Any): The value to wait for. Default is True.
        timeout (float): Max seconds to wait.
        interval (float): Delay between calls in seconds.

    Returns:
        bool: True if func() returned expected before timeout, else False.
    """
    start = time.time()
    while time.time() - start < timeout:
        result = func()
        if result == expected:
            return True
        time.sleep(interval)
    return False


