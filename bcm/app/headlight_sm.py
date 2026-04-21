import logging

logger = logging.getLogger(__name__)

class headlightSM:
    def __init__(self):
        # Independent Boolean Flags (No Enum!)
        # This allows multiple lights to be ON simultaneously (additive lighting)
        self.low_beam_active  = False
        self.high_beam_active = False
        self.parking_active   = False
        self.front_fog_active = False
        self.rear_fog_active  = False

        # Edge detection memory for TOGGLE buttons
        self._prev_high_beam = False

        # Edge detection memory for FTP (momentary) - for logging only
        self._prev_ftp = False

    def update(self, low_beam_on: bool, high_beam_on: bool, parking_on: bool,
               front_fog_on: bool, rear_fog_on: bool, ftp_on: bool):

        # --- 1. Edge Detection (rising-edge only) ---
        high_beam_edge = high_beam_on and not self._prev_high_beam
        self._prev_high_beam = high_beam_on

        ftp_edge = ftp_on and not self._prev_ftp
        self._prev_ftp = ftp_on

        if high_beam_edge:
            logger.debug("[HeadlightSM] HIGH BEAM button RISING EDGE detected")
        if ftp_edge:
            logger.debug("[HeadlightSM] FTP button RISING EDGE detected")

        # --- 2. Parking Lights (REQ-PARK-001, 002, 003) ---
        self.parking_active = parking_on or low_beam_on

        # --- 3. Low Beam (REQ-LOW-001, 002, 003) ---
        self.low_beam_active = low_beam_on and self.parking_active

        # --- 4. High Beam Toggle (REQ-HIGH-001, 002, 003) ---
        # Latches ON/OFF on each press. Prerequisite: low beams must be ON.
        # Auto-cancel: high beam turns OFF if low beams go OFF.
        if high_beam_edge and self.low_beam_active:
            self.high_beam_active = not self.high_beam_active
            logger.info(f"[HeadlightSM] High beam toggled -> {'ON' if self.high_beam_active else 'OFF'}")
        elif not self.low_beam_active:
            if self.high_beam_active:
                logger.info("[HeadlightSM] Low beam OFF -> auto-cancelling high beam")
            self.high_beam_active = False

        # --- 5. Fog Lights (REQ-FOG-001, 002, 003) ---
        if self.parking_active:
            if rear_fog_on:
                self.rear_fog_active  = True
                self.front_fog_active = True
            elif front_fog_on:
                self.front_fog_active = True
                self.rear_fog_active  = False
            else:
                self.front_fog_active = False
                self.rear_fog_active  = False
        else:
            self.front_fog_active = False
            self.rear_fog_active  = False

        logger.debug(
            f"[HeadlightSM] STATE: parking={self.parking_active} low={self.low_beam_active} "
            f"high={self.high_beam_active} ftp_raw={ftp_on} "
            f"front_fog={self.front_fog_active} rear_fog={self.rear_fog_active}"
        )

    def get_light_cmd_bits(self, ftp_on: bool) -> dict:
        """
        HighBeamLed = high_beam_active (toggle latch) OR ftp_on (momentary raw).
        These two are fully independent  FTP does NOT affect the latch state.
        """
        bits = {
            "LowBeamLed":  1 if self.low_beam_active else 0,
            "HighBeamLed": 1 if (self.high_beam_active or ftp_on) else 0,
            "ParkingLed":  1 if self.parking_active else 0,
            "FrontFogLed": 1 if self.front_fog_active else 0,
            "RearFogLed":  1 if self.rear_fog_active else 0,
        }
        logger.debug(f"[HeadlightSM] OUTPUT BITS: {bits}  (ftp_raw={ftp_on})")
        return bits