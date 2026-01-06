from fastapi import WebSocket
from typing import List, Dict
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_update(self, client_id: str, step: str, status: str = "processing", data: dict = None):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            message = {
                "step": step,
                "status": status,
                "data": data
            }
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                print(f"Error sending WS update: {e}")
                self.disconnect(client_id)

manager = ConnectionManager()
