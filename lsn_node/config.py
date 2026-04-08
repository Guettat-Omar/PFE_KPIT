
import enum

# --- 74HC165 (Parallel-In Serial-Out) � Button Inputs ------------------------
PIN_165_LOAD_PL   = 23   # PL  - load parallel inputs (active LOW)
PIN_165_CLOCK_CP  = 24   # CP  - shift clock
PIN_165_DATA_QH   = 6    # QH  - serial data output to Pi
PIN_165_CE        = 5    # CE  - chip enable (active LOW)

# --- 74HC595 (Serial-In Parallel-Out) � LED Outputs --------------------------
PIN_595_DATA_SER   = 17  # SER   - serial data input from Pi
PIN_595_SHIFT_SRCLK = 22 # SRCLK - shift clock
PIN_595_LATCH_RCLK  = 27 # RCLK  - latch output register
PIN_595_RESET       = 4  # MR    - master reset (active LOW)

# --- MCP2515 CAN Controller ---------------------------------------------------
MCP2515_INT  = 25        # INT - interrupt (active LOW)

LIN_frame_id = 0x14
LIN_diag_frame_id = 0x3D  # 61 in decimal
CAN_frame_id = 0x102
CAN_frame_id_response = 0x202

# --- State Machine Enum -------------------------------------------------------
class NodeState(enum.Enum):
    INIT = 1
    RUNNING = 2
    FAULT = 3
    RECOVERY = 4

# --- Global System States -----------------------------------------------------
# Used to share health status between the CAN (Output) and LIN (Input) threads
can_bus_is_healthy = True
current_node_state = NodeState.INIT
last_fault_reason = "NONE"

PULSE_US = 0.000001  # 1 microsecond pulse duration for timing GPIO signals
