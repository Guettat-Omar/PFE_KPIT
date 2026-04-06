# Automotive Embedded Systems: BCM & LSN Architecture
**Status Report & Next Steps**
**Date:** April 6, 2026

## 1. What We Have Built
We successfully transition from a simple, highly-coupled hardware script into an **AUTOSAR-inspired Distributed Network Architecture**. We established a "Smart Master / Dumb Slave" network using two Raspberry Pis.

### Major Milestones Completed:
*   **Hardware Abstraction Layer (HAL) & Drivers:** Implemented LIN (Master/Slave) and CAN (`socketcan`) drivers to handle physical network transmission, moving away from simple GPIO manipulation for networking.
*   **Application Software (ASWs):** Created isolated Finite State Machines (`TurnSignalSM`, `HeadlightSM`, `BrakeSignalSM`, `ReverseSignalSM`) that calculate logical intents (e.g., `LeftTurnLed = 1`) without knowing about hardware pins.
*   **Cooperative Multitasking:** Replaced blocking `time.sleep()` calls with a non-blocking `FlashTimer`. This guarantees the BCM event loop operates responsively at 50Hz without freezing execution.
*   **Decoupled Network Matrices:** 
    *   Created **`LDF.ldf`** to explicitly map the Slave Node's input buttons (via 74HC165 shift registers) to specific bits.
    *   Created **`BCM_CAN.dbc`** to strictly define the hardware topology of the 74HC595 LEDs.
*   **Central Gateway / RTE:** Built `gateway.py` to bridge the LIN inputs mathematically to the State Machines, and then marshal the logical outputs through `cantools` into exact physical bytes on the CAN bus.
*   **Endianness & Bit Ordering:** Corrected the byte-shifting logic in the Master Gateway to naturally flip arrays `[::-1]`, accommodating the shift register topology on the Slave without requiring Slave code refactoring.

---

## 2. Next Steps & Production Roadmap

Our architecture is solid, but since it runs Python on a generic Linux OS, we need to address real-time deterministic constraints and stability.

### Step 1: Migrate to Hardware SPI for Shift Registers (High Priority)
*   **Current State:** The Slave Node bit-bangs GPIO pins using Python `for` loops in `hc595_driver.py` and `hc165_driver.py`.
*   **The Problem:** Linux task scheduling can interrupt the CPU mid-loop, distorting the clock pulses and loading garbage data into the LEDs.
*   **The Fix:** Replace the GPIO bit-banging with the Python `spidev` hardware module to leverage dedicated silicon for shifting data at MHz speeds reliably.

### Step 2: End-to-End (E2E) Communication Protection (Medium Priority)
*   **Current State:** CAN frames define raw LED bytes without safety wrappers.
*   **The Problem:** A random noise spike on the CAN bus could flip a bit, turning on the high beams inadvertently.
*   **The Fix:** Add a Rolling Counter (4-bit) and a CRC-8 Checksum to the `LIGHT_CMD` in `BCM_CAN.dbc`. Update the BCM to increment the counter and calculate the CRC on send, and update the LSN to validate the CRC on receive.

### Step 3: Implement Diagnostic Routines (Medium Priority)
*   **Current State:** We laid the groundwork for `0x3C / 0x3D` Master/Slave requests in the LDF.
*   **The Fix:** Add code to poll the LSN for its health status (e.g., CAN connectivity dropouts recorded via `NodeState.FAULT`) over LIN Diagnostics.

### Step 4: Embedded C++ & RTOS Migration (Long Term Vision)
*   **Current State:** Scripted in Python 3.
*   **The Fix:** Translate this mature, validated logic architecture into C/C++ running on FreeRTOS or bare-metal microcontrollers (like STM32 or ESP32) for true microsecond determinism and ISO 26262 compliance.
