from drivers.hc165_driver import *
from drivers.lin_slave import *
from config import LIN_frame_id

def init ():
    register_handler(LIN_frame_id,handle_input_request)
def handle_input_request(data):
    chips_data = read_all_chips(5)
    chips_bytes = bytes (chips_data)
    return chips_bytes