import logging
from bcm.app.brake_sm import BrakeSignalSM
from bcm.app.reverse_sm import ReverseSignalSM
import cantools
from bcm.app.turn_signal_sm import TurnSignalSM
from bcm.app.headlight_sm import headlightSM
from bcm.config import LDF_path, DBC_path # we will add DBC_path later, let's pretend it's in config for now

logger = logging.getLogger(__name__)

class BcmGateway:
    def __init__(self, DBC_path: str):
        # 1. Initialize the State Machines (The Brains)
        self.turn_sm = TurnSignalSM()
        self.headlight_sm = headlightSM()
        self.brake_sm = BrakeSignalSM()
        self.reverse_sm = ReverseSignalSM()
        
        # 2. Load the DBC Database
        try:
            self.db = cantools.database.load_file(DBC_path)
            # Find the exact message template from the DBC
            self.light_cmd_msg = self.db.get_message_by_name('LIGHT_CMD')
            logger.info("Gateway initialized and DBC loaded successfully.")
        except Exception as e:
            logger.critical(f"Failed to load DBC file: {e}")
            self.db = None

    def process_and_send(self, lsn_lin_data: bytes, flash_state: bool) -> bytes | None:
        """
        This runs every 30ms cycle.
        """
        if not self.db or not lsn_lin_data or len(lsn_lin_data) < 5:
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
        
        left_btn     = bool((lsn_lin_data[4] >> 5) & 1)
        right_btn    = bool((lsn_lin_data[4] >> 4) & 1)
        
        hazard_btn   = bool((lsn_lin_data[3] >> 0) & 1)
        low_beam_sw  = bool((lsn_lin_data[3] >> 2) & 1)
        high_beam_sw = bool((lsn_lin_data[3] >> 1) & 1)
        
        brake_sw     = bool((lsn_lin_data[3] >> 5) & 1)
        reverse_sw   = bool((lsn_lin_data[3] >> 4) & 1)
        
        front_fog_sw = bool((lsn_lin_data[4] >> 3) & 1)
        rear_fog_sw  = front_fog_sw # Binding both to the single fog button for now
        parking_sw   = False        # No parking button in the script
        
        # Step 2: Feed the State Machines
        self.turn_sm.update(left_btn, right_btn, hazard_btn)
        self.headlight_sm.update(low_beam_sw, high_beam_sw, parking_sw, front_fog_sw, rear_fog_sw)
        self.brake_sm.update(brake_sw)
        self.reverse_sm.update(reverse_sw)

        # Step 3: Get their output dictionaries
        turn_signals = self.turn_sm.get_light_cmd_bits(flash_state)
        headlight_signals = self.headlight_sm.get_light_cmd_bits()
        brake_signals = self.brake_sm.get_brake_cmd_bits()
        reverse_signals = self.reverse_sm.get_reverse_cmd_bits()


        # Step 4: Combine into the exact DBC mappings based on the new LED hardware table!
        combined_signals = {
            "Led_B0_0": 0, "Led_B0_5": 0, "Led_B0_6": 0, "Led_B0_7": 0,
            "Led_B1_0": 0, "Led_B1_1": 0, "Led_B1_2": 0, "Led_B1_3": 0, "Led_B1_4": 0,
            "Led_B2_0": 0, "Led_B2_7": 0,
            "Led_B3_4": 0, "Led_B3_5": 0, "Led_B3_6": 0, "Led_B3_7": 0,
            "Led_B4_0": 0, "Led_B4_4": 0, "Led_B4_5": 0, "Led_B4_6": 0, "Led_B4_7": 0,
        }

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
        if headlight_signals.get("FrontFogLed") == 1 or headlight_signals.get("RearFogLed") == 1:
            combined_signals["Led_B1_1"] = 1
            combined_signals["Led_B2_0"] = 1
            combined_signals["Led_B3_7"] = 1
            combined_signals["Led_B4_7"] = 1
            
        if headlight_signals.get("ParkingLed") == 1:
            combined_signals["Led_B1_3"] = 1
            combined_signals["Led_B2_7"] = 1
            combined_signals["Led_B3_6"] = 1
            combined_signals["Led_B4_4"] = 1

        # --- Brake & Reverse Logic ---
        if brake_signals.get("BrakeLed") == 1:
            combined_signals["Led_B0_6"] = 1
            combined_signals["Led_B4_0"] = 1
            combined_signals["Led_B4_5"] = 1
            
        if reverse_signals.get("ReverseLed") == 1:
            combined_signals["Led_B0_5"] = 1
            combined_signals["Led_B1_0"] = 1

        # DRL fallback mapping
        if turn_signals.get("DrlLed", 0) == 1:
            combined_signals["Led_B2_0"] = 1
            combined_signals["Led_B4_7"] = 1

        # Step 5: The Magic. Ask Cantools to encode the dictionary into raw CAN bytes!
        try:
            can_payload = self.light_cmd_msg.encode(combined_signals)
            
            # COMPENSATION FOR SLAVE NODE:
            # If the LSN script has `reversed()` in its driver, we simply reverse 
            # the CAN bytes here on the Master before sending!
            can_payload = can_payload[::-1]
            
            logger.debug(f"Encoded CAN Payload: {can_payload.hex()}")
            return can_payload
        except Exception as e:
            logger.error(f"Failed to encode CAN message: {e}")
            return None