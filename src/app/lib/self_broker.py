
######## MOSQUITTO #########

# Run mosquitto as a subprocess
import subprocess
import logging


logger = logging.getLogger(__name__)


def start_mosquitto():
    try:
        # This will start Mosquitto in the background
        process = subprocess.Popen(["mosquitto", "-c" ,"/etc/mosquitto.conf"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
    else:
        logger.error("Tried to shutdown already stopped mosquitto process...")
