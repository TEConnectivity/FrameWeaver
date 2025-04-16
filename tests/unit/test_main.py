import json
import logging
import time
from paho.mqtt.enums import CallbackAPIVersion
from typing import Any, Callable
from unittest.mock import MagicMock
import pytest
import threading
import paho.mqtt.client as mqtt
import requests
from copy import deepcopy
import multiprocessing

from  tests.static import *

# Project import
import main
from lib.schemas import InvalidJSON
import lib.js_fetcher

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

    # Cleaning
    main.js_worker_process, main.task_queue, main.result_queue = None, None, None
    
    assert (main.js_worker_process, main.task_queue, main.result_queue) == (None, None, None)
    main.init_javascript()
    
    assert main.js_worker_process is not None
    assert main.task_queue is not None
    assert main.result_queue is not None
    lib.js_fetcher.stop_js_worker(main.task_queue,main.js_worker_process)



class TestInitSelfBroker:


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




      
@pytest.mark.usefixtures("mock_config")
class TestInitOutput:
    def test_init_output(self):
        """Check that program exit when no output is selected in conf."""

        main.config["output"]["http"]["enable"] = False
        main.config["output"]["mqtt"]["enable"] = False

        with pytest.raises(SystemExit):
            main.init_output()



    def test_init_output_mqtt_noconnection(self):
        """Check that mqtt output cannot connect."""

        main.config["output"]["mqtt"]["enable"] = True
        main.config["input"]["mqtt"]["host"] = "localhost"
        main.config["output"]["mqtt"]["port"] = 1500

        with pytest.raises(SystemExit):
            main.init_output()
 





