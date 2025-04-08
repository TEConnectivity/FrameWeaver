# Reference : https://www.thethingsindustries.com/docs/integrations/other-integrations/mqtt/
import time, base64 as b64, logging
from . import schemas

logger = logging.getLogger(__name__)


# Reference : https://docs.loriot.io/space/NMS/6032848/Uplink+Data+Message
def parse_loriot(chunk: dict) -> schemas.Frame | None: # type: ignore
    try:
        if chunk["cmd"] != "rx":
            return None
    except:
        logger.error("Cannot decode frame. Frame format changed, or LNS is misconfigured in config.yaml")
        return None
    
    fport = chunk["port"]
    raw_str = chunk["data"] # Format hexstring "CAFEBABE"
    raw = bytes.fromhex(raw_str)
    dev_eui = chunk["EUI"]
    chunk_time = time.time()

    return {"devEUI": dev_eui, "fPort": fport, "raw":raw, "received_time":chunk_time}


