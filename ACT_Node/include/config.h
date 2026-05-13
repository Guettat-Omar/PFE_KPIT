#define WINDOW_CMD_ID 0x103
#define WINDOW_CMD_LEN 8

// Motor commands
#define CMD_STOP 0
#define CMD_UP   1
#define CMD_DOWN 2
#define CMD_UP_AUTO 3
#define CMD_DOWN_AUTO 4

// MCP2515 CAN (fixed SPI pins — do not touch)
const int SPI_CS_PIN = 8;
// 11=MOSI, 12=MISO, 13=SCK (hardwired)

// Window Motor A — L298N #1 Motor A
const int IN1_WA  = 2;
const int IN2_WA  = A0; // Changed from 4 to A0 to fix damaged hardware pin!
const int ENA_WA  = 3;   // PWM

// Window Motor B — L298N #1 Motor B
const int IN3_WB  = 6;
const int IN4_WB  = 7;
const int ENB_WB  = 5;   // PWM

// Piston A — L298N #2 Motor A
const int INP1_PA = A1;
const int INP2_PA = A2;
const int ENA_PA  = 9;   // PWM

// Piston B — L298N #2 Motor B
const int INP1_PB = A3;
const int INP2_PB = A4;
const int ENB_PB  = 10;  // PWM
