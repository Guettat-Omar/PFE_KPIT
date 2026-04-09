class headlightSM :
    def __init__(self):
        # Independent Boolean Flags (No Enum!) 
        # This allows multiple lights to be ON simultaneously (additive lighting)
        self.low_beam_active = False
        self.high_beam_active = False
        self.parking_active = False
        self.front_fog_active = False
        self.rear_fog_active = False
        
        # Edge detection memory for toggle buttons
        self._prev_high_beam = False

    def update (self, low_beam_on: bool, high_beam_on:bool, parking_on:bool, front_fog_on:bool, rear_fog_on:bool, ftp_on:bool):
        # --- 1. Momentary Button Edge Detection ---
        # Detects the exact moment High Beam is pressed (False -> True)
        high_beam_edge = high_beam_on and not self._prev_high_beam
        self._prev_high_beam = high_beam_on
        
        # --- 2. Parking Lights Logic (REQ-PARK-001, 002, 003) ---
        # Active if stalk is in Position 1 (parking) OR Position 2 (low beam)
        if parking_on or low_beam_on:
            self.parking_active = True
        else:
            self.parking_active = False
            
        # --- 3. Low Beam Logic (REQ-LOW-001, 002, 003) ---
        # Active if stalk is in Position 2 AND parking lights are ON (Prerequisite)
        if low_beam_on and self.parking_active:
            self.low_beam_active = True
        else:
            self.low_beam_active = False
            
        # --- 4. High Beam Logic (REQ-HIGH-001, 002, 003) ---
        # Toggles only when button is pressed AND low beams are already ON
        if high_beam_edge and self.low_beam_active :
            self.high_beam_active = not self.high_beam_active
            
        # If low beams are turned off, High Beams must automatically drop
        if not self.low_beam_active:
            self.high_beam_active = False
        
        # --- 5. Fog Lights Logic (REQ-FOG-001, 002, 003) ---
        # Fog ring positions (1=Front, 2=Rear). Prerequisite: Parking lights MUST be ON
        if self.parking_active :
            if rear_fog_on:
                # Position 2: Both fog lights ON
                self.rear_fog_active = True
                self.front_fog_active = True
            elif front_fog_on:
                # Position 1: Only front fog ON
                self.front_fog_active = True
                self.rear_fog_active = False
            else:
                # Ring is OFF
                self.front_fog_active = False
                self.rear_fog_active = False
        else:
            # Auto-deactivate if parking lights turn OFF
            self.front_fog_active = False
            self.rear_fog_active = False
    
    def get_light_cmd_bits(self, ftp_on: bool) -> dict:
        # Dynamically build the final output bit dictionary
        # Includes Flash-to-Pass (REQ-FTP-001) as a momentary OR override on High Beams
        return {
            "LowBeamLed": 1 if self.low_beam_active else 0,
            "HighBeamLed": 1 if (self.high_beam_active or ftp_on) else 0,
            "ParkingLed": 1 if self.parking_active else 0,
            "FrontFogLed": 1 if self.front_fog_active else 0,
            "RearFogLed": 1 if self.rear_fog_active else 0
        }