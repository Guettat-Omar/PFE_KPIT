# Automotive Embedded Systems: BCM & LSN Architecture

**Status Report & Next Steps**
**Date:** April 6, 2026

## 1. What We Have Built

We successfully transition from a simple, highly-coupled hardware script into an **AUTOSAR-inspired Distributed Network Architecture**. We established a "Smart Master / Dumb Slave" network using two Raspberry Pis.

### Major Milestones Completed:

- **Hardware Abstraction Layer (HAL) & Drivers:** Implemented LIN (Master/Slave) and CAN (`socketcan`) drivers to handle physical network transmission, moving away from simple GPIO manipulation for networking.
- **Application Software (ASWs):** Created isolated Finite State Machines (`TurnSignalSM`, `HeadlightSM`, `BrakeSignalSM`, `ReverseSignalSM`) that calculate logical intents (e.g., `LeftTurnLed = 1`) without knowing about hardware pins.
- **Cooperative Multitasking:** Replaced blocking `time.sleep()` calls with a non-blocking `FlashTimer`. This guarantees the BCM event loop operates responsively at 50Hz without freezing execution.
- **Decoupled Network Matrices:**
  - Created **`LDF.ldf`** to explicitly map the Slave Node's input buttons (via 74HC165 shift registers) to specific bits.
  - Created **`BCM_CAN.dbc`** to strictly define the hardware topology of the 74HC595 LEDs.
- **Central Gateway / RTE:** Built `gateway.py` to bridge the LIN inputs mathematically to the State Machines, and then marshal the logical outputs through `cantools` into exact physical bytes on the CAN bus.
- **Endianness & Bit Ordering:** Corrected the byte-shifting logic in the Master Gateway to naturally flip arrays `[::-1]`, accommodating the shift register topology on the Slave without requiring Slave code refactoring.

---

## 2. Next Steps & Production Roadmap

Our architecture is solid, but since it runs Python on a generic Linux OS, we need to address real-time deterministic constraints and stability.

### Step 1: Optimize GPIO Bit-Banging (PCB Constraint Acknowledged)

- **Current State:** The Slave Node bit-bangs GPIO pins using Python `for` loops in `hc595_driver.py` and `hc165_driver.py`.
- **The Constraint:** The custom PCB is already printed, strictly wiring the shift registers to specific generic GPIO pins, meaning we cannot route them to hardware SPI pins.
- **The Fix:** We will keep the GPIO bit-banging but optimize the Python loops, potentially using `pigpio` or C-extensions if we notice Linux task scheduling causing LED flickering. For most didactic setups, standard `RPi.GPIO` at moderate speeds will suffice.

### Step 2: End-to-End (E2E) Communication Protection [DONE]

- **Current State:** CAN frames define raw LED bytes and include SAE J1850 CRC-8 and a 4-bit Sequence Counter.
- **The Problem:** A random noise spike on the CAN bus could flip a bit, turning on the high beams inadvertently.
- **The Fix:** Added a Rolling Counter (4-bit) and a CRC-8 Checksum to the `LIGHT_CMD` in `BCM_CAN.dbc`. Updated the BCM to increment the counter and calculate the CRC on send, and updated the LSN to validate the CRC and Sequence on receive. This completely mitigates data corruption and replay attacks.

### Step 3: Implement Diagnostic Routines [DONE]

- **Current State:** We laid the groundwork for `0x3C / 0x3D` Master/Slave requests in the LDF.
- **The Fix:** Added code to poll the LSN for its health status (e.g., CAN connectivity dropouts recorded via `NodeState.FAULT`) over LIN Diagnostics. The BCM now requests `0x3D` at 1Hz.

### Step 4: Automated HIL Testing & Fault Injection [DONE]

- **Current State:** Standalone fault injection scripts have been developed to bypass physical components and securely execute real-time attack vectors.
- **The Goal:** Build an automated test scripts running on the LSN Raspberry Pi that actively abuses the BCM to ensure it fails safely.
- **The Tests Built & Verified:**
  - **E2E Attack:** Inject CAN frames with bad CRC-8 checksums. (LSN Successfully detects and drops modified packets).
  - **Counter Attack:** Send sequence numbers out of order (e.g., 1, 2, 5). (LSN successfully rejects replay sequences).
  - **Hardware Fault:** Simulate a disconnected LIN bus or a stuck-high button. (BCM detects slave node heartbeat timeouts safely).
- **Why this happens after Step 2 & 3:** We cannot simulate bypassing the checksum protection until we have actually built the checksum protection.

### Step 5: Heterogeneous Architecture - Python BCM + C/RTOS Nodes

- **Current State:** The BCM and LSN are written completely in Python on a Linux environment (Raspberry Pi).
- **The Go Forward Plan:** The current two nodes function as an excellent testing and "Adaptive AUTOSAR"-like platform. For all _future_ nodes (like Doors, Sunroofs, Engine controllers), we will build them on bare-metal or RTOS (FreeRTOS) microcontrollers using **C/C++**.
- **Why Mix Them?** Because CAN and LIN rely _strictly_ on standard byte layouts (defined in your DBC and LDF), a C program running on an STM32 will communicate perfectly with a Python program running on a Raspberry Pi. This is precisely how modern Zonal Automotive architectures are constructed (mixing central high-level computers with low-level specialized microcontrollers).
