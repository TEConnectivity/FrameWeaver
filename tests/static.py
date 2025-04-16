
import time
from typing import Any, Callable

from lib.schemas import Frame


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


