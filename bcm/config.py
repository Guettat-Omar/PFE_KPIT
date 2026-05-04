
import os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LDF_path = os.path.join(base_path, "LDF.ldf")
DBC_path = os.path.join(base_path, "BCM_CAN.dbc")

LIN_BAUDRATE = 19200
CAN_BITRATE = 500000
CAN_CHANNEL = "can0"
FLASH_PERIOD = 500  # 500ms ON + 500ms OFF (1Hz)
DRL_LDR_THRESHOLD = 512  # 50% of 10-bit ADC full scale

# --- MCP2515 CAN Controller ---------------------------------------------------
MCP2515_INT  = 25        # INT - interrupt (active LOW)
