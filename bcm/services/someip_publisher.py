import socket
import struct
import json
import logging

logger = logging.getLogger(__name__)

class SomeIPPublisher:
    def __init__(self, multicast_addr='224.0.0.1', port=30490):
        self.multicast_addr = multicast_addr
        self.port = port
        self.session_id = 1
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        except OSError:
            pass  # Handle gracefully on systems where UDP multicast options fail
        logger.info(f"SOME/IP Publisher initialized on {self.multicast_addr}:{self.port}")

    def publish(self, vehicle_state):
        try:
            payload = json.dumps(vehicle_state).encode('utf-8')
            
            # Build SOME/IP header
            header = struct.pack('>IIHHBBBB',
                0x12348001,        # Message ID
                len(payload) + 8,  # Length
                0x0000,            # Client ID
                self.session_id,   # Session ID
                0x01,              # Protocol Version
                0x01,              # Interface Version
                0x02,              # Message Type (Notification)
                0x00               # Return Code (OK)
            )
            
            packet = header + payload
            self.sock.sendto(packet, (self.multicast_addr, self.port))
            
            self.session_id += 1
            if self.session_id > 0xFFFF:
                self.session_id = 1
        except Exception as e:
            logger.error(f"Failed to publish SOME/IP state: {e}")
