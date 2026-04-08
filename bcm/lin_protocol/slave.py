import serial
import time
import RPi.GPIO as GPIO
from .constants import *
from .exceptions import *

class LINSlave:
    def __init__(self, serial_port=DEFAULT_SERIAL_PORT, baud_rate=DEFAULT_BAUD_RATE,
                 wakeup_pin=DEFAULT_WAKEUP_PIN):
        self.ser = serial.Serial(serial_port, baudrate=baud_rate, timeout=0.1)
        self.baud_rate = baud_rate
        self.wakeup_pin = wakeup_pin
        self.frame_handlers = {}
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.wakeup_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    def register_frame_handler(self, frame_id, handler, data_length=None):
        """
        Register handler for specific frame ID

        Args:
            frame_id:    LIN frame ID to handle
            handler:     Function that takes (data) and returns response data
            data_length: Expected number of data bytes when master sends data
                         on this frame (command frames only).
                         Leave None for request frames where master sends
                         only the header and slave responds.
        """
        self.frame_handlers[frame_id] = (handler, data_length)

    def process_frames(self):
        """
        Main processing loop - waits for and handles incoming frames
        """
        try:
            while True:
                try:
                    frame_id, pid_byte, data = self._receive_header()
                except LINError:
                    continue

                if frame_id in self.frame_handlers:
                    handler, _ = self.frame_handlers[frame_id]
                    response = handler(data)
                    if response is not None:
                        self._send_response(pid_byte, response)

        except KeyboardInterrupt:
            return
    
    def _receive_header(self):
        """Wait for and process incoming header (break, sync, PID)"""
        while True:
            if self.ser.in_waiting and self.ser.read(1) == bytes([BREAK_BYTE]):
                break
        
        sync = self.ser.read(1)
        if sync != bytes([SYNC_BYTE]):
            raise LINSyncError("Invalid sync byte")
        
        pid_raw = self.ser.read(1)
        if not pid_raw:
            raise LINTimeoutError("PID byte timeout")
        pid_byte = pid_raw[0]
        frame_id = self.parse_pid(pid_byte)
        if frame_id is None:
            raise LINParityError("PID parity check failed")

        # Check if this is a header-only frame (master requesting data from slave)
        if not self.ser.in_waiting:
            return (frame_id, pid_byte, None)

        # Command frame: master is sending data to slave.
        # Use the registered data_length so we read exactly the right number
        # of bytes, not MAX_FRAME_DATA_LENGTH (8), which would cause a 100ms
        # timeout waiting for bytes that will never arrive.
        handler_info = self.frame_handlers.get(frame_id)
        if handler_info and handler_info[1] is not None:
            data_len = handler_info[1]
        else:
            data_len = MAX_FRAME_DATA_LENGTH

        data = self.ser.read(data_len)
        checksum_raw = self.ser.read(1)
        if not checksum_raw:
            raise LINTimeoutError("Checksum byte timeout")
        checksum = checksum_raw[0]

        if not self.verify_checksum(pid_byte, data, checksum):
            raise LINChecksumError("Checksum verification failed")

        return (frame_id, pid_byte, data)
    
    def _send_response(self, pid, data):
        """Send response data with checksum"""
        if len(data) > MAX_FRAME_DATA_LENGTH:
            raise ValueError("Data too long for LIN frame")

        checksum = self.calculate_checksum(pid, data)
        self.ser.write(data)
        self.ser.write(bytes([checksum]))
        self.ser.flush()
    
    @staticmethod
    def parse_pid(pid_byte):
        """Extract frame ID and verify parity"""
        frame_id = pid_byte & 0x3F
        p0 = (pid_byte >> 6) & 0x01
        p1 = (pid_byte >> 7) & 0x01
        
        calc_p0 = (frame_id ^ (frame_id >> 1) ^ (frame_id >> 2) ^ (frame_id >> 4)) & 0x01
        calc_p1 = ~((frame_id >> 1) ^ (frame_id >> 3) ^ (frame_id >> 4) ^ (frame_id >> 5)) & 0x01
        
        if p0 != calc_p0 or p1 != calc_p1:
            return None
        return frame_id
    
    @staticmethod
    def calculate_checksum(pid, data):
        """Calculate checksum for response"""
        checksum = pid
        for byte in data:
            checksum += byte
            if checksum > 0xFF:
                checksum -= 0xFF
        return (0xFF - checksum) & 0xFF
    
    @staticmethod
    def verify_checksum(pid, data, received_checksum):
        """Verify checksum of received data"""
        calculated = LINSlave.calculate_checksum(pid, data)
        return calculated == received_checksum
    
    def close(self):
        self.ser.close()
        GPIO.cleanup()