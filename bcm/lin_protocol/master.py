import serial
import time
import RPi.GPIO as GPIO
from .constants import *
from .exceptions import *

class LINMaster:
    def __init__(self, serial_port=DEFAULT_SERIAL_PORT, baud_rate=DEFAULT_BAUD_RATE, 
                 wakeup_pin=DEFAULT_WAKEUP_PIN):
        self.ser = serial.Serial(serial_port, baudrate=baud_rate, timeout=0.5)
        self.baud_rate = baud_rate
        self.sleep_time_per_bit = 1.0 / baud_rate
        self.wakeup_pin = wakeup_pin
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.wakeup_pin, GPIO.OUT)
        GPIO.output(self.wakeup_pin, GPIO.HIGH)
        
    def send_break(self):
        """Send LIN break signal"""
        self.ser.baudrate = self.baud_rate // 4
        self.ser.write(bytes([BREAK_BYTE]))
        self.ser.flush()
        time.sleep(13 * (1.0 / (self.baud_rate // 4)))
        self.ser.baudrate = self.baud_rate
        time.sleep(0.02)   # stabilisation: let SoftwareSerial recover before sync byte
        self.ser.reset_input_buffer() 
        
    @staticmethod
    def calculate_pid(frame_id):
        """Calculate Protected Identifier with parity bits"""
        if frame_id > 0x3F:
            raise ValueError("Frame ID must be 6 bits (0-63)")
            
        p0 = (frame_id ^ (frame_id >> 1) ^ (frame_id >> 2) ^ (frame_id >> 4)) & 0x01
        p1 = ~((frame_id >> 1) ^ (frame_id >> 3) ^ (frame_id >> 4) ^ (frame_id >> 5)) & 0x01
        return (frame_id & 0x3F) | (p0 << 6) | (p1 << 7)
    
    @staticmethod
    def calculate_checksum(pid, data):
        """Calculate LIN 2.0 classic checksum"""
        checksum = pid
        for byte in data:
            checksum += byte
            if checksum > 0xFF:
                checksum -= 0xFF
        return (0xFF - checksum) & 0xFF
    
    def send_command(self, frame_id, data):
        """
        Send unconditional frame (master to slave command)
        
        Args:
            frame_id: 6-bit LIN frame ID (0-63)
            data: Data bytes to send (max 8 bytes)
        """
        if frame_id > 0x3F:
            raise ValueError("Frame ID must be 6 bits (0-63)")
        if len(data) > MAX_FRAME_DATA_LENGTH:
            raise ValueError(f"Data length exceeds maximum of {MAX_FRAME_DATA_LENGTH} bytes")
        
        self._wakeup_slave()
        self.send_break()
        self.ser.write(bytes([SYNC_BYTE]))
        
        pid = self.calculate_pid(frame_id)
        self.ser.write(bytes([pid]))
        self.ser.write(data)
        
        checksum = self.calculate_checksum(pid, data)
        self.ser.write(bytes([checksum]))
        self.ser.flush()
    
    def request_data(self, frame_id, expected_data_length=8):
        """
        Request data from slave (master sends header, expects response)
        
        Args:
            frame_id: 6-bit LIN frame ID (0-63)
            expected_data_length: Expected data length in response
            
        Returns:
            bytes: Received data from slave
        """
        if frame_id > 0x3F:
            raise ValueError("Frame ID must be 6 bits (0-63)")
        
        self._wakeup_slave()
        self.send_break()
        self.ser.write(bytes([SYNC_BYTE]))
        
        pid = self.calculate_pid(frame_id)
        self.ser.write(bytes([pid]))
        self.ser.flush()
        
        time.sleep(0.05)
        
        # Wait for response
        data = self.ser.read(expected_data_length)
        if len(data) != expected_data_length:
            raise LINFrameError(f"Expected {expected_data_length} bytes, got {len(data)}")
        
        checksum_byte = self.ser.read(1)
        if not checksum_byte:
            raise LINFrameError("Checksum byte timeout - no response from slave")
        checksum = checksum_byte[0]   # Python 3: index bytes object to get int
        
        if not self.verify_checksum(pid, data, checksum):
            raise LINChecksumError("Response checksum failed")
        
        return data
    
    def verify_checksum(self, pid, data, received_checksum):
        """Verify checksum of received data"""
        calculated = self.calculate_checksum(pid, data)
        return calculated == received_checksum
    
    def _wakeup_slave(self, pulse_duration=0.01):
        GPIO.output(self.wakeup_pin, GPIO.LOW)
        time.sleep(pulse_duration)
        GPIO.output(self.wakeup_pin, GPIO.HIGH)
        
    def close(self):
        self.ser.close()
        GPIO.cleanup()