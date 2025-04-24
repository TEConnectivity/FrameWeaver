# File used to benchmark app with a lot of requests
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import json
import time
from threading import Thread



def on_message(client, userdata, message: mqtt.MQTTMessage) -> None:
    decoded = json.loads(message.payload)
    print("message, ", decoded)

    pass
    

DEVEUI = "4200000000000000"
client_mqtt = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
client_mqtt.on_message = on_message
status_code = client_mqtt.connect("localhost", 1883)
client_mqtt.subscribe("output/topic/#")
client_mqtt.loop_start()


msg1 = json.load(open("payload/payload_ttn_fragment1.json"))
last = json.load(open("payload/payload_ttn_fragment_last.json"))


def scenario1():
    # SCENARIO 1 : Lot of proper request

    FRAME_NUMBER = 100
    for i in range(FRAME_NUMBER):
        # Change devEUI dynamically

        msg1["end_device_ids"]["dev_eui"] = "1Dev" +str(i) 
        last["end_device_ids"]["dev_eui"] = "1Dev" +str(i) 

        res = client_mqtt.publish(payload=json.dumps(msg1), topic="test")
        res.wait_for_publish()


        res = client_mqtt.publish(payload=json.dumps(last), topic="test")
        res.wait_for_publish()


def scenario2():
    # SCENARIO 2 : lot of pending fragments

    FRAME_NUMBER = 10 *1000
    for i in range(FRAME_NUMBER):
        # Change devEUI dynamically

        msg1["end_device_ids"]["dev_eui"] = "2Dev" +str(i) 

        res = client_mqtt.publish(payload=json.dumps(msg1), topic="test")
        res.wait_for_publish()

def scenario3():

    FRAME_NUMBER = 100
    THREAD_COUNT = 10
    def spam(dev_prefix):
        for i in range(FRAME_NUMBER):
            msg1["end_device_ids"]["dev_eui"] = f"{dev_prefix}{i}"
            client_mqtt.publish(payload=json.dumps(msg1), topic="test").wait_for_publish()

    threads = [Thread(target=spam, args=(f"concurrent{i}_",)) for i in range(THREAD_COUNT)]

    for t in threads: t.start()
    for t in threads: t.join()



scenario3()


# Finish sending
time.sleep(1)
print("Benchmark done")
