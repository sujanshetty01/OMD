from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import endpoints, prompt_iq
from .core.ws_manager import manager
from fastapi import WebSocket, WebSocketDisconnect

app = FastAPI(title="Auto-Classification App")

@app.websocket("/ws/ingestion/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(client_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(client_id)

# ... (middleware stays same)

# CORS for React
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(endpoints.router, prefix="/api")
app.include_router(prompt_iq.router, prefix="/api/ai")

@app.get("/")
def read_root():
    return {"message": "Classifier AI Platform is running"}
