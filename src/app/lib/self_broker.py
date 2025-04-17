######## MOSQUITTO #########

# Run mosquitto as a subprocess
import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def start_mosquitto() -> subprocess.Popen[bytes] | None:
    try:
        # This will start Mosquitto in the background
        if os.getenv("ENV") == "test":
            base_dir = os.path.dirname(__file__)
            config_path = os.path.join(base_dir, "mosquitto.conf")
        else:
            config_path = "/etc/mosquitto.conf"

        process = subprocess.Popen(
            ["mosquitto", "-c", config_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        logger.info("Self-hosted MQTT broker started.")
        return process
    except Exception as e:
        logger.critical(f"Error starting Self-hosted MQTT Broker: {e}")
        return None


# Stop mosquitto (kill the process)
def stop_mosquitto(process: subprocess.Popen[bytes]) -> int:
    if process:
        process.terminate()
        status_code = process.wait()
        logger.info("Self-hosted MQTT broker stopped.")
        return status_code
    else:
        logger.error("Tried to shutdown already stopped mosquitto process...")
