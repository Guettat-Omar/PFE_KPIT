import asyncio
import json
import logging
import threading
import websockets

logger = logging.getLogger(__name__)

CMD_PORT = 8766   # must match ws://10.20.0.41:8766 in dashboard HTML


class CmdServer:
    """
    WebSocket server that receives fault injection commands from the browser.

    Browser sends:  {"cmd": "inject_fault",  "fault_id": 1}
                    {"cmd": "clear_fault",   "fault_id": 1}
                    {"cmd": "clear_all_faults"}
                    {"cmd": "send_lin_frame", "frame_id": "0x12", "data": [1,2,3,4,5]}
                    {"cmd": "send_can_frame", "can_id": "0x102",  "data": [0,0,0,0,0,0,0]}

    BCM replies:    {"type": "fault_ack", "fault_id": 1, "active": true}
    """

    def __init__(self, fault_injector):
        # fault_injector is the FaultInjector instance from main.py
        self._fi = fault_injector
        self._loop = None

        # These are set by main.py after hardware is initialized
        self._send_lin = None   # function: send_lin(frame_id, data)
        self._send_can = None   # function: send_can(arb_id, data)
        self._get_seq_counter = None  # function that returns current BCM seq counter

    def set_hardware(self, send_lin, send_can, get_seq_counter=None):
        """Called by main.py once hardware is ready."""
        self._send_lin = send_lin
        self._send_can = send_can
        self._get_seq_counter = get_seq_counter

    def start(self):
        """Start WebSocket server in a background thread."""
        thread = threading.Thread(
            target=self._run_loop,
            name="cmd-server",
            daemon=True
        )
        thread.start()
        logger.info(f"[CMD] WebSocket command server starting on port {CMD_PORT}")

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())

    async def _serve(self):
        async with websockets.serve(self._handle_client, "0.0.0.0", CMD_PORT):
            logger.info(f"[CMD] Listening on ws://0.0.0.0:{CMD_PORT}")
            await asyncio.get_event_loop().create_future()  # run forever

    async def _handle_client(self, websocket):
        """Handle one browser connection. Runs until browser disconnects."""
        logger.info(f"[CMD] Browser connected: {websocket.remote_address}")
        try:
            async for raw_msg in websocket:
                await self._dispatch(websocket, raw_msg)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            logger.info(f"[CMD] Browser disconnected")

    async def _dispatch(self, websocket, raw_msg: str):
        """Parse a command and act on it."""
        try:
            msg = json.loads(raw_msg)
            logger.warning(f"[CMD] Received: {msg}")
        except json.JSONDecodeError:
            logger.warning(f"[CMD] Invalid JSON: {raw_msg}")
            return

        cmd = msg.get("cmd")

        if cmd == "inject_fault":
            fault_id = msg.get("fault_id")
            ok = self._fi.inject(fault_id)
            # Send acknowledgement back to dashboard
            await websocket.send(json.dumps({
                "type": "fault_ack",
                "fault_id": fault_id,
                "active": True
            }))

        elif cmd == "clear_fault":
            fault_id = msg.get("fault_id")
            self._fi.clear(fault_id)
            await websocket.send(json.dumps({
                "type": "fault_ack",
                "fault_id": fault_id,
                "active": False
            }))

        elif cmd == "clear_all_faults":
            self._fi.clear_all()

        elif cmd == "send_lin_frame":
            if self._send_lin:
                frame_id = int(msg.get("frame_id", "0x12"), 16)
                data = bytes(msg.get("data", []))
                repeat = int(msg.get("repeat", 5))  # send 5 times by default
                # Freeze LIN scheduler
                self._fi.lin_freeze.set()
                await asyncio.sleep(0.025)  # wait for current cycle to finish
                # Send frame multiple times to ensure motor moves
                for _ in range(repeat):
                    self._send_lin(frame_id, data)
                    await asyncio.sleep(0.012)  # 12ms between frames
                self._fi.lin_freeze.clear()
                logger.warning(f"[CMD] Manual LIN TX ID={hex(frame_id)} data={data.hex()} x{repeat}")
            else:
                logger.warning("[CMD] send_lin is None  set_hardware() was not called")

        elif cmd == "send_can_frame":
            if self._send_can:
                can_id = int(msg.get("can_id", "0x102"), 16)
                data = msg.get("data", [])
                if can_id == 0x102 and len(data) == 8:
                    data = data[:7]
                # For LIGHT_CMD — patch sequence counter to match BCM's current counter
                if can_id == 0x102 and len(data) == 7 and self._get_seq_counter:
                    current_seq = self._get_seq_counter()
                    next_seq = (current_seq + 1) % 16
                    # Reverse to find seq byte position
                    # In reversed payload: seq is at index 5 (original index 1 after reversal)
                    # Recalculate CRC with new seq
                    from bcm.utils.crc import calculate_crc8
                    # Un-reverse to get original order
                    original = list(reversed(data))
                    original[5] = next_seq  # seq counter at index 5
                    new_crc = calculate_crc8(bytes(original[:6]))
                    original[6] = new_crc
                    # Re-reverse
                    data = list(reversed(original))
                # Freeze BCM CAN output
                if can_id == 0x102:
                    self._fi.can_freeze.set()
                    await asyncio.sleep(0.050)
                self._send_can(can_id, data)
                logger.warning(f"[CMD] Manual CAN TX ID={hex(can_id)} data={bytes(data).hex()}")
                if can_id == 0x102:
                    await asyncio.sleep(0.100)
                    self._fi.can_freeze.clear()
        else:
            logger.warning(f"[CMD] Unknown command: {cmd}")