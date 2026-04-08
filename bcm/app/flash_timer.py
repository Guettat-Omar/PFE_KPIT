import time

class FlashTimer:
    def __init__(self, period_ms=500):
        """
        period_ms: How long the flash stays ON and OFF in milliseconds.
                   500ms means 0.5s ON, 0.5s OFF (1Hz blink rate).
        """
        self.period_secs = period_ms / 1000.0
        self.flash_state = False
        self.last_toggle_time = time.time()

    def update(self) -> bool:
        """
        Must be called rapidly in the main loop.
        Returns the current flash state (True/False) without stopping the program.
        """
        current_time = time.time()
        
        # If enough time has passed (e.g., 0.5 seconds), flip the state
        if (current_time - self.last_toggle_time) >= self.period_secs:
            self.flash_state = not self.flash_state
            self.last_toggle_time = current_time
            
        return self.flash_state
