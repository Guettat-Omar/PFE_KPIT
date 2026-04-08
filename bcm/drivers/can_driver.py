import logging
import can
from bcm.config import CAN_CHANNEL, CAN_BITRATE

logger = logging.getLogger(__name__)
bus = None

def init_can():
    global bus
    try:
        # python-can using SocketCAN
        bus = can.interface.Bus(channel=CAN_CHANNEL, bustype='socketcan', bitrate=CAN_BITRATE)
        logger.info(f"CAN Bus initialized on {CAN_CHANNEL} at {CAN_BITRATE} bps")
        return bus
    except Exception as e:
        logger.critical(f"Failed to initialize CAN bus: {e}")
        return None

def send(arb_id: int, data: list[int]) -> bool:
    # TODO: Implement this! Look at how python-can creates a can.Message
    logger.info(f"Sending CAN message: ID={hex(arb_id)}, Data={bytes(data).hex()}")
    try:
        msg = can.Message(arbitration_id=arb_id, data=bytes(data), is_extended_id=False)
        bus.send(msg)
        logger.debug("CAN message sent successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to send CAN message: {e}")
        return False

def recv(timeout: float = 0.1) -> can.Message | None:
    # TODO: Implement this!
    logger.info("Waiting to receive CAN message...")
    try:
        msg=bus.recv(timeout=0.1)
        if msg is not None:
            logger.info(f"Received CAN message: ID={hex(msg.arbitration_id)}, Data={msg.data.hex()}")
            return msg
        else:
            logger.debug("No CAN message received within timeout.")
            return None
    except Exception as e:
        logger.error(f"Error receiving CAN message: {e}")
        return None