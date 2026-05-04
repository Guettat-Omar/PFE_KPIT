import logging

logger = logging.getLogger(__name__)
class WBPMonitor:
    def __init__(self):
        self.last_payload = b'\x00\x00\x00\x00\x00'  # Initialize to all zeros
        self.counter = 0
        self.threshold = 10  
        self.is_healthy = True
    def update(self, raw_response):
        if raw_response is None:
            self.counter += 1
            if self.counter >= self.threshold:
                self.is_healthy = False
            return self.last_payload
        
        self.counter = 0
        self.is_healthy = True

        if raw_response != self.last_payload:
            logger.info(f"[WBP] New payload: {raw_response.hex()}")
            self.last_payload = raw_response
        return self.last_payload