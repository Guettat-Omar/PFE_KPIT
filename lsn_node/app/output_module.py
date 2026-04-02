import can 
from drivers.hc595_driver import *
from config import CAN_frame_id, CAN_frame_id_response

def init ():
    bus = can.interface.Bus(channel='can0', bustype='socketcan')
    return bus

def run(bus):
    while True:
        msg = bus.recv(timeout=1.0)
        list = []
        if msg is not None:
            if msg.arbitration_id == CAN_frame_id:
                for i in range (5):
                    list.append(msg.data[i])
                data = bytes(list)
                write_all_chips(data)
                can_msg = can.Message(arbitration_id=CAN_frame_id_response, data=data)
                bus.send(can_msg)
        else:
            print("[CAN] recv timeout")
