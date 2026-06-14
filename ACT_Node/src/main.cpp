#include <Arduino.h>
#include <mcp_can.h>
#include <mcp_can_dfs.h>
#include "config.h"
#include "motor_driver.h"
MCP_CAN CAN(SPI_CS_PIN);

void setup()
{
  Serial.begin(9600);
  motor_driver_init();
  
  uint8_t retries = 3U;
  while (retries > 0U) {
      if (CAN.begin(MCP_ANY, CAN_500KBPS, MCP_16MHZ) == CAN_OK) {
          CAN.setMode(MCP_NORMAL);
          Serial.println("[ACT] CAN init OK");
          return;
      }
      retries--;
      delay(100U);
  }
  Serial.println("[ACT] CAN init FAILED. Halting.");
  while (1U) { delay(1000U); }
}
void loop()
{
  update_all_motors(); // Keep checking the 5-second timers!

  unsigned long canId;
  uint8_t len;
  uint8_t buf[8];
  while (CAN.checkReceive() == CAN_MSGAVAIL)
  {
    CAN.readMsgBuf(&canId, &len, buf);
    if (canId == WINDOW_CMD_ID)
    {
      uint8_t w1 = (buf[0] >> 0) & 0x07;                   // bits 0-2
      uint8_t w2 = (buf[0] >> 3) & 0x07;                   // bits 3-5
      uint8_t w3 = ((buf[0] >> 6) | (buf[1] << 2)) & 0x07; // bits 6-8
      uint8_t w4 = (buf[1] >> 1) & 0x07;                   // bits 9-11
      uint8_t child_safety = (buf[1] >> 4) & 0x01;
      uint8_t door_lock = (buf[1] >> 5) & 0x01;

      static uint8_t last_door_lock = 0; 
      // If door lock is 1, push pistons down (lock), if 0 push up (unlock)
      if (door_lock != last_door_lock)
      {
      if (door_lock == 1)
        {
          pistonPA_command(CMD_UP);
          pistonPB_command(CMD_UP);
        }
        else
        {
          pistonPA_command(CMD_DOWN);
          pistonPB_command(CMD_DOWN);
        }
      last_door_lock = door_lock;
      }

      if (child_safety == 0)
      {
        motorWA_command(w1);
        motorWB_command(w2);
      }
      else
      {
        motorWA_command(CMD_STOP);
        motorWB_command(CMD_STOP);
      }
    }
  }}
