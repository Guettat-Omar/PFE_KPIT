from enum import Enum

class TurnSignalState(Enum):
    IDLE = 0
    LEFT = 1
    RIGHT = 2
    HAZARD = 3

class TurnSignalSM :
    def __init__(self):
        self.state = TurnSignalState.IDLE
    
    def update (self, left_on: bool, right_on:bool, hazard_on:bool):
        if hazard_on:
            self.state = TurnSignalState.HAZARD
        elif left_on and not right_on:
            self.state = TurnSignalState.LEFT
        elif right_on and not left_on:
            self.state = TurnSignalState.RIGHT
        else:
            self.state = TurnSignalState.IDLE
    
    def get_light_cmd_bits(self, flash_state: bool) -> dict:
        if flash_state:
            if self.state == TurnSignalState.IDLE:
                return {"LeftTurnLed": 0, "RightTurnLed": 0}
            elif self.state == TurnSignalState.LEFT:
                return {"LeftTurnLed": 1, "RightTurnLed": 0}
            elif self.state == TurnSignalState.RIGHT:
                return {"LeftTurnLed": 0, "RightTurnLed": 1}
            elif self.state == TurnSignalState.HAZARD:
                return {"LeftTurnLed": 1, "RightTurnLed": 1}
        else:
            return {"LeftTurnLed": 0, "RightTurnLed": 0}
