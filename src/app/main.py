import ast
import asyncio
import datetime
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import requests
import threading
import time
import logging

from flask import Flask, abort, render_template, jsonify
from asgiref.wsgi import WsgiToAsgi
import uvicorn
import signal

from typing import TypedDict
import js_fetcher  # Import the fetcher script
import base64 as b64
import subprocess
import json
import multiprocessing
import copy

from validate_config import export_config


try:
    config = export_config()
except:
    exit()

match config["log"]["level"]:
    case "debug":
        log_level = logging.DEBUG
    case "info":
        log_level = logging.INFO
    case "warning":
        log_level = logging.WARNING
    case "error":
        log_level = logging.ERROR
    case "critical":
        log_level = logging.CRITICAL
    case _: # Default
        log_level = logging.INFO

logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

client_output = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)


class Frame(TypedDict):
    raw: bytes
    devEUI: str
    fPort: int
    received_time: float

# Global var

# Holding DevEUI - list Frame mapping
frame_buffer: dict[str,list[Frame]] = {}
frame_lock = threading.Lock()

# Valid for MP
FRAGMENT_FPORT = 138
LAST_FRAGMENT_FPORT = 202
DATA_FPORT = 10 # port used to trigger decoder to look like the frame is whole

TIMEOUT_VALUE = config["frame"]["timeout"]
MAX_CHUNKS = config["frame"]["max_chunks"]

exit_event = threading.Event()



####### Javascript interface #######

def start_js_worker():
    """Start the JS worker process and return the queues and process."""
    task_queue = multiprocessing.Queue()
    result_queue = multiprocessing.Queue()
    
    worker_process = multiprocessing.Process(target=js_fetcher.js_worker, args=(task_queue, result_queue))
    worker_process.start()

    return worker_process, task_queue, result_queue

def stop_js_worker():
    # Stop the fetcher process
    task_queue.put("STOP")
    process.join()

def call_js_function(task_queue, result_queue, func_name, *args):
    """Send a JS function call request and get the result."""
    task_queue.put((func_name, args))  # Send function and args
    return result_queue.get()  # Receive result


######## MOSQUITTO #########

# Run mosquitto as a subprocess
def start_mosquitto():
    try:
        # This will start Mosquitto in the background
        process = subprocess.Popen(["mosquitto"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("Self-hosted MQTT broker started.")
        return process
    except Exception as e:
        logger.critical(f"Error starting Self-hosted MQTT Broker: {e}")
        return None

# Stop mosquitto (kill the process)
def stop_mosquitto(process):
    if process:
        process.terminate()
        logger.info("Self-hosted MQTT broker stopped.")


######## FRAME PROCESSING #########
    
# Reassemble frames
def reassemble_frame(devEUI: str):
    global frame_buffer
    if frame_buffer[devEUI]:
        reconstructed_frame = b''.join([frame["raw"] for frame in frame_buffer[devEUI]])
        del frame_buffer[devEUI]
        return reconstructed_frame
    return None



def process_frame(devEUI: str):
    reconstructed_frame = reassemble_frame(devEUI)

    if reconstructed_frame:
        logger.debug(f"Raw frame reassembled for DevEUI {devEUI}: {reconstructed_frame.hex()}")


        # Example: Call myFunction("hello", "world") in JS
        result = call_js_function(task_queue, result_queue, "te_decoder", list(reconstructed_frame),10)
        decoded = ast.literal_eval(node_or_string=str(result))

        logger.info(f"Frame reassembled and decoded for DevEUI {devEUI}: {decoded}")

        if config["output"]["mqtt"]["enable"] == True:
            send_mqtt_message(devEUI, decoded)
        if config["output"]["http"]["enable"] == True:
            send_http_request(decoded)

    else:
        logger.debug("Tried to process a devEUI that didn't have any frame...")

def frame_timeout_checker():
    while exit_event.is_set():
        time.sleep(10)
        with frame_lock:
            logger.debug(f"Frame buffer content : {frame_buffer}")
            to_be_deleted = []
            for devEUI, frame_list in frame_buffer.items():

                if len(frame_list) >= config["frame"]["max_chunks"]:
                    logger.warning(f"Received more than configured {MAX_CHUNKS} chunk from {devEUI}, flushing all its pending fragments...")
                    to_be_deleted.append(devEUI)

                # Check if last frame received is still fresh enough
                if frame_list and (time.time() - frame_list[-1]["received_time"] > (TIMEOUT_VALUE * 3600)):
                    to_be_deleted.append(devEUI)
                    logger.warning(f"Didn't received any new chunk from DevEUI {devEUI} for {TIMEOUT_VALUE} hours, flushing all its pending fragment...")

            # Delete afterwards, as dict cannot be deleted while iterating
            for devEUI in to_be_deleted:
                del frame_buffer[devEUI]

######## LNS Parsing ###########

# Reference : https://www.thethingsindustries.com/docs/integrations/other-integrations/mqtt/
def parse_ttn(chunk) -> Frame:
    fport = chunk["uplink_message"]["f_port"]
    raw_str = chunk["uplink_message"]["frm_payload"]
    raw = b64.b64decode(raw_str)
    dev_eui = chunk["end_device_ids"]["dev_eui"]
    chunk_time = time.time()

    return {"devEUI": dev_eui, "fPort": fport, "raw":raw, "received_time":chunk_time}

def parse_loriot(chunk) -> Frame: # type: ignore
    # TODO
    pass



######### INPUT #########


#### MQTT ####

# MQTT : On message callback
def on_mqtt_message(client, userdata, message: mqtt.MQTTMessage):
    logger.debug(f"Received MQTT msg on topic: {message.topic}, payload :" + str(message.payload))
    
    try:
        chunk = json.loads(message.payload)
    except:
        logger.error(f"Received an invalid message (not json) from topic {message.topic}: {message.payload}")
        return None

    match config["frame"]["lns"]:
        case "ttn":
            frame = parse_ttn(chunk)
        case "loriot":
            frame = parse_loriot(chunk)
        case _:
            logger.critical("This LNS is not supported, exiting...")
            exit()

    # We don't care about non fragmented frames
    if frame["fPort"] in {FRAGMENT_FPORT, LAST_FRAGMENT_FPORT}:
        with frame_lock:
            if frame["devEUI"] in frame_buffer:
                frame_buffer[frame["devEUI"]].append(frame)
            else:
                frame_buffer[frame["devEUI"]] = [frame]

            if frame["fPort"] == LAST_FRAGMENT_FPORT:
                process_frame(frame["devEUI"])



#### HTTP ####

flask_app = Flask(__name__)


def start_flask():
    http_server.run()

@flask_app.route("/input", methods=["POST"])
def receive_http_chunk():
    if config["input"]["http"]["enable"] == False:
        abort(404)

    # chunk = request.json.get("chunk", "")
    # with frame_lock:
    #     frame_buffer.append(chunk)
    #     if len(frame_buffer) >= config["frame"]["max_chunks"]:
    #         process_frame("AA")
    return jsonify({"status": "received"}), 200


@flask_app.route("/monitor", methods=["GET"])
def monitor_buffer():
    table_data = copy.deepcopy(frame_buffer)

    for frame_list in table_data.values():
        for frame in frame_list:
            frame["received_time_str"] = datetime.datetime.fromtimestamp(frame["received_time"]).strftime("%Y-%m-%d %H:%M:%S") # type: ignore
            frame["raw_hex"] =  frame["raw"].hex() # type: ignore


    result = render_template("monitor.html",data=table_data)
    return result, 200

######### OUTPUT #########


#### MQTT ####

# MQTT : Publish
def send_mqtt_message(devEUI: str, frame: dict):
    logger.debug(f"Publishing decoded frame for DevEUI {devEUI} to MQTT")
    client_output.publish(config["output"]["mqtt"]["topic"]+f"/{devEUI}", json.dumps(frame))
    
#### HTTP ####

def send_http_request(frame):
    requests.post(config["output"]["http"]["url"], json={"frame": frame})





# Init self broker
if config["local-broker"]["enable"] == True:
    mosquitto_process = start_mosquitto()

    if mosquitto_process is None:
        exit()
    
    # Wait 1 sec and check if process is still alive
    time.sleep(1)
    if mosquitto_process.poll() is not None:
        logger.error("Self hosted MQTT Broker could not be started : ")
        stdout, stderr = mosquitto_process.communicate()
        print(stderr.decode("utf-8"))




# Init Javascript decoder
process, task_queue, result_queue = start_js_worker()


# Init input
if config["input"]["mqtt"]["enable"] == True:
    mqtt_client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
    mqtt_client.on_message = on_mqtt_message
    try:
        mqtt_client.connect(config["input"]["mqtt"]["host"], config["input"]["mqtt"]["port"])
        logger.info("Input Connected to MQTT Broker !")
    except Exception as e:
        logger.critical("MQTT Input Failed : Failed to connect to the MQTT Broker : " +  str(e))
        exit()
    mqtt_client.subscribe(config["input"]["mqtt"]["topic"])
    mqtt_client.loop_start()



asgi_flask_app = WsgiToAsgi(flask_app)
http_server = uvicorn.Server(uvicorn.Config(asgi_flask_app, host=config["input"]["http"]["host"], port=config["input"]["http"]["port"]))

# flask_thread = threading.Thread(target=lambda: flask_app.run(host=config["input"]["http"]["host"], port=config["input"]["http"]["port"]))
flask_thread = threading.Thread(target=start_flask,  daemon=True)
flask_thread.start()
logger.info("HTTP Server started...")


if config["input"]["http"]["enable"] == False and config["input"]["mqtt"]["enable"] == False:
    logger.critical("At least one input should be selected. Please check config.")
    exit()

# Init output
if config["output"]["mqtt"]["enable"] == True:
    try:
        client_output.connect(config["output"]["mqtt"]["host"], config["output"]["mqtt"]["port"])
        logger.info("Output Connected to MQTT Broker !")
    except Exception as e:
        logger.critical("MQTT Output Failed : Failed to connect to the MQTT Broker : " +  str(e))
        exit()
if config["output"]["http"]["enable"] == True:
    # TODO Implement HTTP
    pass



# Timeout checker thread
timeout_thread = threading.Thread(target=frame_timeout_checker, daemon=True)
timeout_thread.start()



def frame_checker():
    while True:
        time.sleep(2)
        for devEUI, frame_list in frame_buffer.items():
            for frame in frame_list:
                if frame["fPort"] == LAST_FRAGMENT_FPORT:
                    process_frame(devEUI)




logger.info("Application started and waiting for input...")

async def main():
    # Keep the main thread alive
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            stop_js_worker()

            if config["local-broker"]["enable"] == True:
                stop_mosquitto(mosquitto_process) # type: ignore

            exit_event.set() 

            time.sleep(1) # Allow time for all thread to end properly
            exit(0)


if __name__ == "__main__":
    asyncio.run(main())