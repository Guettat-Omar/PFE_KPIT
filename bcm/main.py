import sys
import os

# Add the 'didactic_code' root to Python's path so it can find the 'bcm' package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import logging
from bcm.config import DBC_path, CAN_CHANNEL
from bcm.app.gateway import BcmGateway
from bcm.app.flash_timer import FlashTimer
import logging.handlers

# Mock imports for hardware drivers. 
# We use try/except so we can run this on Windows for testing without Raspberry Pi errors.
try:
    from bcm.drivers.can_driver import init_can, send
    from bcm.drivers.lin_master import init_lin_master, request_frame
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("WARNING: Hardware drivers not found. Running in simulation mode.")
    
logger = logging.getLogger("BCM_MAIN")
logger.setLevel(logging.INFO)

# Define the format of the logs (e.g., "2026-04-09 14:00:00 - INFO: Starting...")
log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")

# 1. Create the Rotating File Handler (Max 5MB, keep 3 backup files)
log_path = os.path.join(os.path.dirname(__file__), 'bcm_node.log')
file_handler = logging.handlers.RotatingFileHandler(
    log_path, maxBytes=5*1024*1024, backupCount=3
)
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

# 2. Keep the Console Handler (so you still see logs if you perfectly run it manually)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)
def main():
    logger.info("Starting Body Control Module (BCM)...")

    # 1. Initialize Communication Buses
    if HARDWARE_AVAILABLE:
        # Initialize CAN (e.g., 'can0')
        bus = init_can()
        # Initialize LIN (e.g., '/dev/serial0')
        # We assume baudrate is handled inside init_lin_master via config.py
        init_lin_master('/dev/serial0')
    else:
        logger.warning("Simulation Mode: Hardware buses skipped.")

    # 2. Initialize the Application Layer (Gateway & Timers)
    gw = BcmGateway(DBC_path)
    if not gw.db:
        logger.critical("Cannot start BCM without an active CAN Database.")
        return

    # Create the 1Hz Heartbeat Timer (500ms ON / 500ms OFF)
    flash_timer = FlashTimer(period_ms=500)

    # 3. Enter the Infinite Loop (The BCM Lifecycle)
    logger.info("BCM entering active run state.")
    
    # Example Node ID from our LDF for LSN input is 0x14, Length is 5 bytes (+1 diag).
    LSN_FRAME_ID = 0x14
    LSN_PAYLOAD_LEN = 6 
    
    # Node ID for Diagnostic Slave Response is 0x3D
    LSN_DIAG_FRAME_ID = 0x3D
    LSN_DIAG_LEN = 8

    loop_counter = 0
    WBP_FRAME_ID = 0x12
    WBP_PAYLOAD_LEN = 4

    while True:
        try:
            loop_counter += 1
            
            # Step A: Update the heartbeat
            is_flashing = flash_timer.update()

            # Step B: Read Inputs from LIN Network
            lsn_payload = None
            wbp_payload = None
            if HARDWARE_AVAILABLE:
                # Normal Polling
                lsn_payload = request_frame(LSN_FRAME_ID, LSN_PAYLOAD_LEN)
                wbp_payload = request_frame(WBP_FRAME_ID, WBP_PAYLOAD_LEN)

                # Step B.2: Periodic Diagnostic Heartbeat (Once every ~1 second)
                if loop_counter % 50 == 0:
                    try:
                        diag_payload = request_frame(LSN_DIAG_FRAME_ID, LSN_DIAG_LEN)
                        node_state = diag_payload[0]
                        can_health = diag_payload[1]
                        
                        if node_state == 3 or can_health == 0xFF:
                            logger.critical(f"LSN DIAGNOSTIC FAULT DETECTED: NodeState={node_state}, CAN={can_health}. LSN is failing!")
                        else:
                            logger.info(f"LSN Health OK: NodeState={node_state}")
                            
                    except Exception as diag_err:
                        logger.error(f"[DIAG] Diagnostic request to LSN failed - Node may be offline: {diag_err}")
                
            else:
                # Simulation Mode: Inject fake 5-byte off-state payload
                lsn_payload = b'\x00\x00\x00\x00\x00\x00'
                wbp_payload = b'\x00\x00\x00\x00'

            # Step C: Feed inputs to the Brains (Gateway -> State Machines)
            can_payload = gw.process_and_send(lsn_payload, wbp_payload, is_flashing)

            # Step D: Broadcast intended outputs to CAN Network
            if can_payload:
                can_id = gw.light_cmd_msg.frame_id
                if HARDWARE_AVAILABLE:
                    send(can_id, list(can_payload))
                else:
                    # In simulation, we print it out only if it's changing or periodically to avoid spam
                    pass # We won't spam the console in simulation

            # Step E: Rest the CPU. 
            # A 20ms sleep ensures we run at ~50Hz. Fast enough to catch buttons instantly, 
            # but slow enough to leave 99% of the CPU free for other car functions.
            time.sleep(0.02)

        except KeyboardInterrupt:
            logger.info("BCM shutting down gracefully...")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            time.sleep(1) # Prevent infinite crash-loops from eating all CPU

if __name__ == "__main__":
    main()
