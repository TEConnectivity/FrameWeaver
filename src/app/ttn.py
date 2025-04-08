# Reference : https://www.thethingsindustries.com/docs/integrations/other-integrations/mqtt/
import time, base64 as b64, logging
from schemas import Frame

logger = logging.getLogger(__name__)

def parse_ttn(chunk: dict) -> Frame | None:
    try:
        fport = chunk["uplink_message"]["f_port"]
        raw_str = chunk["uplink_message"]["frm_payload"]
        raw = b64.b64decode(raw_str)
        dev_eui = chunk["end_device_ids"]["dev_eui"]
        chunk_time = time.time()
    except:
        logger.error("Cannot decode frame. Frame format changed, or LNS is misconfigured in config.yaml")
        return None
    
    return {"devEUI": dev_eui, "fPort": fport, "raw":raw, "received_time":chunk_time}