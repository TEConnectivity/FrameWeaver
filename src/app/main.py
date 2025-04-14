import ast
import datetime
import os
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import requests
import threading
import time
import logging

from flask import Flask, abort, render_template, jsonify
from asgiref.wsgi import WsgiToAsgi
import uvicorn
import json
import copy

# Project import
from lib.ttn import parse_ttn
from lib.loriot import parse_loriot
from lib.schemas import Frame, InvalidFrame, InvalidJSON, JSWorkerFail
from lib.validate_config import export_config
import lib.js_fetcher as js_fetcher  # Import the fetcher script
import lib.self_broker as self_broker


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = {} # Will be loaded after
js_worker_process, task_queue, result_queue = None, None, None



client_mqtt_output = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)




# Global var

# Holding DevEUI - list Frame mapping
frame_buffer: dict[str,list[Frame]] = {}
frame_lock = threading.Lock()
exit_event = threading.Event()


# CONST

# Valid for MP
FRAGMENT_FPORT = 138
LAST_FRAGMENT_FPORT = 202
DATA_FPORT = 10 # port used to trigger decoder to look like the frame is whole

TIMEOUT_CHECK_INTERVAL = 10 #second

# Map MQTT error name with enum value
MQTT_ERROR_NAMES = {v: k for k, v in vars(mqtt).items() if k.startswith("MQTT_ERR_")}



def get_timeout():
    return config["frame"]["timeout"]

def get_max_chunk():
    return config["frame"]["max_chunks"]



######## FRAME PROCESSING #########
    
# Reassemble frames
def reassemble_frame(devEUI: str) -> bytes | None:
    global frame_buffer
    if devEUI in frame_buffer:
        reconstructed_frame = b''.join([frame["raw"] for frame in frame_buffer[devEUI]])
        del frame_buffer[devEUI]
        return reconstructed_frame
    return None



def process_frame(devEUI: str):
    reconstructed_frame = reassemble_frame(devEUI)

    if reconstructed_frame:
        logger.debug(f"Raw frame reassembled for DevEUI {devEUI}: {reconstructed_frame.hex()}")

        decoded = js_fetcher.decode(task_queue,result_queue,reconstructed_frame,10)

        logger.info(f"Frame reassembled and decoded for DevEUI {devEUI}: {decoded}")

        if config["output"]["mqtt"]["enable"] == True:
            send_mqtt_message(devEUI, decoded)
        if config["output"]["http"]["enable"] == True:
            send_http_request(decoded)
        
        return decoded
    
    else:
        logger.debug("Tried to process a devEUI that didn't have any frame...")
        return -1

def frame_timeout_checker():
    """ Threaded function checking that a frame is fresh, and number of chunk is not too high  """
    while not exit_event.is_set():
        time.sleep(TIMEOUT_CHECK_INTERVAL)
        with frame_lock:
            logger.debug(f"Frame buffer content : {frame_buffer}")
            to_be_deleted = []
            for devEUI, frame_list in frame_buffer.items():

                if len(frame_list) > config["frame"]["max_chunks"]:
                    logger.warning(f"Received more than configured {get_max_chunk()} chunk from {devEUI}, flushing all its pending fragments...")
                    to_be_deleted.append(devEUI)

                # Check if last frame received is still fresh enough
                if frame_list and (time.time() - frame_list[-1]["received_time"] > (get_timeout() * 3600)):
                    to_be_deleted.append(devEUI)
                    logger.warning(f"Didn't received any new chunk from DevEUI {devEUI} for {get_timeout()} hours, flushing all its pending fragment...")

            # Delete afterwards, as dict cannot be deleted while iterating
            for devEUI in to_be_deleted:
                del frame_buffer[devEUI]


######### INPUT #########


#### MQTT ####

# Loriot : directly output on the topic itself, no subtopic used.
# TTN : Need to subscribe to v3/{application id}@{tenant id}/devices/{device id}/up


# MQTT : On message callback
def on_mqtt_message(client, userdata, message: mqtt.MQTTMessage) -> None:
    logger.debug(f"Received MQTT msg on topic: {message.topic}, payload :" + str(message.payload))
    
    try:
        frame = parse_mqtt(message)
    except:
        return None

    # We don't care about non fragmented frames
    if frame["fPort"] in {FRAGMENT_FPORT, LAST_FRAGMENT_FPORT}:
        with frame_lock:
            if frame["devEUI"] in frame_buffer:
                frame_buffer[frame["devEUI"]].append(frame)
            else:
                frame_buffer[frame["devEUI"]] = [frame]

            if frame["fPort"] == LAST_FRAGMENT_FPORT:
                process_frame(frame["devEUI"])
    else:
        logger.debug("Received MQTT frame with non-interesting fPort")


def parse_mqtt(message: mqtt.MQTTMessage):
    try:
        chunk = json.loads(message.payload)
    except:
        logger.error(f"Received an invalid message (not json) from topic {message.topic}: {message.payload}")
        raise InvalidJSON

    match config["frame"]["lns"]:
        case "ttn":
            frame = parse_ttn(chunk)
        case "loriot":
            frame = parse_loriot(chunk)
        case _:
            logger.critical("This LNS is not supported, check config.yaml, exiting...")
            exit()

    if not frame:
        logger.debug("Could not decode the MQTT received.")
        raise InvalidFrame
    
    return frame


#### HTTP ####

flask_app = Flask(__name__)



def start_flask(http_server):
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
    res = client_mqtt_output.publish(config["output"]["mqtt"]["topic"]+f"/{devEUI}", json.dumps(frame))
    if res.rc == mqtt.MQTT_ERR_SUCCESS:
        return True
    else:
        logger.error(f"Failed to publish MQTT message: {MQTT_ERROR_NAMES.get(res.rc)}")
        return False
    
#### HTTP ####

def send_http_request(frame):
    requests.post(config["output"]["http"]["url"], json={"frame": frame})



###### INIT

def load_config() -> dict:
    global config 

    try:
    # Run validation
        if os.getenv("ENV") == "dev":
            config_file = "config_dev.yaml"
        else:
            config_file = "config.yaml"
        config = export_config(config_file)
        return config
    except Exception as e:
        logger.error("Fail to parse config.yaml, verify if file exist and its content")
        exit()


def launch():

    ######## CONFIG
    load_config()
    init_logging()
    init_javascript()
    mosquitto_process = init_self_broker()
    init_input()
    init_http_server()
    init_output()
    init_timeout_checker()
        

    logger.info("Application started and waiting for input...")
    

    # Keep the main thread alive
    while not exit_event.is_set():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            shutdown(mosquitto_process)




def shutdown(mosquitto_process):
    logger.info("Shutting down...")

    if js_worker_process is not None and task_queue is not None:
        js_fetcher.stop_js_worker(task_queue, js_worker_process)

    if config["local-broker"]["enable"] == True:
        self_broker.stop_mosquitto(mosquitto_process) # type: ignore

    exit_event.set() 

    time.sleep(1) # Allow time for all thread to end properly
    exit(0)

def init_timeout_checker():
    timeout_thread = threading.Thread(target=frame_timeout_checker, daemon=True) 
    timeout_thread.start()

def init_output():
    if config["output"]["mqtt"]["enable"] == True:
        try:
            client_mqtt_output.connect(config["output"]["mqtt"]["host"], config["output"]["mqtt"]["port"])
            logger.info("Output Connected to MQTT Broker !")
        except Exception as e:
            logger.critical("MQTT Output Failed : Failed to connect to the MQTT Broker : " +  str(e))
            exit()
    if config["output"]["http"]["enable"] == True:
        # TODO Implement HTTP
        pass

def init_http_server():
    asgi_flask_app = WsgiToAsgi(flask_app)
    http_server = uvicorn.Server(uvicorn.Config(asgi_flask_app, host=config["input"]["http"]["host"], port=config["input"]["http"]["port"]))
    flask_thread = threading.Thread(target=start_flask,args=[http_server], daemon=True)
    flask_thread.start()
    logger.info("HTTP Server started...")

def init_input():
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

    if config["input"]["http"]["enable"] == False and config["input"]["mqtt"]["enable"] == False:
        logger.critical("At least one input should be selected. Please check config.")
        exit()

def init_self_broker():
    if config["local-broker"]["enable"] == True:
        mosquitto_process = self_broker.start_mosquitto()

        if mosquitto_process is None:
            exit()
        
        # Wait 1 sec and check if process is still alive
        time.sleep(1)
        if mosquitto_process.poll() is not None:
            logger.error("Self hosted MQTT Broker could not be started : ")
            stdout, stderr = mosquitto_process.communicate()
            
        return mosquitto_process
    else:
        return None

def init_javascript():
    global js_worker_process, task_queue, result_queue
    js_worker_process, task_queue, result_queue = js_fetcher.start_js_worker()

    if (js_worker_process, task_queue, result_queue) == (None, None, None):
        logger.error("Fail to initialize JS Worker")
        exit()

def init_logging():
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

    logger.setLevel(log_level)


if __name__ == "__main__":
    launch()
    