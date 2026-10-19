from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json

ws_router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WEBSOCKET] Tablet connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print("[WEBSOCKET] Tablet disconnected.")

    async def broadcast_state(self, state_payload: dict):
        """Sends the JSON payload to the Android Tablet."""
        for connection in self.active_connections:
            try:
                await connection.send_json(state_payload)
            except Exception as e:
                print(f"[WEBSOCKET] Failed to send message: {e}")

manager = ConnectionManager()

@ws_router.websocket("/ws/kiosk")
async def kiosk_endpoint(websocket: WebSocket):
    """The endpoint the Android app connects to."""
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect much data FROM the tablet via WS, 
            # but we must keep the loop open to listen for disconnects.
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)