LDF_path = "C:\\Users\\Omar\\Documents\\ME\\PFE 2026\\KPIT\\Code\\didactic_code\\LDF.ldf"
DBC_path = "C:\\Users\\Omar\\Documents\\ME\\PFE 2026\\KPIT\\Code\\didactic_code\\BCM_CAN.dbc"

LIN_BAUDRATE = 19200
CAN_BITRATE = 500000
CAN_CHANNEL = "can0"
FLASH_PERIOD = 500  # 500ms ON + 500ms OFF (1Hz)
DRL_LDR_THRESHOLD = 512  # 50% of 10-bit ADC full scale

# --- MCP2515 CAN Controller ---------------------------------------------------
MCP2515_INT  = 25        # INT - interrupt (active LOW)
