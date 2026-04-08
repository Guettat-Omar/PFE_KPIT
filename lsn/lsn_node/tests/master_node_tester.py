#!/usr/bin/env python3

import sys
import time
import can

sys.path.append('/home/pi/lsn_node')
from lin_protocol import LINMaster

# ==============================
# BUTTON POSITIONS
# ==============================
BUTTON_LEFT_TURN  = (4, 5)
BUTTON_RIGHT_TURN = (4, 4)
BUTTON_HAZARD     = (3, 0)
BUTTON_LOW_BEAM   = (3, 2)
BUTTON_HIGH_BEAM  = (3, 1)
BUTTON_PARKING    = (3, 6)
BUTTON_BRAKE      = (3, 5)
BUTTON_REVERSE    = (3, 4)

# ==============================
# HELPER: check button pressed
# ==============================
def is_button_pressed(data, pos):
    byte_idx, bit_idx = pos
    return (data[byte_idx] >> bit_idx) & 1

# ==============================
# MAPPING: LIN -> CAN FRAME
# ==============================
def map_lin_to_can(chips_data):
    """
    Returns (arbitration_id, data) OR (None, None)
    """
    if is_button_pressed(chips_data, BUTTON_LEFT_TURN): return 0x102, [0x00, 0x00, 0x00, 0x1C, 0x01]
    elif is_button_pressed(chips_data, BUTTON_RIGHT_TURN): return 0x102, [0x00, 0x70, 0x00, 0x00, 0x01]
    elif is_button_pressed(chips_data, BUTTON_HAZARD): return 0x102, [0x00, 0x70, 0x00, 0x1C, 0x01]
    elif is_button_pressed(chips_data, BUTTON_LOW_BEAM): return 0x102, [0x00, 0x80, 0x00, 0x02, 0x00]
    elif is_button_pressed(chips_data, BUTTON_HIGH_BEAM): return 0x102, [0x40, 0x80, 0x00, 0x02, 0x80]
    elif is_button_pressed(chips_data, BUTTON_PARKING): return 0x102, [0x00, 0x00, 0x00, 0x01, 0x20]
    elif is_button_pressed(chips_data, BUTTON_BRAKE): return 0x102, [0x21, 0x00, 0x00, 0x00, 0x40]
    elif is_button_pressed(chips_data, BUTTON_REVERSE): return 0x102, [0x10, 0x00, 0x80, 0x00, 0x00]
    return None, None

# ==============================
# MAIN
# ==============================
def main():
    lin = LINMaster()
    print("LIN Master initialized")
    
    can_bus = can.interface.Bus(channel='can0', bustype='socketcan')
    print("CAN Bus initialized")

    print("\n[MASTER NODE] Polling Slave Node...")
    print("Ctrl+C to stop\n")

    prev_data = None

    try:
        while True:
            try:
                # PHASE 3 UPGRADE: We now expect 6 bytes! (5 data + 1 diagnostic)
                response = lin.request_data(0x14, expected_data_length=6)
                chips_data = list(response)
                
            except Exception as e:
                print(f"LIN error: {e}")
                time.sleep(0.1)
                continue

            # 1. Extract the 6th Diagnostic Byte
            button_data = chips_data[0:5]
            diagnostic_byte = chips_data[5]

            # 2. Monitor changes
            if chips_data != prev_data:
                print(f"\nLIN RX: {[hex(b) for b in chips_data]}")
                
                # Check the diagnostic byte from the slave
                if diagnostic_byte == 0xFF:
                    print("🚨 [DIAGNOSTIC ALERT]: Slave Node is reporting a CAN FAULT (0xFF)!")
                elif diagnostic_byte == 0x00:
                    print("✅ [DIAGNOSTIC]: Slave Node is Healthy (0x00).")
                else:
                    print(f"⚠️ [WARNING]: Unknown Diagnostic Byte: {hex(diagnostic_byte)}")

                # 3. Map to CAN using only the first 5 button data bytes
                arb_id, data = map_lin_to_can(button_data)

                if data is not None:
                    print(f"CAN TX -> ID={hex(arb_id)} DATA={[hex(b) for b in data]}")
                    msg = can.Message(arbitration_id=arb_id, data=data, is_extended_id=False)
                    can_bus.send(msg)

                prev_data = chips_data[:]

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        lin.close()
        can_bus.shutdown()

if __name__ == "__main__":
    main()