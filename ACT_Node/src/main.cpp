#include <Arduino.h>
#include <mcp_can.h>
#include <mcp_can_dfs.h>
#include "config.h"
#include "motor_driver.h"
MCP_CAN CAN(SPI_CS_PIN);                                        

void setup() {
    Serial.begin(9600);
  motor_driver_init();
  if (CAN.begin(MCP_ANY, CAN_500KBPS, MCP_16MHZ) != CAN_OK) {
    Serial.println("CAN init failed!");
    while(1);
  }
  Serial.println("CAN init OK");
  CAN.setMode(MCP_NORMAL);
}
void loop() {
  unsigned long canId;
  uint8_t len;
  uint8_t buf[8];
  if (CAN.checkReceive() == CAN_MSGAVAIL) {

    CAN.readMsgBuf(&canId, &len, buf);
    if (canId == WINDOW_CMD_ID) {
      uint8_t w1 = (buf[0] >> 0) & 0x07;  // bits 0-2
      uint8_t w2 = (buf[0] >> 3) & 0x07;  // bits 3-5
      uint8_t w3 = ((buf[0] >> 6) | (buf[1] << 2)) & 0x07;  // bits 6-8
      uint8_t w4 = (buf[1] >> 1) & 0x07;  // bits 9-11
      Serial.print("[ACT] W1="); Serial.print(w1);
      Serial.print(" W2="); Serial.print(w2);
      Serial.print(" W3="); Serial.print(w3);
      Serial.print(" W4="); Serial.println(w4);
      motorWA_command(w1);
      motorWB_command(w2);
      Serial.println("[ACT] Motors updated.");
    }
  }
}
