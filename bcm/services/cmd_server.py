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

    def set_hardware(self, send_lin, send_can):
        """Called by main.py once hardware is ready."""
        self._send_lin = send_lin
        self._send_can = send_can

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
                self._send_lin(frame_id, data)
                logger.info(f"[CMD] Manual LIN TX ID={hex(frame_id)} data={data.hex()}")

        elif cmd == "send_can_frame":
            if self._send_can:
                can_id = int(msg.get("can_id", "0x102"), 16)
                data = msg.get("data", [])
                self._send_can(can_id, data)
                logger.info(f"[CMD] Manual CAN TX ID={hex(can_id)} data={bytes(data).hex()}")

        else:
            logger.warning(f"[CMD] Unknown command: {cmd}")