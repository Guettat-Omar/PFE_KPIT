"""
Automated HIL Tester: LSN Fault Injector (Testing E2E Protection)
Runs on the BCM (Master) Raspberry Pi.
Pretends to be the BCM sending CAN frames, but intentionally corrupts the E2E
(End-to-End) protection to verify the LSN safely drops bad messages.
"""

import sys
import os
import time
import logging
import threading
from utils.crc import calculate_crc8

# Use absolute path resolution to guarantee we find the 'bcm' packages
current_file_path = os.path.abspath(__file__)
bcm_root_dir = os.path.dirname(current_file_path)
workspace_root_dir = os.path.dirname(bcm_root_dir)
sys.path.insert(0, workspace_root_dir)
sys.path.insert(0, bcm_root_dir)

try:
    from bcm.drivers.can_driver import init_can, send
    import cantools
    from bcm.config import DBC_path
    HARDWARE_AVAILABLE = True
except Exception as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
    HARDWARE_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("LSN_HIL_INJECTOR")

# Silencing the CAN driver so it doesn't spam our interactive menu at 50Hz!
logging.getLogger("bcm.drivers.can_driver").setLevel(logging.WARNING)

class InjectorState:
    bad_crc = False
    bad_sequence = False
    active = True

state = InjectorState()

def attack_loop():
    """ Runs continuously, blasting CAN messages to the LSN """
    if not HARDWARE_AVAILABLE:
        logger.error("Hardware not available, shutting down attack loop.")
        return
        
    try:
        db = cantools.database.load_file(DBC_path)
        light_msg = db.get_message_by_name("LIGHT_CMD")
    except Exception as e:
        logger.error(f"Could not load DBC: {e}")
        return

    bus = init_can()
    if not bus:
        return

    seq_counter = 0

    while True:
        if not state.active:
            time.sleep(1)
            continue
            
        try:
            # Initialize all CAN signals to 0 to satisfy cantools strict encoding
            signals = {sig.name: 0 for sig in light_msg.signals}
            
            # Tell LSN to turn ON some LEDs normally so we can physically see it working
            signals["Led_B0_5"] = 1 
            signals["Led_B1_0"] = 1 
            signals["Seq_Counter"] = seq_counter
            
            # If "Bad Sequence" is active, freeze the counter (Replay Attack!)
            if state.bad_sequence:
                signals["Seq_Counter"] = 5 # Always 5, a frozen replay
                logger.debug("Injecting REPLAY ATTACK (Frozen Sequence 5)")
            else:
                seq_counter = (seq_counter + 1) % 16
                
            # Dictionary -> Bytes (CRC is 0 for now)
            payload = bytearray(light_msg.encode(signals))
            
            # Step: Calculate CRC on first 6 bytes
            crc_val = calculate_crc8(bytes(payload[0:6]))
            
            # If "Bad CRC" is active, corrupt the math
            if state.bad_crc:
                crc_val = (crc_val + 1) % 256
                logger.debug("Injecting BAD CRC (Corrupted Checksum)")
                
            payload[6] = crc_val
            
            # Reverse bytes to match the Python implementation for LSN hardware
            final_bytes = payload[::-1]
            
            # Send to LSN
            send(light_msg.frame_id, list(final_bytes))
            
            # 50Hz transmission rate
            time.sleep(0.02)
            
        except Exception as e:
            logger.error(f"Error in attack loop: {e}")
            time.sleep(1)

def interactive_menu():
    time.sleep(1)
    while True:
        print("\n--- LSN HIL FAULT INJECTOR (E2E ATTACKS) ---")
        print("1. Toggle BAD CRC-8 Checksum Attack")
        print("2. Toggle REPLAY / BAD SEQUENCE Attack")
        print("3. Stop transmitting CAN entirely")
        print("4. Reset to Normal (Send Valid Frames)")
        print("5. Exit")
        
        choice = input("Select Attack Scenario: ")
        
        if choice == '1':
            state.bad_crc = not state.bad_crc
            logger.warning(f"BAD CRC Attack Active: {state.bad_crc}")
        elif choice == '2':
            state.bad_sequence = not state.bad_sequence
            logger.warning(f"REPLAY Attack Active: {state.bad_sequence}")
        elif choice == '3':
            state.active = not state.active
            status = "STOPPED" if not state.active else "TRANSMITTING"
            logger.warning(f"CAN Transmission: {status}")
        elif choice == '4':
            state.bad_crc = False
            state.bad_sequence = False
            state.active = True
            logger.info("Reset to Normal. Sending perfect valid E2E frames.")
        elif choice == '5':
            logger.info("Exiting...")
            os._exit(0)

if __name__ == "__main__":
    logger.info("Starting LSN E2E Fault Injector...")
    
    # 1. Start the CAN transmitting thread
    attack_thread = threading.Thread(target=attack_loop, daemon=True)
    attack_thread.start()
    
    # 2. Run the interactive menu
    interactive_menu()
