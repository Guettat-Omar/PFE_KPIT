import asyncio
import json
import logging
import os
import subprocess
import time
import websockets

from someipy import (
    ServiceBuilder,
    ClientServiceInstance,
    Event,
    EventGroup,
    TransportLayerProtocol,
    connect_to_someipy_daemon,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_someipyd(config_path: str):
    socket_path = "/tmp/someipyd.sock"
    # Remove stale socket if daemon is not running
    if os.path.exists(socket_path):
        os.remove(socket_path)
    subprocess.Popen(
        ["someipyd", "--config", config_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    # Wait for socket to appear
    for _ in range(50):
        if os.path.exists(socket_path):
            break
        time.sleep(0.1)
    # Extra time for daemon to finish internal setup
    time.sleep(1.0)


# -- Must match BCM publisher exactly -----------------------------------------
SERVICE_ID    = 0x1234
...
# -- Must match BCM publisher exactly -----------------------------------------
# If any of these differ from BCM, LCD will never find the service.
SERVICE_ID    = 0x1234
INSTANCE_ID   = 0x0001
EVENT_ID      = 0x8001
EVENTGROUP_ID = 0x0001

LCD_IP        = "10.20.0.39"   # this Pi's IP
DATA_PORT     = 30499          # must match BCM's DATA_PORT

WEBSOCKET_PORT = 8765

# -- Connected WebSocket clients -----------------------------------------------
connected_clients: set = set()


async def websocket_handler(websocket):
    """Accept dashboard browser connections and keep them alive."""
    connected_clients.add(websocket)
    logger.info(f"Dashboard connected: {websocket.remote_address}")
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.discard(websocket)
        logger.info(f"Dashboard disconnected")


async def broadcast_to_dashboard(vehicle_state: dict):
    """Send vehicle state to all connected browser clients."""
    if not connected_clients:
        return
    message = json.dumps(vehicle_state)
    await asyncio.gather(
        *[client.send(message) for client in connected_clients],
        return_exceptions=True
    )


async def start_someip_subscriber():
    """
    Connect to the local someipyd daemon, build the service definition,
    subscribe to BCM's eventgroup, and register a callback.
    """

    # Step 1   Build the EXACT same service definition as BCM.
    # LCD doesn't offer anything  it just needs this definition
    # to know what it's looking for.
    vehicle_state_event = Event(
        id=EVENT_ID,
        protocol=TransportLayerProtocol.UDP
    )
    eventgroup = EventGroup(
        id=EVENTGROUP_ID,
        events=[vehicle_state_event]
    )
    service = (
        ServiceBuilder()
        .with_service_id(SERVICE_ID)
        .with_major_version(1)
        .with_eventgroup(eventgroup)
        .build()
    )

    # Step 2   Connect to LCD's local someipyd daemon.
    logger.info("[SOME/IP] Connecting to someipyd daemon...")
    daemon = await connect_to_someipy_daemon()

    # Step 3   Create the client service instance.
    # LCD's endpoint_ip tells the daemon which interface to use.
    # endpoint_port is where LCD will receive unicast event data.
    client = ClientServiceInstance(
        daemon=daemon,
        service=service,
        instance_id=INSTANCE_ID,
        endpoint_ip=LCD_IP,
        endpoint_port=DATA_PORT,
    )

    # Step 4   Register the callback.
    # This function is called automatically every time BCM sends an event.
    def on_vehicle_state_received(event_id: int, payload: bytes):
        if event_id != EVENT_ID:
            return
        try:
            vehicle_state = json.loads(payload.decode('utf-8'))
            logger.info(f"[SOME/IP] Received: {vehicle_state}")

            # Schedule the WebSocket broadcast from inside the async loop.
            # asyncio.ensure_future() posts it to the running event loop.
            asyncio.ensure_future(broadcast_to_dashboard(vehicle_state))

        except json.JSONDecodeError as e:
            logger.error(f"[SOME/IP] Bad payload: {e}")

    client.register_callback(on_vehicle_state_received)

    # Step 5   Subscribe to BCM's eventgroup.
    # LCD tells the daemon: "When you find Service 0x1234, subscribe to
    # eventgroup 0x0001 and keep the subscription alive for 10 seconds
    # (renewing automatically)."
    client.subscribe_eventgroup(eventgroup, ttl_subscription_seconds=10)
    logger.info(
        f"[SOME/IP] Subscribed to Service 0x{SERVICE_ID:04X} "
        f"EventGroup 0x{EVENTGROUP_ID:04X}"
    )


async def main():
    start_someipyd("/home/rasp2/someipyd_lcd.json")
    await start_someip_subscriber()

    # Start the WebSocket server for the dashboard browser
    ws_server = await websockets.serve(
        websocket_handler,
        "0.0.0.0",      # listen on all interfaces, not just localhost
        WEBSOCKET_PORT
    )
    logger.info(f"[WS] Dashboard server on ws://0.0.0.0:{WEBSOCKET_PORT}")

    # Keep running forever   the callback handles everything
    await asyncio.get_event_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())