from enum import Enum

class headlightState(Enum):
    OFF = 0
    LOW_BEAM = 1
    HIGH_BEAM = 2
    parking = 3
    FRONT_FOG_ON = 4
    REAR_FOG_ON = 5

class headlightSM :
    def __init__(self):
        self.state = headlightState.OFF
    
    def update (self, low_beam_on: bool, high_beam_on:bool, parking_on:bool, front_fog_on:bool, rear_fog_on:bool):
        if low_beam_on :
            self.state = headlightState.LOW_BEAM
        elif high_beam_on :
            self.state = headlightState.HIGH_BEAM
        elif parking_on :
            self.state = headlightState.parking
        elif front_fog_on :
            self.state = headlightState.FRONT_FOG_ON
        elif rear_fog_on :
            self.state = headlightState.REAR_FOG_ON
        else:
            self.state = headlightState.OFF
    
    def get_light_cmd_bits(self) -> dict:
        if self.state == headlightState.OFF:
            return {"LowBeamLed": 0, "HighBeamLed": 0, "ParkingLed": 0, "FrontFogLed": 0, "RearFogLed": 0}
        elif self.state == headlightState.LOW_BEAM:
            return {"LowBeamLed": 1, "HighBeamLed": 0, "ParkingLed": 1, "FrontFogLed": 0, "RearFogLed": 0}
        elif self.state == headlightState.HIGH_BEAM:
            return {"LowBeamLed": 0, "HighBeamLed": 1, "ParkingLed": 1, "FrontFogLed": 0, "RearFogLed": 0}
        elif self.state == headlightState.parking:
            return {"LowBeamLed": 0, "HighBeamLed": 0, "ParkingLed": 1, "FrontFogLed": 0, "RearFogLed": 0}
        elif self.state == headlightState.FRONT_FOG_ON:
            return {"LowBeamLed": 1, "HighBeamLed": 0, "ParkingLed": 1, "FrontFogLed": 1, "RearFogLed": 0}
        elif self.state == headlightState.REAR_FOG_ON:
            return {"LowBeamLed": 0, "HighBeamLed": 0, "ParkingLed": 1, "RearFogLed": 1, "FrontFogLed": 1}