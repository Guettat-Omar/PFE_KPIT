import asyncio, json, logging, websockets
logger = logging.getLogger(__name__)
connected_clients: set = set()

async def websocket_handler(websocket):
    connected_clients.add(websocket)
    logger.warning(f"[WS] Dashboard connected: {websocket.remote_address}")
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.discard(websocket)
        logger.warning("[WS] Dashboard disconnected")

async def broadcast(vehicle_state: dict):
    if not connected_clients:
        return
    message = json.dumps(vehicle_state)
    await asyncio.gather(
        *[client.send(message) for client in connected_clients],
        return_exceptions=True
    )

async def start_websocket_server(port: int):
    server = await websockets.serve(websocket_handler, "0.0.0.0", port)
    logger.warning(f"[WS] State server on ws://0.0.0.0:{port}")
    return server
