"""
Output Module
Responsible for receiving LIGHT_CMD over CAN, triggering the 74HC595 shift 
registers to update the LEDs, and sending back the LIGHT_STATUS.

LAYER: Application Layer
NODE: LSN Node | Raspberry Pi 4B
"""

import time
import can 
import logging
import subprocess
from drivers.hc595_driver import *
from config import CAN_frame_id, CAN_frame_id_response,NodeState
import config

logger = logging.getLogger(__name__)
comm_logger = logging.getLogger("communication")

def _calculate_crc8(data: bytes) -> int:
    """
    SAE J1850 CRC-8 calculation. Same identical math used on the BCM.
    Polynomial: 0x1D
    Initial value: 0xFF
    """
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x1D
            else:
                crc <<= 1
            crc &= 0xFF
    return crc ^ 0xFF

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
    can_error = 0
    last_counter = -1 # Initialize to -1 so the first expected counter is 0
    while True:
        try:
            msg = bus.recv(timeout=1.0)
            if msg is not None:
                # If we catch our target frame ID
                can_error = 0
                config.can_bus_is_healthy = True
                
                if msg.arbitration_id == CAN_frame_id:
                    logger.debug(f"Intercepted LIGHT_CMD: {msg.data.hex()}")
                    
                    # E2E Protection Validation (Extract 7 bytes)
                    # We expect 7 bytes (5 bytes of LEDs, 1 byte of Counter, 1 byte of CRC)
                    received_bytes = msg.data[:7]
                    
                    if len(received_bytes) == 7:
                        # 1. Reverse the whole array back to big-endian (since BCM reversed it)
                        reversed_data = received_bytes[::-1]
                        
                        # 2. Extract the CRC (it was originally at index 6 on the master)
                        received_crc = reversed_data[6]
                        data_to_check = bytes(reversed_data[0:6])
                        
                        # 3. Calculate what the CRC *should* be
                        expected_crc = _calculate_crc8(data_to_check)
                        
                        if received_crc != expected_crc:
                            logger.error(f"[E2E FAULT] CRC Mismatch! Expected: {hex(expected_crc)}, Got: {hex(received_crc)}. Discarding frame.")
                            continue # Drop the frame entirely, do not update LEDs!
                            
                        # 4. Extract the Sequence Counter (it's the 6th byte, bits 0-3)
                        current_counter = reversed_data[5] & 0x0F
                        
                        if last_counter == -1:
                            logger.info(f"E2E First Sync: Initializing Sequence Counter to {current_counter}")
                            last_counter = current_counter
                        else:
                            expected_counter = (last_counter + 1) % 16
                            if current_counter != expected_counter:
                                logger.error(f"[E2E FAULT] Sequence Counter Mismatch! Expected: {hex(expected_counter)}, Got: {hex(current_counter)}. Discarding frame.")
                                # Re-synchronize the counter to the received one to prevent permanent lockout
                                last_counter = current_counter
                                continue
                            # Update to the successful counter!
                            last_counter = current_counter

                        # 5. Extract only the 5 bytes intended for the Shift Registers
                        led_data = bytes(reversed_data[0:5])
                        
                        # Log the received CAN data to the dedicated communications log
                        comm_logger.info(f"CAN IN  | Frame: {hex(CAN_frame_id)} | E2E Valid | LED Data: {led_data.hex()}")
                        
                        # Update hardware LEDs. The driver expects them in the Slave's reversed order 
                        # (Led4 down to Led0). We can just reverse our clean led_data.
                        raw_shift_data = led_data[::-1]
                        
                        logger.debug("Writing validated data to LED shift registers...")
                        write_all_chips(raw_shift_data)
                        
                        # Send response back to CAN master
                        can_msg = can.Message(arbitration_id=CAN_frame_id_response, data=msg.data, is_extended_id=False)
                        logger.debug(f"Responding with LIGHT_STATUS frame {hex(CAN_frame_id_response)}: {msg.data.hex()}")
                        bus.send(can_msg)
                        comm_logger.info(f"CAN OUT | Frame: {hex(CAN_frame_id_response)} | Data: {msg.data.hex()}")
                    else:
                        logger.error(f"[E2E FAULT] Invalid length {len(msg.data)}. Expected 7. Discarding.")
            else:
                # Silence normal timeout warnings unless debugging deeply
                can_error = can_error + 1
                logger.debug(f"[CAN] recv timeout - bus is quiet. Waiting. Error count: {can_error}/5")
                
        except Exception as e:
            logger.error(f"Critical error in output execution loop: {e}")
            can_error += 1
            config.can_bus_is_healthy = False
            config.current_node_state = NodeState.FAULT
            config.last_fault_reason = "CAN_EXCEPTION_OS_ERROR"
            time.sleep(1) # Prevent CPU spinlock when interface is completely dead
            
        # This is the "Self-Healing" mechanism (Point 2)
        if can_error >= 5:
            logger.error("[CAN] Bus timeout limit reached! Hardware down. Attempting self-healing...")
            config.can_bus_is_healthy = False
            config.last_fault_reason = "CAN_BUS_HARDWARE_FAILURE"
            config.current_node_state = NodeState.RECOVERY
            
            # Shut down old socket properly to stop the "not properly shut down" warning
            try:
                if bus is not None:
                    bus.shutdown()
            except Exception as e:
                logger.error(f"[CAN] Failed to shutdown old socket: {e}")
                pass
            
            # Step 1: Execute ip link commands directly (removes the need for can_init.sh to exist at all!)
            subprocess.run(["sudo", "ip", "link", "set", "can0", "down"], capture_output=True)
            subprocess.run(["sudo", "ip", "link", "set", "can0", "type", "can", "bitrate", "500000"], capture_output=True)
            result = subprocess.run(["sudo", "ip", "link", "set", "up", "can0"], capture_output=True, text=True)
            
            logger.info("[CAN] Self-healing ip commands executed.")
            if result.stderr:
                logger.error(f"[CAN] Self-healing ip errors: {result.stderr.strip()}")
            
            # Give the OS 1 second to actually turn the hardware on before Python tries to bind to it!
            time.sleep(1)
            
            # Step 2: Re-initialize the Python socket object because the old connection is dead
            try:
                bus = init()
                # Step 3: Reset the loop counter 
                can_error = 0
                config.current_node_state = NodeState.RUNNING
                config.can_bus_is_healthy = True
            except Exception as e:
                logger.error(f"[CAN] Self-healing failed to re-init bus: {e}")
                time.sleep(2)

