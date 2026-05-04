import logging
from bcm.lin_protocol.master import LINMaster
from bcm.lin_protocol.exceptions import LINChecksumError, LINTimeoutError,LINFrameError
from bcm.config import LIN_BAUDRATE
logger = logging.getLogger(__name__)
master_instance = None

def init_lin_master(port, baudrate=LIN_BAUDRATE):
    global master_instance
    master_instance = LINMaster(port, baudrate)
    logger.info("LIN master initialized with baudrate: %d", baudrate)

def request_frame(frame_id: int, length: int) -> bytes | None:
    try:
        # We use request_data, not request_frame!
        response = master_instance.request_data(frame_id, expected_data_length=length)
        # CHANGED FROM DEBUG TO INFO TO SHOW IT ON TERMINAL
        logger.info(f"Received LIN response from LSN (ID {hex(frame_id)}): {response.hex()}")
        return response
    except LINChecksumError as e:
        logger.error(f"Checksum error for frame ID {hex(frame_id)}: {e}")
        return None
    except LINTimeoutError as e:
        logger.error(f"Timeout error for frame ID {hex(frame_id)}: {e}")
        return None
    except LINFrameError as e:
        logger.debug(f"Frame error for frame {hex(frame_id)}: {e}")  # debug not error
        return None

def send_frame(frame_id: int, data: bytes):
    try:
        master_instance.send_command(frame_id, data)
        logger.debug(f"Sent command for frame ID {hex(frame_id)}: {data}")
        return 
    except LINChecksumError as e:
        logger.error(f"Checksum error when sending frame ID {hex(frame_id)}: {e}")
        return False
    except LINTimeoutError as e:
        logger.error(f"Timeout error when sending frame ID {hex(frame_id)}: {e}")
        return False
    
def close_lin_master():
    global master_instance
    if master_instance:
        master_instance.close()