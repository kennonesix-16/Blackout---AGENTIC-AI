from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .models import ChaosEvent, ScenarioCommand
from .scenarios import SCENARIOS, get_scenario
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
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "physics_mode": "SIMULATION FALLBACK", "simulator_running": simulator.running, "schema_version": "1.0", "scenario_id": simulator.last_snapshot.scenario.scenario_id}


@app.get("/api/health")
async def api_health() -> dict:
    return await health()


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


@app.post("/api/simulation/start")
async def simulation_start():
    return await start()


@app.post("/api/v1/scenario/pause")
async def pause():
    await simulator.pause()
    return {"status": "paused", "tick": simulator.tick}


@app.post("/api/simulation/pause")
async def simulation_pause():
    return await pause()


@app.post("/api/simulation/reset")
async def simulation_reset(command: ScenarioCommand | None = None):
    return await reset(command)


@app.post("/api/v1/chaos")
async def chaos(event: ChaosEvent):
    return await simulator.inject(event)


@app.post("/api/scenarios/inject")
async def inject_scenario(event: ChaosEvent):
    return await chaos(event)


@app.get("/api/v1/scenarios")
async def scenarios() -> dict:
    return {"scenarios": [{"id": definition.scenario_id, "label": definition.label, "event_type": definition.event_type, "magnitude": definition.magnitude} for definition in SCENARIOS.values()]}


@app.post("/api/v1/scenario/{scenario_id}")
async def activate_scenario(scenario_id: str, command: ScenarioCommand | None = None):
    definition = get_scenario(scenario_id)
    if definition is None:
        raise HTTPException(status_code=400, detail=f"Unknown scenario '{scenario_id}'. Supported IDs: {', '.join(SCENARIOS)}")
    event = ChaosEvent(event_type=definition.event_type, magnitude=definition.magnitude, seed=(command or ScenarioCommand()).seed)
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
