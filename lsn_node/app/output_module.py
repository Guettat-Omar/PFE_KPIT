import can 
from drivers.hc595_driver import *

def init ():
    bus = can.interface.Bus(channel='can0', bustype='socketcan')
    return bus

def run(bus):
    while True:
        msg = bus.recv()
        list = []
        if msg.arbitration_id == 0x102:
            for i in range (5):
                list.append(msg.data[i])
            data = bytes(list)
            write_all_chips(data)
            can_msg = can.Message(arbitration_id=0x202, data=data)
            bus.send(can_msg)
