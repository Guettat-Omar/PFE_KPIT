from lin_protocol import LINSlave
import logging

logger = logging.getLogger(__name__)
slave = LINSlave()

def register_handler(frame_id, handler):
    slave.register_frame_handler(frame_id, handler)

def start():
    logger.info("Starting LIN slave...")
    slave.process_frames()