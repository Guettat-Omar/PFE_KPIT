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
  if (CAN.begin(MCP_ANY, CAN_500KBPS, MCP_16MHZ) != CAN_OK)
  {
    Serial.println("CAN init failed!");
    while (1)
      ;
  }
  Serial.println("CAN init OK");
  CAN.setMode(MCP_NORMAL);
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

      // If door lock is 1, push pistons down (lock), if 0 push up (unlock)
      if (door_lock == 1)
      {
        motorPA_command(CMD_DOWN);
        motorPB_command(CMD_DOWN);
      }
      else
      {
        motorPA_command(CMD_UP);
        motorPB_command(CMD_UP);
      }

      if (child_safety == 0)
      {
        // Child safety is OFF, allow all windows to move
        motorWA_command(w1);
        motorWB_command(w2);
        // motorWC_command(w3);
        // motorWD_command(w4);
      }
      else
      {
        // Child safety is ON, block all windows and force them to stop!
        motorWA_command(CMD_STOP);
        motorWB_command(CMD_STOP);
        // motorWC_command(CMD_STOP);
        // motorWD_command(CMD_STOP);
      }
    }
  }}
