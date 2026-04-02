"""
Output Module
Responsible for receiving LIGHT_CMD over CAN, triggering the 74HC595 shift 
registers to update the LEDs, and sending back the LIGHT_STATUS.

LAYER: Application Layer
NODE: LSN Node | Raspberry Pi 4B
"""

import can 
import logging
from drivers.hc595_driver import *
from config import CAN_frame_id, CAN_frame_id_response

logger = logging.getLogger(__name__)
comm_logger = logging.getLogger("communication")

def init():
    """
    Initializes the CAN socketcar interface.
    """
    logger.info("Initializing CAN0 interface for socketcan...")
    try:
        bus = can.interface.Bus(channel='can0', bustype='socketcan')
        logger.info("CAN bus connected successfully.")
        return bus
    except Exception as e:
        logger.error(f"Failed to start CAN bus: {e}")
        raise

def run(bus):
    """
    Background loop that continuously polls the CAN bus for LIGHT_CMD frames.
    Updates the 74HC595 cascading LEDs and responds with LIGHT_STATUS.
    """
    logger.info("Output module background monitoring loop started.")
    while True:
        try:
            msg = bus.recv(timeout=1.0)
            list = []
            if msg is not None:
                # If we catch our target frame ID
                if msg.arbitration_id == CAN_frame_id:
                    logger.debug(f"Intercepted LIGHT_CMD: {msg.data.hex()}")
                    # Extract the payload bytes
                    for i in range(5):
                        # Ensure we don't index out of bounds
                        if i < len(msg.data):
                            list.append(msg.data[i])
                        else:
                            list.append(0x00)
                            
                    data = bytes(list)
                    
                    # Log the received CAN data to the dedicated communications log
                    comm_logger.info(f"CAN IN  | Frame: {hex(CAN_frame_id)} | Data: {data.hex()}")
                    
                    # Update hardware LEDs
                    logger.debug("Writing received data to LED shift registers...")
                    write_all_chips(data)
                    
                    # Send response back to CAN master
                    can_msg = can.Message(arbitration_id=CAN_frame_id_response, data=data, is_extended_id=False)
                    logger.debug(f"Responding with LIGHT_STATUS frame {hex(CAN_frame_id_response)}: {data.hex()}")
                    bus.send(can_msg)
                    comm_logger.info(f"CAN OUT | Frame: {hex(CAN_frame_id_response)} | Data: {data.hex()}")
            else:
                # Silence normal timeout warnings unless debugging deeply
                logger.debug("[CAN] recv timeout - bus is quiet. Waiting.")
                
        except Exception as e:
            logger.error(f"Critical error in output execution loop: {e}")
            # Do not exit the thread; recover context and loop again
            pass

