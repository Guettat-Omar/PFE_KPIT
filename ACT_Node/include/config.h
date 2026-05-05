#define WINDOW_CMD_ID 0x103
#define WINDOW_CMD_LEN 8

// Motor commands
#define CMD_STOP 0
#define CMD_UP   1
#define CMD_DOWN 2

// Window Motor A
const int ENA_WA = 3;  
const int IN1_WA = 2;
const int IN2_WA = 4;

// Window Motor B
const int ENB_WB = 5;  
const int IN3_WB = 7;
const int IN4_WB = A2;

// Piston A 
const int ENA_PA = 6;  
const int INP1_PA = 10;
const int INP2_PA = A1;
// Piston B
const int ENB_PB = 9;
const int INP1_PB = A3;
const int INP2_PB =A4;
// MCP CAN
const int SPI_CS_PIN = 8;
