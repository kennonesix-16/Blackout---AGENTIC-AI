# Blackout Broker

Blackout Broker is a local-first demonstrator of an emergency energy marketplace. It models a hospital, EV fleet V2G, commercial demand response, residential loads, and two substations on an eight-bus synthetic city topology.

> **Honest scope:** this is a simulation of market allocation and simulated grid constraints. It is not a production dispatch controller, protection system, electrical safety certification, legally valid tariff, or guarantee of hospital continuity.

## What is implemented

- Python 3.11 backend with FastAPI endpoints and a managed WebSocket telemetry hub.
- Pydantic schemas for orders, trade proposals/decisions, agent state, chaos events, scenario status, and atomic telemetry snapshots.
- Deterministic seedable personas and a continuous double auction using a transparent midpoint clearing price.
- Eight named buses: two substations, Ward 4 hospital, EV depot, two commercial sites, and two residential sites.
- Safety governor with schema, inventory, path, and conservative line-capacity checks.
- A scripted feeder-loss event that produces accepted trades and a deterministic rejected residential trade.
- React dashboard with a first-class local SVG topology fallback; Mapbox is not required.
- Measured auction and telemetry samples with p50/p95 fields. Targets are displayed separately from observed values.

## Run locally

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` after starting both processes. The dashboard connects to `http://localhost:8000` by default. Set `VITE_API_URL` to use another backend origin.

## Two-minute demo

1. Start the backend and frontend; confirm `LIVE TELEMETRY` and `SIMULATION FALLBACK`.
2. Show the eight-bus SVG topology, hospital request, EV SoC, commercial flexibility, and order book.
3. Click **Inject feeder loss**. The UI should show a red shock state and changed feeder utilization.
4. Read the decision feed: accepted V2G/commercial trades are committed; the residential-north candidate is rejected for a thermal line limit.
5. Point to measured auction/telemetry timing and explain that 200 ms / 100 ms are targets, not guarantees.
6. Finish with the limitation statement in the footer: this is not production grid control or a continuity guarantee.

## Checks

```bash
PYTHONPATH=. pytest -q backend/tests
PYTHONPATH=. python scripts/smoke_test.py
cd frontend && npm run build
```

The environment used to assemble this workspace did not have the Python or Node dependencies preinstalled. If package installation is unavailable, the source and commands above remain the reproducible setup path; run the checks after network/package access is restored.

## Physics and agent caveats

The backend reports `SIMULATION FALLBACK`. It uses a NetworkX graph and documented synthetic line capacities instead of pandapower AC load flow. No claim of AC validation is made. Agent policies are deterministic and structured; no LLM is placed in the 200 ms clearing path. LangGraph is optional and intentionally not required for this bounded MVP.
