# LIN Protocol Library v3 — Python

A Python library implementing the **LIN (Local Interconnect Network)** serial communication protocol for Raspberry Pi. It provides both **Master** and **Slave** node implementations, handling all low-level protocol details such as break signals, sync bytes, protected identifiers (PID), and checksums.

---

## Table of Contents

- [What is LIN?](#what-is-lin)
- [Project Structure](#project-structure)
- [File-by-File Explanation](#file-by-file-explanation)
  - [constants.py](#constantspy)
  - [exceptions.py](#exceptionspy)
  - [master.py](#masterpy)
  - [slave.py](#slavepy)
  - [\_\_init\_\_.py](#__init__py)
- [LIN Frame Format](#lin-frame-format)
- [PID Calculation](#pid-calculation)
- [Checksum Algorithm](#checksum-algorithm)
- [Usage Examples](#usage-examples)
- [Hardware Requirements](#hardware-requirements)

---

## What is LIN?

LIN (Local Interconnect Network) is a low-cost serial communication standard widely used in automotive systems. It operates on a single-wire bus with one **master** node and up to 16 **slave** nodes. The master always initiates communication by sending a **frame header**; slaves respond when addressed.

A LIN frame consists of:

```
| BREAK | SYNC (0x55) | PID | DATA (1-8 bytes) | CHECKSUM |
```

---

## Project Structure

```
lin_protocol/
├── __init__.py       # Package entry point — exports public API
├── constants.py      # Protocol-level constants and defaults
├── exceptions.py     # Custom exception hierarchy
├── master.py         # LINMaster class
└── slave.py          # LINSlave class
```

---

## File-by-File Explanation

### `constants.py`

Defines all shared configuration values used by both master and slave.

```python
DEFAULT_SERIAL_PORT = '/dev/serial0'   # UART port on Raspberry Pi
DEFAULT_BAUD_RATE   = 19200            # Standard LIN baud rate
DEFAULT_WAKEUP_PIN  = 18               # BCM GPIO pin for wakeup signal

SYNC_BYTE              = 0x55   # Fixed sync byte sent after every break
BREAK_BYTE             = 0x00   # Byte used to generate the break signal
MAX_FRAME_DATA_LENGTH  = 8      # LIN frames carry at most 8 data bytes

UNCONDITIONAL_FRAME    = 0      # Frame always carries data
EVENT_TRIGGERED_FRAME  = 1      # Frame sent only on an event
SPORADIC_FRAME         = 2      # Master sends only when data changed
```

**Why these values?**

- `0x55` as sync byte is a special choice: in binary it is `01010101`, which gives the receiver a perfectly alternating pattern to calibrate its baud rate clock.
- The break signal is intentionally sent at 1/4 the normal baud rate so it dominates the bus visibly longer than any normal byte, marking the start of a new frame.

---

### `exceptions.py`

Defines a clean exception hierarchy so callers can catch errors at any level of specificity.

```
LINError                  ← base class for all LIN errors
├── LINChecksumError      ← received checksum does not match calculated one
├── LINParityError        ← PID parity bits are wrong (corrupted identifier)
├── LINSyncError          ← sync byte (0x55) was not found where expected
├── LINFrameError         ← frame has wrong length or structure
└── LINTimeoutError       ← no response received within the timeout window
```

All exceptions inherit from `LINError`, which itself inherits from Python's built-in `Exception`. This means callers can catch just `LINError` to handle all protocol errors, or catch specific subclasses for fine-grained handling.

---

### `master.py`

Implements the `LINMaster` class. The master is the **only node** that initiates frames on the bus. All communication starts with the master.

#### `__init__(serial_port, baud_rate, wakeup_pin)`

```python
self.ser = serial.Serial(serial_port, baudrate=baud_rate, timeout=0.1)
self.sleep_time_per_bit = 1.0 / baud_rate

GPIO.setmode(GPIO.BCM)
GPIO.setup(self.wakeup_pin, GPIO.OUT)
GPIO.output(self.wakeup_pin, GPIO.HIGH)  # Idle high
```

- Opens the UART serial port.
- Configures GPIO pin as output, held HIGH (idle state).
- Calculates `sleep_time_per_bit` for timing the break signal duration.

---

#### `_wakeup_slave(pulse_duration=0.01)`

```python
GPIO.output(self.wakeup_pin, GPIO.LOW)
time.sleep(pulse_duration)
GPIO.output(self.wakeup_pin, GPIO.HIGH)
```

Sends a short LOW pulse on the GPIO wakeup pin. This is used to wake a slave that may be in a low-power sleep state before sending a LIN frame over the UART.

---

#### `send_break()`

```python
self.ser.baudrate = self.baud_rate // 4       # Drop to 1/4 speed
self.ser.write(bytes([BREAK_BYTE]))           # Send 0x00
self.ser.flush()
time.sleep(13 * (1.0 / (self.baud_rate // 4)))  # Hold for 13 bit-times
self.ser.baudrate = self.baud_rate            # Restore normal speed
```

The LIN break signal is a dominant (LOW) bus state lasting at least 13 bit periods. This is achieved by temporarily reducing the baud rate to 1/4 so that sending a single `0x00` byte takes 4x longer, creating the required long LOW pulse that all slaves recognize as the start of a new frame.

---

#### `calculate_pid(frame_id)` — static method

```python
p0 = (frame_id ^ (frame_id >> 1) ^ (frame_id >> 2) ^ (frame_id >> 4)) & 0x01
p1 = ~((frame_id >> 1) ^ (frame_id >> 3) ^ (frame_id >> 4) ^ (frame_id >> 5)) & 0x01
return (frame_id & 0x3F) | (p0 << 6) | (p1 << 7)
```

The raw 6-bit `frame_id` is protected by adding two parity bits (P0 and P1) to form the 8-bit **Protected Identifier (PID)**:

```
PID byte layout:
[ P1 | P0 | ID5 | ID4 | ID3 | ID2 | ID1 | ID0 ]
  bit7  bit6  bit5 ... bit0
```

- **P0** = XOR of bits 0, 1, 2, 4 of the frame ID.
- **P1** = inverted XOR of bits 1, 3, 4, 5 of the frame ID.

These parity bits allow the slave to detect corrupted identifiers caused by bus noise.

---

#### `calculate_checksum(pid, data)` — static method

```python
checksum = pid
for byte in data:
    checksum += byte
    if checksum > 0xFF:
        checksum -= 0xFF       # Carry-around addition
return (0xFF - checksum) & 0xFF
```

Implements the **LIN 2.0 "classic" checksum** (also called inverted sum with carry-around):

1. Start with the PID value.
2. Add each data byte; if the sum exceeds 255, subtract 255 (carry-around, not truncate).
3. Invert the final sum (`0xFF - sum`) to get the checksum.

The receiver recalculates this value and compares it with the transmitted checksum byte.

---

#### `send_command(frame_id, data)`

Sends a **full unconditional LIN frame** (master writes data to slave):

```
GPIO wakeup pulse
    → BREAK signal
    → SYNC byte (0x55)
    → PID byte
    → data bytes (1–8)
    → checksum byte
```

Raises `ValueError` if `frame_id > 63` or `len(data) > 8`.

---

#### `request_data(frame_id, expected_data_length=8)`

Sends a **header-only frame** to request data from a slave:

```
GPIO wakeup pulse
    → BREAK signal
    → SYNC byte (0x55)
    → PID byte
    ← (slave responds with data + checksum)
```

- Reads back `expected_data_length` bytes from the slave.
- Reads 1 more byte as the checksum.
- Verifies the checksum; raises `LINChecksumError` on mismatch.
- Returns the received data bytes.

---

#### `verify_checksum(pid, data, received_checksum)`

Recalculates the expected checksum using `calculate_checksum()` and compares it to the received value. Returns `True` if they match, `False` otherwise.

---

### `slave.py`

Implements the `LINSlave` class. The slave **never initiates** communication; it only listens for headers from the master and responds when addressed.

#### `__init__(serial_port, baud_rate, wakeup_pin)`

```python
self.ser = serial.Serial(serial_port, baudrate=baud_rate, timeout=0.1)
self.frame_handlers = {}   # Dict mapping frame_id -> handler function

GPIO.setmode(GPIO.BCM)
GPIO.setup(self.wakeup_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
```

- Opens UART serial port (same settings as the master).
- Configures the wakeup GPIO pin as **input** with pull-up (slave receives the pulse, master sends it).
- `frame_handlers` is a dictionary: `{ frame_id: callback_function }`.

---

#### `register_frame_handler(frame_id, handler)`

```python
self.frame_handlers[frame_id] = handler
```

Registers a callback function to be called when a specific `frame_id` is received. The callback receives the incoming data (or `None` for header-only frames) and should return the response data bytes (or `None` to send no response).

---

#### `process_frames()`

The main event loop. Runs indefinitely until `KeyboardInterrupt`:

```python
while True:
    frame_id, data = self._receive_header()
    if frame_id in self.frame_handlers:
        response = self.frame_handlers[frame_id](data)
        if response is not None:
            self._send_response(response)
```

For each incoming frame:

1. Waits for a valid header.
2. Looks up the registered handler for the frame ID.
3. Calls the handler with the received data.
4. If the handler returns data, sends it back to the master.

---

#### `_receive_header()`

```python
# Step 1: Wait for BREAK byte
while True:
    if self.ser.in_waiting and self.ser.read(1) == bytes([BREAK_BYTE]):
        break

# Step 2: Check SYNC byte
sync = self.ser.read(1)
if sync != bytes([SYNC_BYTE]):
    raise LINSyncError("Invalid sync byte")

# Step 3: Parse PID
pid_byte = ord(self.ser.read(1))
frame_id = self.parse_pid(pid_byte)
if frame_id is None:
    raise LINParityError("PID parity check failed")

# Step 4: Determine if data follows
if not self.ser.in_waiting:
    return (frame_id, None)   # Header-only: master is requesting data

data = self.ser.read(MAX_FRAME_DATA_LENGTH)
checksum = ord(self.ser.read(1))
if not self.verify_checksum(pid_byte, data, checksum):
    raise LINChecksumError("Checksum verification failed")

return (frame_id, data)
```

The slave synchronizes by polling for the `BREAK_BYTE` (`0x00`), then reads the sync byte and PID. If no more bytes are in the buffer, it knows the master is requesting a response (header-only frame). Otherwise it reads the full data payload and verifies the checksum.

---

#### `_send_response(data)`

```python
checksum = self.calculate_checksum(0, data)   # PID = 0 for slave responses
self.ser.write(data)
self.ser.write(bytes([checksum]))
self.ser.flush()
```

Sends data back to the master as the response to a request frame. Note that the checksum here uses `pid=0`, meaning this implementation uses a **data-only checksum** (without the PID) for slave responses — this is a design choice in this library.

---

#### `parse_pid(pid_byte)` — static method

Extracts the 6-bit frame ID and verifies both parity bits:

```python
frame_id = pid_byte & 0x3F          # Lower 6 bits
p0 = (pid_byte >> 6) & 0x01        # Bit 6
p1 = (pid_byte >> 7) & 0x01        # Bit 7

# Recalculate expected parity
calc_p0 = (frame_id ^ (frame_id>>1) ^ (frame_id>>2) ^ (frame_id>>4)) & 0x01
calc_p1 = ~((frame_id>>1) ^ (frame_id>>3) ^ (frame_id>>4) ^ (frame_id>>5)) & 0x01

if p0 != calc_p0 or p1 != calc_p1:
    return None   # Parity error
return frame_id
```

Returns `None` on parity failure so `_receive_header()` can raise `LINParityError`.

---

### `__init__.py`

The package entry point. It imports and re-exports the public API:

```python
from .master import LINMaster
from .slave import LINSlave
from .exceptions import *
from .constants import *

__all__ = [
    'LINMaster', 'LINSlave',
    'LINError', 'LINChecksumError', 'LINParityError',
    'LINSyncError', 'LINFrameError', 'LINTimeoutError'
]
```

This means users only need to import from `lin_protocol`:

```python
from lin_protocol import LINMaster, LINSlave, LINChecksumError
```

---

## LIN Frame Format

```
+-------+------+-----+-------------------+----------+
| BREAK | SYNC | PID |   DATA (1-8 B)    | CHECKSUM |
+-------+------+-----+-------------------+----------+
  0x00   0x55   8b     1 to 8 bytes         1 byte
 (at 1/4           (6-bit ID + 2 parity)
  baud rate)
```

| Field    | Value     | Description                                    |
| -------- | --------- | ---------------------------------------------- |
| BREAK    | `0x00`    | Sent at 1/4 baud rate — marks start of frame   |
| SYNC     | `0x55`    | Fixed sync byte — `01010101` in binary         |
| PID      | 8-bit     | 6-bit frame ID + P0 (bit6) + P1 (bit7)         |
| DATA     | 1–8 bytes | Payload (absent in header-only/request frames) |
| CHECKSUM | 1 byte    | Inverted carry-around sum over PID + data      |

---

## PID Calculation

Given a 6-bit `frame_id` (0–63):

```
P0 = ID0 XOR ID1 XOR ID2 XOR ID4
P1 = NOT (ID1 XOR ID3 XOR ID4 XOR ID5)

PID = [ P1 | P0 | ID5 | ID4 | ID3 | ID2 | ID1 | ID0 ]
```

Example for `frame_id = 0x10` (16 decimal = `010000` binary):

- P0 = 0 XOR 0 XOR 0 XOR 1 = 1
- P1 = NOT(0 XOR 0 XOR 1 XOR 0) = NOT(1) = 0
- PID = `0b00010000 | (1<<6) | (0<<7)` = `0x50`

---

## Checksum Algorithm

Uses **LIN 2.0 classic checksum** (inverted sum with carry-around):

```
sum = PID
for each data byte:
    sum += byte
    if sum > 255: sum -= 255    # carry-around (not modulo)
checksum = 255 - sum
```

The receiver recomputes the same sum and checks that `sum + received_checksum == 255`.

---

## Usage Examples

### Master — Send a Command

```python
from lin_protocol import LINMaster

master = LINMaster(serial_port='/dev/serial0', baud_rate=19200)

# Send 4 bytes to the slave registered on frame ID 0x10
master.send_command(frame_id=0x10, data=bytes([0x01, 0x02, 0x03, 0x04]))

master.close()
```

### Master — Request Data from Slave

```python
from lin_protocol import LINMaster, LINChecksumError, LINFrameError

master = LINMaster()

try:
    data = master.request_data(frame_id=0x20, expected_data_length=4)
    print("Received:", list(data))
except LINFrameError as e:
    print("Frame error:", e)
except LINChecksumError as e:
    print("Checksum error:", e)
finally:
    master.close()
```

### Slave — Listen and Respond

```python
from lin_protocol import LINSlave

slave = LINSlave(serial_port='/dev/serial0', baud_rate=19200)

# Handler for frame ID 0x10 — receives a command, no response needed
def handle_command(data):
    print("Command received:", list(data))
    return None   # No response

# Handler for frame ID 0x20 — master is requesting data
def handle_request(data):
    return bytes([0xAA, 0xBB, 0xCC, 0xDD])   # Send back 4 bytes

slave.register_frame_handler(0x10, handle_command)
slave.register_frame_handler(0x20, handle_request)

print("Slave listening...")
slave.process_frames()   # Blocks until KeyboardInterrupt

slave.close()
```

---

## Hardware Requirements

| Requirement     | Details                                     |
| --------------- | ------------------------------------------- |
| Platform        | Raspberry Pi (any model with GPIO and UART) |
| UART port       | `/dev/serial0` (hardware UART, not USB)     |
| GPIO pin        | BCM pin 18 — wakeup signal line             |
| Baud rate       | 19200 bps (standard LIN rate, configurable) |
| Python packages | `pyserial`, `RPi.GPIO`                      |

Install dependencies:

```bash
pip install pyserial RPi.GPIO
```

Make sure UART is enabled on the Raspberry Pi:

```bash
sudo raspi-config  # Interface Options -> Serial Port -> Enable
```

---

## Troubleshooting

### RPi Receives Nothing from Slave — "Expected N bytes, got 0"

**Problem: The Linux serial console is stealing all incoming bytes**

#### What happens

By default, Raspberry Pi OS configures the UART as a **serial console** — a system feature that lets you log in to the RPi using a terminal connected to GPIO14/15. This is controlled by a program called `agetty` that runs permanently in the background and reads *every byte* that arrives on the RX pin (GPIO15), treating them as keyboard input for a login session.

Because `agetty` grabs the incoming bytes first, your Python script calls `ser.read()` and finds the buffer empty — even though the slave did send a response.

The TX direction (RPi → slave) is unaffected, which is why the master can send commands successfully but never receives a response.

#### Symptoms

- `[ERR] Expected N bytes, got 0` on every sensor request
- Slave Serial Monitor shows `[REQ] Sensor = ...` confirming it DID send a response
- RPi TX works fine (slave receives commands, LED toggles)
- Loopback test (GPIO14 → GPIO15 jumper wire) returns wrong or no data

#### How to diagnose

Check if the getty service is running:

```bash
sudo systemctl status serial-getty@ttyAMA0.service
```

If the output shows `Active: active (running)` — this is the problem.

#### How to fix

**Step 1:** Find the boot configuration file.

```bash
cat /boot/cmdline.txt 2>/dev/null || cat /boot/firmware/cmdline.txt
```

You will see a line containing `console=serial0,115200`. This is the kernel parameter that activates the serial console at boot.

**Step 2:** Remove it.

```bash
# On older Raspberry Pi OS (Bullseye and earlier):
sudo sed -i 's/console=serial0,115200 //g' /boot/cmdline.txt

# On newer Raspberry Pi OS (Bookworm):
sudo sed -i 's/console=serial0,115200 //g' /boot/firmware/cmdline.txt
```

**Step 3:** Reboot.

```bash
sudo reboot
```

**Step 4:** Verify the service is no longer running.

```bash
sudo systemctl status serial-getty@ttyAMA0.service
# Should show: inactive (dead)
```

**Step 5:** Confirm the UART RX now works with a loopback test. Connect a jumper wire between GPIO14 (pin 8) and GPIO15 (pin 10), then run:

```bash
python3 -c "
import serial, time
s = serial.Serial('/dev/serial0', baudrate=19200, timeout=2.0)
s.write(bytes([0xBB]))
s.flush()
time.sleep(0.1)
d = s.read(1)
print('Sent 0xBB, got:', hex(d[0]) if d else 'nothing')
s.close()
"
```

Expected output: `Sent 0xBB, got: 0xbb`

Remove the jumper wire, reconnect the slave, and run the application normally.
