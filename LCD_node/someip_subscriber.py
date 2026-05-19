import socket
import struct
import json
import asyncio
import websockets

# SOME/IP constants
MULTICAST_ADDR = '224.0.0.1'
SOMEIP_PORT = 30490
WEBSOCKET_PORT = 8765

# Global set of connected WebSocket clients
connected_clients = set()

async def websocket_handler(websocket, path):
    """Handle new WebSocket connections from the dashboard"""
    connected_clients.add(websocket)
    print(f"Dashboard connected: {websocket.remote_address}")
    try:
        # Keep connection alive, wait for disconnect
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)
        print(f"Dashboard disconnected: {websocket.remote_address}")

async def broadcast_state(vehicle_state):
    """Send state to all connected WebSocket clients"""
    if connected_clients:
        message = json.dumps(vehicle_state)
        # Send to all clients concurrently
        await asyncio.gather(
            *[client.send(message) for client in connected_clients],
            return_exceptions=True
        )

async def someip_receiver():
    """Receive SOME/IP packets and forward to WebSocket clients"""
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', SOMEIP_PORT))
    
    # Join multicast group
    mreq = struct.pack('4sL', socket.inet_aton(MULTICAST_ADDR), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    
    # Make socket non-blocking for asyncio
    sock.setblocking(False)
    
    print(f"Listening for SOME/IP events on {MULTICAST_ADDR}:{SOMEIP_PORT}")
    
    loop = asyncio.get_event_loop()
    
    while True:
        # Wait for data asynchronously
        data = await loop.sock_recv(sock, 2048)
        
        # Parse SOME/IP header
        if len(data) < 16:
            continue
        
        header = data[:16]
        payload = data[16:]
        
        message_id, length, client_id, session_id, proto_ver, iface_ver, msg_type, ret_code = \
            struct.unpack('>IIHHBBBB', header)
        
        service_id = message_id >> 16
        event_id = message_id & 0xFFFF
        
        # Deserialize JSON payload
        try:
            vehicle_state = json.loads(payload.decode('utf-8'))
            print(f"Session {session_id}: {vehicle_state}")
            
            # Forward to WebSocket clients
            await broadcast_state(vehicle_state)
            
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}")

async def main():
    """Run both SOME/IP receiver and WebSocket server concurrently"""
    # Start WebSocket server
    ws_server = await websockets.serve(websocket_handler, 'localhost', WEBSOCKET_PORT)
    print(f"WebSocket server listening on ws://localhost:{WEBSOCKET_PORT}")
    
    # Run SOME/IP receiver
    await someip_receiver()

if __name__ == '__main__':
    asyncio.run(main())