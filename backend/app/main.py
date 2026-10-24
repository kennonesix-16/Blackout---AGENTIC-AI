from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .models import ChaosEvent, ScenarioCommand
from .simulation import Simulator


simulator = Simulator()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await simulator.start()
    yield
    await simulator.stop()


app = FastAPI(title="Blackout Broker API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "physics_mode": "SIMULATION FALLBACK", "simulator_running": simulator.running, "schema_version": "1.0"}


@app.get("/api/v1/state")
async def state():
    return simulator.last_snapshot


@app.post("/api/v1/scenario/reset")
async def reset(command: ScenarioCommand | None = None):
    return await simulator.reset((command or ScenarioCommand()).seed)


@app.post("/api/v1/scenario/start")
async def start():
    await simulator.start()
    return {"status": "running", "tick": simulator.tick}


@app.post("/api/v1/chaos")
async def chaos(event: ChaosEvent):
    return await simulator.inject(event)


@app.websocket("/ws/telemetry")
async def telemetry(websocket: WebSocket):
    await websocket.accept()
    queue = simulator.subscribe()
    try:
        await websocket.send_json(simulator.last_snapshot.model_dump())
        while True:
            snapshot = await queue.get()
            await websocket.send_json(snapshot.model_dump())
    except WebSocketDisconnect:
        pass
    finally:
        simulator.unsubscribe(queue)
