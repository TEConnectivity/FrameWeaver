import time
from unittest.mock import MagicMock
import pytest
from lib.schemas import Frame
from pytest import MonkeyPatch
import main
from main import frame_buffer, config, exit_event
import lib.js_fetcher
import threading

example_config = {
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
            "host": "localhost.local",
            "port": 1883,
            "topic": "output"
        },
        "http": {
            "enable": False,
            "url": "http://example.com"
        }
    },
    "local-broker": {
        "enable": False
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

hex_df2 = "152f000408630b3e81000c000000060000180000000400010000d0001c0003c000d0001b00038000d0001a8003600142002880051800cd0019c0033c00cd0019b0033800cd0019a8033600"
bytes_df2 = bytes.fromhex(hex_df2)
decoded_df2 = {
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


####### FIXTURE


@pytest.fixture
def mock_config(request: pytest.FixtureRequest):
    config.update(example_config)

    marker = request.node.get_closest_marker("mock_config_value")
    if marker:
        upd = marker.args[0]
        config.update(upd)

@pytest.fixture
def mock_patch_reassemble(request: pytest.FixtureRequest, monkeypatch: MonkeyPatch):
    """Mock frame reassembled. Can be parametrized."""

    print(request.node.own_markers)

    marker = request.node.get_closest_marker("mock_patch_reassemble")
    if marker:
        result = marker.args[0]
    else:
        result = bytes_df2
    # Data format 2

    monkeypatch.setattr(main, 'reassemble_frame', MagicMock(return_value=result))

@pytest.fixture
def mock_frame_buffer() -> dict[str, list[Frame]]:
    # Prepare mock data in frame_buffer
    frame_buffer.clear()  # Clear any existing data
    frame_buffer["AA"] = [{"raw": b"152f000408630b3e81000c000000060000180000000400010000", "devEUI":"AA","fPort":138,"received_time":10},
                          {"raw": b"d0001c0003c000d0001b00038000d0001a800360014200288005", "devEUI":"AA","fPort":138,"received_time":20},
                          {"raw": b"1800cd0019c0033c00cd0019b0033800cd0019a8033600", "devEUI":"AA","fPort":202,"received_time":30}]

    frame_buffer["BB"] = [{"raw": b"152f000408630b3e81000c000000060000180000000400010000", "devEUI":"AA","fPort":138,"received_time":10}]
    return frame_buffer

@pytest.fixture
def mock_patch_jsdecode(monkeypatch: MonkeyPatch):
    # Mock the js_fetcher.decode method
         
    monkeypatch.setattr(lib.js_fetcher, 'decode', MagicMock(return_value=decoded_df2))

######## TEST


@pytest.mark.usefixtures("mock_config")
class TestReassembleFrame:
    def test_reassemble(self, mock_frame_buffer):
        res = main.reassemble_frame("AA") # return b'152...'
        assert res is not None
        assert res.decode() == hex_df2
    def test_reassemble_no_frame(self):
        """Frame buffer is empty"""
        res = main.reassemble_frame("AA")
        assert res is None

@pytest.mark.usefixtures("mock_config")
class TestProcessFrame:
    @pytest.mark.mock_patch_reassemble(bytes_df2)
    def test_process_frame_decoded(self, mock_patch_jsdecode,mock_patch_reassemble):
        assert main.process_frame("AA") == decoded_df2

    @pytest.mark.mock_patch_reassemble(None)
    def test_process_frame_empty(self, mock_patch_jsdecode,mock_patch_reassemble):
        assert main.process_frame("AA") == -1





@pytest.mark.usefixtures("mock_frame_buffer","mock_config")
class TestTimeoutChecker:

    @pytest.mark.parametrize("dynamic_config", [{},
                                                                    {"frame":{"max_chunks":1,"timeout": 1000000000000,"lns": "ttn"}}
                                                                    ])
    def test_deletion(self,monkeypatch, dynamic_config):
        """Test : deletion cuz timeout, cuz max chunk"""
        config.update(dynamic_config)

        monkeypatch.setattr(time, 'sleep', MagicMock(return_value=None))
        
        assert "AA" in frame_buffer
        
        t = threading.Thread(target=main.frame_timeout_checker)
        t.start()
        exit_event.set()
        t.join()

        assert "AA" not in frame_buffer

    def test_no_del(self,monkeypatch):
        """Test : no deletion"""
        config.update( {"frame":{"max_chunks":10,"timeout": 1000000000000,"lns": "ttn"}})

        monkeypatch.setattr(time, 'sleep', MagicMock(return_value=None))
        
        assert "AA" in frame_buffer
        
        t = threading.Thread(target=main.frame_timeout_checker)
        t.start()
        exit_event.set()
        t.join()

        assert "AA" in frame_buffer

                                                                           




def test_my_function(monkeypatch: MonkeyPatch):
    
    monkeypatch.setattr(main, 'load_config', MagicMock(return_value = example_config))
    assert main.load_config() == example_config
