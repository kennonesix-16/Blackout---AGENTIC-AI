# Blackout Broker

Blackout Broker is a local-first demonstrator of an emergency energy marketplace. It models a hospital, EV fleet V2G, commercial demand response, residential loads, and two substations on an eight-bus synthetic city topology.

> **Honest scope:** this is a simulation of market allocation and simulated grid constraints. It is not a production dispatch controller, protection system, electrical safety certification, legally valid tariff, or guarantee of hospital continuity.

## What is implemented

- Python 3.9+ backend with FastAPI endpoints and a managed WebSocket telemetry hub (Python 3.11 is also supported).
- Pydantic schemas for orders, trade proposals/decisions, agent state, generators, chaos events, scenario status, decision events, and atomic telemetry snapshots.
- Deterministic seedable personas and a continuous double auction using a transparent midpoint clearing price.
- Eight named buses: two substations, Ward 4 hospital, EV depot, two commercial sites, and two residential sites.
- Modular monitoring, allocation, trade-matching, and explanation engines with inventory, path, feeder-capacity, and conservative thermal checks.
- A scripted feeder-loss event that produces accepted trades and a deterministic rejected residential trade.
- React dashboard with a first-class local SVG topology fallback; Mapbox is not required.
- Measured auction and telemetry samples with p50/p95 fields. Targets are displayed separately from observed values.

## Run locally

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run typecheck
npm run dev
```

Open `http://localhost:5173` after starting both processes. The dashboard connects to `http://localhost:8000` by default. Copy `frontend/.env.example` to `frontend/.env.local` only when overriding the backend or WebSocket origin; the supported variables are `VITE_API_BASE_URL` and `VITE_WS_BASE_URL`.

## API and scenarios

The frontend-compatible contract is documented in [`docs/api-contract.md`](docs/api-contract.md). The primary routes are:

- `GET /health` and `GET /api/health`
- `GET /api/v1/state`
- `POST /api/v1/scenario/start` and `POST /api/v1/scenario/pause`
- `POST /api/v1/scenario/reset`
- `POST /api/v1/chaos` and `POST /api/scenarios/inject`
- `POST /api/v1/scenario/{scenario_id}`
- `WS /ws/telemetry`

Supported scenario IDs are `normal`, `supply_20`, `supply_40`, `feeder_reduction_50`, `feeder_loss`, `feeder_outage`, `renewable_drop`, and `solar_reduction` (the last is a frontend-compatible alias). For example:

```bash
curl -X POST http://localhost:8000/api/v1/scenario/supply_40
curl -X POST http://localhost:8000/api/v1/chaos \
  -H 'Content-Type: application/json' \
  -d '{"event_type":"feeder_loss","target_id":"ward-4-feeder","magnitude":0.5,"units":"fraction","seed":42}'
```

All power values are instantaneous `kW`; prices are modeled `₹/kWh` midpoint values. The simulator is deterministic for a given seed, and scenario changes replace prior modifiers rather than accumulating them.

## Two-minute demo

1. Start the backend and frontend; confirm `LIVE TELEMETRY`, `BACKEND CONNECTED`, and `SIMULATION FALLBACK`.
2. Show the eight-bus SVG topology, hospital request, EV SoC, commercial flexibility, and order book.
3. Click **-20% supply** to show a real shortage, hospital prioritization, and honest unmet demand. Then click **-50% feeder** to show a red shock state, changed feeder utilization, accepted trades, and a rejected trade.
4. Read the decision feed: accepted V2G/commercial trades are committed; the residential-north candidate is rejected for a thermal line limit.
5. Click **Normal** or **Reset** and show the hospital returning to full allocation with zero deficit.
6. Point to measured auction/telemetry timing and explain that 200 ms / 100 ms are targets, not guarantees.
7. Finish with the limitation statement in the footer: this is not production grid control or a continuity guarantee.

## Checks

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
PYTHONPATH=. .venv/bin/python scripts/smoke_test.py
cd frontend && npm run typecheck && npm run build
```

No hosted deployment configuration is included; this MVP is intended for local judging unless the team chooses a separate platform. Do not present a deployment as complete unless a hosted URL has been started and health/WebSocket checks have been verified.

## Physics and agent caveats

The backend reports `SIMULATION FALLBACK`. It uses a NetworkX graph and documented synthetic line capacities instead of pandapower AC load flow. No claim of AC validation is made. Agent policies are deterministic and structured; no LLM is placed in the 200 ms clearing path. LangGraph is optional and intentionally not required for this bounded MVP.
