from enum import Enum

class ReverseSignalState(Enum):
    OFF = 0
    ON = 1
    


class ReverseSignalSM :
    def __init__(self):
        self.state = ReverseSignalState.OFF
    
    def update (self, reverse_on: bool):
        if reverse_on:
            self.state = ReverseSignalState.ON
        else:
            self.state = ReverseSignalState.OFF

    def get_reverse_cmd_bits(self) -> dict:
        if self.state == ReverseSignalState.OFF:
            return {"ReverseLed": 0}
        else:
            return {"ReverseLed": 1}