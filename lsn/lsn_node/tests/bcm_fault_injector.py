"""
Automated HIL Tester: BCM Fault Injector
Runs on the LSN (Slave) Raspberry Pi.
Pretends to be the real LSN, but intentionally injects faults to test the BCM.
"""

import sys
import os
import time
import logging
import threading

# Use absolute path resolution to find all possible module locations
current_file_path = os.path.abspath(__file__)
lsn_node_dir = os.path.dirname(os.path.dirname(current_file_path)) # Parent dir (lsn_node)
lsn_root_dir = os.path.dirname(lsn_node_dir) # Grandparent dir (lsn)

# Add both to sys.path so we can find 'lin_protocol' and 'drivers' regardless of OS differences
sys.path.insert(0, lsn_root_dir)
sys.path.insert(0, lsn_node_dir)

try:
    from drivers.lin_slave import start as init_lin_slave, register_handler
    HARDWARE_AVAILABLE = True
except Exception as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
    HARDWARE_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("HIL_INJECTOR")

# Mock State 
class InjectorState:
    stuck_button = False
    diagnostic_fault = False
    offline_mode = False

state = InjectorState()

def mock_input_request(data):
    """
    Called when BCM requests Frame 0x14 (6 bytes).
    Normal: all zeros.
    Fault: inject a stuck 1-bit on the Turn Signal.
    """
    if state.offline_mode:
        # Return empty bytes to simulate silence without crashing the LIN driver thread
        return bytes()
    
    # Byte 0, Bit 0 = Left Turn Signal (example LDF mapping)
    if state.stuck_button:
        return bytes([0x01, 0x00, 0x00, 0x00, 0x00, 0x00]) # Stuck button
    else:
        return bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00]) # No buttons pressed

def mock_diagnostic_request(data):
    """
    Called when BCM requests Frame 0x3D (8 bytes).
    Normal: NodeState=2 (RUNNING)
    Fault: NodeState=3 (FAULT) or CAN=0xFF
    """
    if state.offline_mode:
        # Return empty bytes to simulate silence without crashing the LIN driver thread
        return bytes()
    
    byte_0 = 0x02 # NodeState.RUNNING
    byte_1 = 0x00 # CAN Ok
    
    if state.diagnostic_fault:
        byte_0 = 0x03 # NodeState.FAULT
        byte_1 = 0xFF # CAN Broken
        
    return bytes([byte_0, byte_1, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

def interactive_menu():
    time.sleep(1)
    while True:
        print("\n--- BCM HIL FAULT INJECTOR ---")
        print("1. Toggle Stuck Button (LIN 0x14)")
        print("2. Toggle Diagnostic Fault (LIN 0x3D)")
        print("3. Toggle Offline Mode (Drop all LIN traffic)")
        print("4. Reset to Normal")
        print("5. Exit")
        
        choice = input("Select Attack Scenario: ")
        
        if choice == '1':
            state.stuck_button = not state.stuck_button
            logger.info(f"Stuck Button: {state.stuck_button}")
        elif choice == '2':
            state.diagnostic_fault = not state.diagnostic_fault
            logger.info(f"Diagnostic Fault: {state.diagnostic_fault}")
        elif choice == '3':
            state.offline_mode = not state.offline_mode
            logger.info(f"Offline Mode: {state.offline_mode}")
        elif choice == '4':
            state.stuck_button = False
            state.diagnostic_fault = False
            state.offline_mode = False
            logger.info("Reset to Normal State. Responding safely.")
        elif choice == '5':
            logger.info("Exiting HIL Injector...")
            os._exit(0)

def main():
    logger.info("Starting BCM Fault Injector...")
    
    if not HARDWARE_AVAILABLE:
        logger.warning("Hardware missing. Run this on the LSN Raspberry Pi.")
        return

    # 1. Initialize the LIN Slave driver (Steals the Serial port)
    # Note: Do not run this while the real LSN main.py is running!
    # The start() function in lin_slave doesn't take arguments natively
    lin_thread = threading.Thread(target=init_lin_slave, daemon=True)
    lin_thread.start()
    
    # 2. Register malicious handlers for the BCM's requests
    register_handler(0x14, mock_input_request)
    register_handler(0x3D, mock_diagnostic_request)
    
    logger.info("Evil LIN endpoints registered. Waiting for BCM...")
    
    # 3. Start Interactive Menu
    menu_thread = threading.Thread(target=interactive_menu, daemon=True)
    menu_thread.start()
    
    # Keep main thread alive so LIN interrupts work
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")

if __name__ == "__main__":
    main()
