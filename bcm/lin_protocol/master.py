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
        self._wakeup_slave()  # Ensure slave is awake before initializing serial
        
    def send_break(self):
      # Inter-frame gap — let bus settle and drain any stale bytes
      time.sleep(0.008)               # 20ms gap between frames
      self.ser.reset_input_buffer()   # flush anything that arrived during gap
  
      self.ser.baudrate = self.baud_rate // 4
      self.ser.write(bytes([BREAK_BYTE]))
      self.ser.flush()
      time.sleep(13 * (1.0 / (self.baud_rate // 4)))
      self.ser.baudrate = self.baud_rate
      time.sleep(0.005)
        
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
        """Send unconditional frame (master to slave command)"""
        if frame_id > 0x3F:
            raise ValueError("Frame ID must be 6 bits (0-63)")
        if len(data) > MAX_FRAME_DATA_LENGTH:
            raise ValueError(f"Data length exceeds maximum of {MAX_FRAME_DATA_LENGTH} bytes")
        
        self.send_break()
        self.ser.write(bytes([SYNC_BYTE]))
        pid = self.calculate_pid(frame_id)
        self.ser.write(bytes([pid]))
        self.ser.write(data)
        checksum = self.calculate_checksum(pid, data)
        self.ser.write(bytes([checksum]))
        self.ser.flush()
    
    def request_data(self, frame_id, expected_data_length=8):
      """Request data from slave"""
      if frame_id > 0x3F:
          raise ValueError("Frame ID must be 6 bits (0-63)")
      
      self.send_break()  # send_break() already calls reset_input_buffer()
      
      self.ser.write(bytes([SYNC_BYTE]))
      pid = self.calculate_pid(frame_id)
      self.ser.write(bytes([pid]))
      self.ser.flush()
      
      # Wait until buffer has enough bytes or timeout
      # Expected: up to 3 echo bytes + data + checksum
      expected_total = 3 + expected_data_length + 1
      deadline = time.monotonic() + 0.030  # 30ms timeout
      
      while time.monotonic() < deadline:
          if self.ser.in_waiting >= expected_total:
              break
          time.sleep(0.001)
      
      # Read everything in buffer
      all_bytes = bytearray(self.ser.read(self.ser.in_waiting))
      
      # Find PID byte in buffer — everything after it is the response
      pid_byte = pid & 0xFF
      pid_pos = -1
      for i in range(len(all_bytes)):
          if all_bytes[i] == pid_byte:
              pid_pos = i
              break
      
      if pid_pos == -1:
          raise LINFrameError(f"PID byte {hex(pid_byte)} not found in buffer")
      
      response_bytes = bytearray(all_bytes[pid_pos + 1:])
      
      # Read remaining bytes if needed
      if len(response_bytes) < expected_data_length + 1:
          remaining = self.ser.read(expected_data_length + 1 - len(response_bytes))
          response_bytes += remaining
      
      if len(response_bytes) < expected_data_length + 1:
          raise LINFrameError(f"Expected {expected_data_length} bytes, got {max(0, len(response_bytes) - 1)}")
      
      data = bytes(response_bytes[:expected_data_length])
      checksum = response_bytes[expected_data_length]
      
      if not self.verify_checksum(pid, data, checksum):
          raise LINChecksumError("Response checksum failed")
      
      return data
    
    def verify_checksum(self, pid, data, received_checksum):
        """Verify checksum of received data"""
        calculated = self.calculate_checksum(pid, data)
        return calculated == received_checksum
    
    def _wakeup_slave(self, pulse_duration=0.002):
        GPIO.output(self.wakeup_pin, GPIO.LOW)
        time.sleep(pulse_duration)
        GPIO.output(self.wakeup_pin, GPIO.HIGH)
        
    def close(self):
        self.ser.close()
        GPIO.cleanup()