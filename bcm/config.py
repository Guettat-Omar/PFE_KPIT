
import os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LDF_path = os.path.join(base_path, "LDF.ldf")
DBC_path = os.path.join(base_path, "BCM_CAN.dbc")

LIN_BAUDRATE = 19200
CAN_BITRATE = 500000
CAN_CHANNEL = "can0"

LSN_FRAME_ID = 0x14
LSN_PAYLOAD_LEN = 6
WBP_FRAME_ID = 0x12
WBP_PAYLOAD_LEN = 5
LSN_DIAG_FRAME_ID = 0x3D
LSN_DIAG_LEN = 8
WBP_DIAG_FRAME_ID = 0x3E
WBP_DIAG_LEN = 4
LIGHT_CMD_ID = 0x102
WINDOW_CMD_ID = 0x103
FLASH_PERIOD_MS = 500
WBP_FAULT_THRESHOLD = 50
LIN_TIMEOUT_MS = 30

FLASH_PERIOD = 500  # 500ms ON + 500ms OFF (1Hz)
DRL_LDR_THRESHOLD = 512  # 50% of 10-bit ADC full scale

# --- MCP2515 CAN Controller ---------------------------------------------------
MCP2515_INT  = 25        # INT - interrupt (active LOW)
