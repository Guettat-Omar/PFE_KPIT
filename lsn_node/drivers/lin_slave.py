from lin_protocol import LINSlave

slave = LINSlave()

def register_handler(frame_id, handler):
    slave.register_frame_handler(frame_id, handler)
def start():
    print("Starting LIN slave...")
    slave.process_frames()