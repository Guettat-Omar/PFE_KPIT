from enum import IntEnum

class PWFState(IntEnum):
    PARKEN = 0
    WOHNEN = 1
    FAHREN = 2

class PWFStateSM:
    def __init__(self):
        # Always start in PARKEN
        self.current_state = PWFState.PARKEN

    def update(self, requested_state_raw: int):
        """
        Evaluates the requested state against the transition rules.
        """
        try:
            req_state = PWFState(requested_state_raw)
        except ValueError:
            return self.current_state.value  # Ignore invalid numbers

        # If it's already in the requested state, do nothing
        if self.current_state == req_state:
            return self.current_state.value

        # --- Transition Rules ---
        # All transitions between valid states (PARKEN, WOHNEN, FAHREN) are allowed.
        self.current_state = req_state

        return self.current_state.value

    def get_state(self) -> int:
        return self.current_state.value