from enum import Enum


class BrakeSignalState(Enum):
    OFF = 0
    ON = 1
    


class BrakeSignalSM :
    def __init__(self):
        self.state = BrakeSignalState.OFF
    
    def update (self, brake_on: bool):
        if brake_on:
            self.state = BrakeSignalState.ON
        else:
            self.state = BrakeSignalState.OFF

    def get_brake_cmd_bits(self) -> dict:
        if self.state == BrakeSignalState.OFF:
            return {"BrakeLed": 0}
        else:
            return {"BrakeLed": 1}