"""
Input Module
Responsible for reading the 74HC165 shift registers and transmitting
the state to the LIN bus master when polled.

LAYER: Application Layer
NODE: LSN Node | Raspberry Pi 4B
"""

import logging
import time
from drivers.hc165_driver import *
from drivers.lin_slave import *
from config import LIN_frame_id, NodeState
import config

logger = logging.getLogger(__name__)
comm_logger = logging.getLogger("communication")

previous_chips_data = None
last_lin_rx_time = time.time()  # Start the watchdog timer


def init():
    """
    Initializes the LIN input request handler.
    """
    logger.info("Initializing input module.")
    register_handler(LIN_frame_id, handle_input_request)


def check_lin_watchdog():
    """
    Checks if the LIN master has stopped polling us.
    If it has been more than 5 seconds since the last request, set FAULT state.
    """
    global last_lin_rx_time
    
    # If the system is already in FAULT, no need to keep warning
    if config.current_node_state == NodeState.FAULT:
        return
        
    time_since_last_poll = time.time() - last_lin_rx_time
    if time_since_last_poll > 5.0:
        logger.error(f"[LIN WATCHDOG] LIN Master lost! No polls received in {time_since_last_poll:.1f} seconds.")
        config.last_fault_reason = f"LIN_MASTER_TIMEOUT (> 5s)"
        config.current_node_state = NodeState.FAULT


def handle_input_request(data):
    """
    Callback triggered when the LIN master polls for input state.
    Reads button states from the cascaded 74HC165 chips and packages them into bytes.
    """
    global previous_chips_data, last_lin_rx_time
    
    # Reset the watchdog timer because the Master just knocked on our door!
    last_lin_rx_time = time.time()
    
    logger.debug(f"Received LIN request for frame {hex(LIN_frame_id)}. Reading hardware state...")
    try:
        chips_data = read_all_chips(5)
        
        # Phase 3: Upstream Diagnostics (LIN)
        # We append a 6th "Diagnostic" byte to our LIN payload. 
        # 0x00 means CAN is Healthy. 0xFF means CAN has Failed.
        diag_byte = 0x00 if config.can_bus_is_healthy else 0xFF
        chips_data.append(diag_byte)
        
        chips_bytes = bytes(chips_data)
        
        # Delta-Logging: Only log if the physical buttons or the error state changed
        if chips_bytes != previous_chips_data:
            logger.info(f"Input state changed: {chips_bytes.hex()}")
            previous_chips_data = chips_bytes
            comm_logger.info(f"LIN OUT | Frame: {hex(LIN_frame_id)} | Data: {chips_bytes.hex()}")
        
        logger.debug(f"Input request handled successfully. Returning payload: {chips_bytes.hex()}")
        return chips_bytes
        
    except Exception as e:
        logger.error(f"Failed to handle LIN input request: {e}")
        # Safe fallback upon crash (all zeros, indicating failure to read)
        return bytes([0x00] * 6)  

