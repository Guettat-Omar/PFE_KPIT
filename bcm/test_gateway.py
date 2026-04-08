import sys
import os

# Add the 'didactic_code' root to Python's path so it can find 'bcm.app...'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cantools
from bcm.app.gateway import BcmGateway

def run_test():
    print("--- STARTING BCM GATEWAY TEST ---")
    
    dbc_path = os.path.join(os.path.dirname(__file__), '..', 'BCM_CAN.dbc')
    gw = BcmGateway(dbc_path)
    
    if not gw.db:
        print("❌ FAILED: Could not load BCM_CAN.dbc")
        return
    else:
        print("✅ SUCCESS: DBC Loaded.")

    print("\n--- TEST 1: ALL OFF (No Buttons Pressed) ---")
    # 5 Bytes of Zeroes
    null_payload = b'\x00\x00\x00\x00\x00'
    bytes_out = gw.process_and_send(null_payload, flash_state=False)
    print(f"CAN Payload (Expected 00 00): {bytes_out.hex()}")

    print("\n--- TEST 2: LEFT TURN ON (Tick) ---")
    # Left Turn is Byte 4, Bit 5 (0x20)
    left_turn_payload = b'\x00\x00\x00\x00\x20'
    bytes_out_tick = gw.process_and_send(left_turn_payload, flash_state=True)
    print(f"CAN Payload - Tick: {bytes_out_tick.hex()}")

    print("\n--- TEST 3: LEFT TURN ON (Tock) ---")
    # Flash OFF, but Left Button is still ON (being held down)
    bytes_out_tock = gw.process_and_send(left_turn_payload, flash_state=False)
    print(f"CAN Payload - Tock: {bytes_out_tock.hex()}")

    print("\n--- TEST 4: LOW BEAMS ON ---")
    # Low Beam is Byte 3, Bit 2 (0x04)
    low_beam_left_turn_payload = b'\x00\x00\x00\x04\x20'
    
    bytes_out_head = gw.process_and_send(low_beam_left_turn_payload, flash_state=True)
    print(f"CAN Payload: {bytes_out_head.hex()}")

    print("\n--- END OF TEST ---")

if __name__ == "__main__":
    run_test()