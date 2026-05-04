import logging
from bcm.app.brake_sm import BrakeSignalSM
from bcm.app.reverse_sm import ReverseSignalSM
import cantools
from bcm.app.turn_signal_sm import TurnSignalSM
from bcm.app.headlight_sm import headlightSM
from bcm.config import LDF_path, DBC_path
from bcm.utils.crc import calculate_crc8 

logger = logging.getLogger(__name__)

class BcmGateway:
    def __init__(self, DBC_path: str):
        # 1. Initialize the State Machines (The Brains)
        self.turn_sm = TurnSignalSM()
        self.headlight_sm = headlightSM()
        self.brake_sm = BrakeSignalSM()
        self.reverse_sm = ReverseSignalSM()
        
        # Initialize E2E sequence counter
        self.seq_counter = 0

        # 2. Load the DBC Database
        try:
            self.db = cantools.database.load_file(DBC_path)
            # Find the exact message template from the DBC
            self.light_cmd_msg = self.db.get_message_by_name('LIGHT_CMD')
            self.window_cmd_msg = self.db.get_message_by_name('WINDOW_CMD')
            logger.info("Gateway initialized and DBC loaded successfully.")
        except Exception as e:
            logger.critical(f"Failed to load DBC file: {e}")
            self.db = None
    
    def decode_wbp_frame(self, wbp_lin_data: bytes):
        state_to_cmd = {
            0: 0,  # WINDOW_OFF       → cmd=STOP
            1: 2,  # WINDOW_DOWN      → cmd=DOWN
            2: 1,  # WINDOW_UP        → cmd=UP
            3: 1,  # WINDOW_UP_AUTO   → cmd=UP
            4: 2,  # WINDOW_DOWN_AUTO → cmd=DOWN
        }
        commands ={}
        for i in range(4):
            window_state = wbp_lin_data[i] & 0x07
            commands.update({f"Window_{i+1}": state_to_cmd.get(window_state,0)}) 
        return commands

    def process_and_send(self, lsn_lin_data: bytes,wbp_lin_data: bytes, flash_state: bool) -> tuple[bytes, bytes] | None:
        """
        This runs every 30ms cycle.
        """
        if not self.db or lsn_lin_data is None or len(lsn_lin_data) < 5 or wbp_lin_data is None or len(wbp_lin_data) < 4:
          return None
        # Step 1: Parse the raw LIN bytes into Booleans EXACTLY matching the 74HC165 layout
        # BUTTON_LEFT_TURN = (4, 5) -> byte 4, bit 5
        # BUTTON_RIGHT_TURN = (4, 4) -> byte 4, bit 4
        # BUTTON_HAZARD = (3, 0) -> byte 3, bit 0
        # BUTTON_LOW_BEAM = (3, 2) -> byte 3, bit 2
        # BUTTON_HIGH_BEAM = (3, 1) -> byte 3, bit 1
        # BUTTON_BRAKE = (3, 5) -> byte 3, bit 5
        # BUTTON_REVERSE = (3, 4) -> byte 3, bit 4
        # BUTTON_FOG = (4, 3) -> byte 4, bit 3
        # BUTTON_FLASH = (4, 2) -> byte 4, bit 2
        # Note in Python, we shift the bit right and check if it's 1
        
        # Left Turn = Byte 3, Bit 6 (0x40)
        left_btn     = bool((lsn_lin_data[3] >> 6) & 1)
        # Right Turn = Byte 3, Bit 5 (0x20)
        right_btn    = bool((lsn_lin_data[3] >> 5) & 1)
        
        hazard_btn   = bool((lsn_lin_data[4] >> 3) & 1) # Double check this is correct on your board
        low_beam_sw  = bool((lsn_lin_data[2] >> 3) & 1) # byte 2, bit 3
        ftp_not_pressed = bool((lsn_lin_data[2] >> 6) & 1)  # normally closed = 1 when not pressed
        ftp_btn = not ftp_not_pressed                          # inverted: True when pressed
        high_beam_sw = bool((lsn_lin_data[2] >> 2) & 1) and ftp_not_pressed   # byte 4, bit 2 (momentary, raw)
        
        brake_sw     = bool((lsn_lin_data[1] >> 6) & 1) # Used to be byte 3 bit 5, moved it away to let rear fog use it
        reverse_sw   = bool((lsn_lin_data[1] >> 1) & 1)
        
        front_fog_sw = bool((lsn_lin_data[3] >> 7) & 1)   # fog ring engaged
        rear_fog_sw  = bool((lsn_lin_data[2] >> 0) & 1)
        
        # Position light is 000050000000 -> Byte 2 is 0x50 (Idle 0x40 + Switch 0x10) -> 0x10 is Bit 4
        parking_sw   = bool((lsn_lin_data[2] >> 4) & 1)
        
        # Step 1b: Debug — log raw parsed inputs so bit-mapping bugs are visible
        logger.debug(
            f"[GW] LIN raw: {lsn_lin_data.hex()} | "
            f"low={low_beam_sw} high={high_beam_sw} park={parking_sw} "
            f"ftp={ftp_btn} fog_f={front_fog_sw} fog_r={rear_fog_sw} "
            f"brake={brake_sw} rev={reverse_sw}"
        )
        window_commands = self.decode_wbp_frame(wbp_lin_data)
        logger.info(f"[WBP] Window commands: {window_commands}")


        # Step 2: Feed the State Machines
        self.turn_sm.update(left_btn, right_btn, hazard_btn)
        self.headlight_sm.update(low_beam_sw, high_beam_sw, parking_sw, front_fog_sw, rear_fog_sw, ftp_btn)
        self.brake_sm.update(brake_sw)
        self.reverse_sm.update(reverse_sw)

        # Step 3: Get their output dictionaries
        turn_signals = self.turn_sm.get_light_cmd_bits(flash_state)
        headlight_signals = self.headlight_sm.get_light_cmd_bits(ftp_btn)
        brake_signals = self.brake_sm.get_brake_cmd_bits()
        reverse_signals = self.reverse_sm.get_reverse_cmd_bits()

        # Step 4: Combine into the exact DBC mappings based on the new LED hardware table!
        combined_signals = {
            "Led_B0_0": 0, "Led_B0_3": 0, "Led_B0_5": 0, "Led_B0_6": 0, "Led_B0_7": 0,
            "Led_B1_0": 0, "Led_B1_1": 0, "Led_B1_2": 0, "Led_B1_3": 0, "Led_B1_4": 0, "Led_B1_7": 0,
            "Led_B2_0": 0, "Led_B2_1": 0, "Led_B2_7": 0,
            "Led_B3_1": 0, "Led_B3_4": 0, "Led_B3_5": 0, "Led_B3_6": 0, "Led_B3_7": 0,
            "Led_B4_0": 0, "Led_B4_4": 0, "Led_B4_5": 0, "Led_B4_6": 0, "Led_B4_7": 0,
            "Seq_Counter": self.seq_counter,  # Add the Seq_Counter to the dictionary
            "CRC_Checksum": 0  # Placeholder, we will calculate this next!
        }

        # Increment sequence counter for next time (0 to 15)
        self.seq_counter = (self.seq_counter + 1) % 16

        # --- Turn & Hazard Logic ---
        if turn_signals.get("LeftTurnLed") == 1:
            combined_signals["Led_B0_0"] = 1
            combined_signals["Led_B1_2"] = 1
            combined_signals["Led_B1_3"] = 1
            combined_signals["Led_B1_4"] = 1
            
        if turn_signals.get("RightTurnLed") == 1:
            combined_signals["Led_B0_0"] = 1
            combined_signals["Led_B3_4"] = 1
            combined_signals["Led_B3_5"] = 1
            combined_signals["Led_B3_6"] = 1

        # --- Headlight & Fog Logic ---
        if headlight_signals.get("LowBeamLed") == 1:
            combined_signals["Led_B1_1"] = 1
            combined_signals["Led_B3_7"] = 1
            
        if headlight_signals.get("HighBeamLed") == 1:
            combined_signals["Led_B0_7"] = 1
            combined_signals["Led_B1_1"] = 1
            combined_signals["Led_B3_7"] = 1
            combined_signals["Led_B4_6"] = 1

        # Front/Rear Fog Lights overlap in the physical scheme provided
        if headlight_signals.get("FrontFogLed") == 1:
            combined_signals["Led_B1_1"] = 1
            combined_signals["Led_B3_7"] = 1
            combined_signals["Led_B0_3"] = 1
            combined_signals["Led_B2_1"] = 1
        
        if headlight_signals.get("RearFogLed") == 1:
            combined_signals["Led_B4_4"] = 1
            combined_signals["Led_B2_7"] = 1
            
        if headlight_signals.get("ParkingLed") == 1:
            combined_signals["Led_B0_5"] = 1
            combined_signals["Led_B1_0"] = 1
            combined_signals["Led_B2_0"] = 1

        # --- Brake & Reverse Logic ---
        if brake_signals.get("BrakeLed") == 1:
            combined_signals["Led_B0_6"] = 1
            combined_signals["Led_B4_0"] = 1
            combined_signals["Led_B4_5"] = 1
            
        if reverse_signals.get("ReverseLed") == 1:
            combined_signals["Led_B3_1"] = 1
            combined_signals["Led_B1_7"] = 1
        # DRL fallback mapping
        if turn_signals.get("DrlLed", 0) == 1:
            combined_signals["Led_B2_0"] = 1
            combined_signals["Led_B4_7"] = 1

        # Step 5: Ask Cantools to encode the dictionary into raw CAN bytes
        try:
            # First encode with CRC = 0
            can_payload = bytearray(self.light_cmd_msg.encode(combined_signals))
            window_can_payload = bytearray(self.window_cmd_msg.encode(window_commands))
            
            # Step 6: Calculate E2E CRC on the first 6 bytes (0 through 5)
            # The CRC byte itself is at index 6, which is currently 0
            crc_val = calculate_crc8(bytes(can_payload[0:6]))
            
            # Re-encode or simply inject the CRC into the bytearray
            # Since DBC CRC is exactly byte 6:
            can_payload[6] = crc_val
            
            # COMPENSATION FOR SLAVE NODE:
            # If the LSN script has `reversed()` in its driver, we reverse it here
            can_payload = can_payload[::-1]
            
            logger.debug(f"Encoded CAN Payload with CRC: {can_payload.hex()}")
            return bytes(can_payload), bytes(window_can_payload)
        except Exception as e:
            logger.error(f"Failed to encode CAN message: {e}")
            return None