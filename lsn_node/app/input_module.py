"""
Input Module
Responsible for reading the 74HC165 shift registers and transmitting
the state to the LIN bus master when polled.

LAYER: Application Layer
NODE: LSN Node | Raspberry Pi 4B
"""

import logging
from drivers.hc165_driver import *
from drivers.lin_slave import *
from config import LIN_frame_id

logger = logging.getLogger(__name__)
comm_logger = logging.getLogger("communication")
previous_chips_data = None

def init():
    """
    Initializes the LIN input request handler.
    """
    logger.info("Initializing input module.")
    register_handler(LIN_frame_id, handle_input_request)


def handle_input_request(data):
    """
    Callback triggered when the LIN master polls for input state.
    Reads button states from the cascaded 74HC165 chips and packages them into bytes.
    """
    global previous_chips_data
    logger.debug(f"Received LIN request for frame {hex(LIN_frame_id)}. Reading hardware state...")
    try:
        chips_data = read_all_chips(5)
        chips_bytes = bytes(chips_data)
        if chips_bytes != previous_chips_data:
            logger.info(f"Input state changed: {chips_bytes.hex()}")
            previous_chips_data = chips_bytes
            comm_logger.info(f"LIN OUT | Frame: {hex(LIN_frame_id)} | Data: {chips_bytes.hex()}")
        
            logger.debug(f"Input request handled successfully. Returning payload: {chips_bytes.hex()}")
        # Log the LIN output data to the dedicated communications log

        return chips_bytes
    except Exception as e:
        logger.error(f"Failed to handle LIN input request: {e}")
        return bytes([0x00] * 5)  # Safe fallback upon crash