import json
import time
import pytest
import requests

# Project import
import main
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from tests.static import EXAMPLE_CONFIG, wait_until, DATAFORMAT2_DECODED

@pytest.mark.usefixtures("start_system")
class TestSystem:
    def test_system_monitor(self,start_system):
        """Check that launch func launch every services"""

        assert requests.get(f'http://localhost:{main.config["input"]["http"]["port"]}/monitor').status_code == 200
        

    def test_frame_accepted(self,start_system):
        """Check that a TTN frame is accepted and seen in monitor page"""
        
        frame_received = None

        def on_message(client, userdata, message: mqtt.MQTTMessage) -> None:
            nonlocal frame_received
            decoded = json.loads(message.payload)

            # It means we recieved a true decoded frame
            if "preset_id" in decoded["data"]:
                frame_received = decoded
            pass
            
        DEVEUI = "4200000000000000"
        client_mqtt = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
        client_mqtt.on_message = on_message
        status_code = client_mqtt.connect("localhost", EXAMPLE_CONFIG["output"]["mqtt"]["port"])
        client_mqtt.subscribe(f"output/{DEVEUI}")
        client_mqtt.loop_start()


        assert status_code == mqtt.MQTT_ERR_SUCCESS


        assert DEVEUI not in main.frame_buffer

        # Fragment 1
        raw_msg = json.load(open("payload/payload_ttn_fragment1.json"))
        client_mqtt.publish(payload=json.dumps(raw_msg), topic=EXAMPLE_CONFIG["input"]["mqtt"]["topic"])

        
        assert wait_until(lambda: DEVEUI in main.frame_buffer)
        assert len(main.frame_buffer[DEVEUI]) == 1

        # Fragment 2
        raw_msg = json.load(open("payload/payload_ttn_fragment_last.json"))
        client_mqtt.publish(payload=json.dumps(raw_msg), topic=EXAMPLE_CONFIG["input"]["mqtt"]["topic"])
        

        # No longer fragmented
        assert wait_until(lambda: DEVEUI not in main.frame_buffer)

        # We received the answer, decoded
        assert wait_until(lambda: frame_received == DATAFORMAT2_DECODED)


 
        


    def test_stop_system(self,start_system):
        """Check that launch func launch every services"""

        with pytest.raises(SystemExit):
            main.shutdown(start_system)






