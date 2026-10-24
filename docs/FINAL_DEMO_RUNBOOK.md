# Blackout Broker — Final Demo Runbook

## Goal

Show a deterministic emergency electricity market reacting to a supply shortage and feeder constraint, protecting hospital demand first, rejecting an infeasible trade with an explanation, and recovering after reset.

This is a simulation. It is not production grid control, AC load-flow validation, a tariff/settlement system, or a continuity guarantee.

## Launch

Use two local processes from the repository root.

### Backend

```bash
python3 -m venv .venv                 # first run only
source .venv/bin/activate
python -m pip install -r backend/requirements.txt  # first run only
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install                            # first run only
npm run dev
```

Open `http://localhost:5173`. The backend health endpoint is `http://localhost:8000/health`.

Expected connected indicators:

- `LIVE TELEMETRY`
- `BACKEND CONNECTED`
- `PHYSICS MODE · SIMULATION FALLBACK`

If the backend is not running, the dashboard intentionally shows a labeled synthetic demo fallback. Do not claim that fallback data is live backend data.

## Presentation sequence

1. **Normal operation**
   - Start with the baseline dashboard.
   - Point out the eight-node topology, order book, modeled midpoint price, and hospital allocation.
   - Baseline should show full hospital service and zero market deficit after the first clearing cycle.

2. **Supply shortage**
   - Click `-20% supply`.
   - Expected: available supply falls from the baseline, deficit/unmet demand becomes visible, scenario label changes to `Supply Deficit · 20%`, and the hospital remains the highest-priority buyer.
   - Use `-40% supply` if the judges want a larger shortage.

3. **Feeder-constrained trading**
   - Click `-50% feeder`.
   - Expected: shock state becomes active, feeder loading changes, V2G and commercial trades may be accepted, and the residential candidate is rejected with an explicit thermal/conservative feeder reason.
   - Open the `Why this trade?` panel and explain that the governor validates seller inventory, graph path, and feeder capacity before committing the trade.

4. **Complete outage, if time permits**
   - Click `Outage`.
   - Expected: the Ward 4 feeder capacity becomes `0 kW`, the line is marked overloaded/out of service, and hospital unmet demand is reported honestly rather than hidden.

5. **Recovery**
   - Click `Normal` or `Reset`.
   - Expected: shock label clears and capacities return to baseline. `Reset` sets the tick and decision history back to zero; wait for the next live clearing update (about one second) to see the hospital return to full allocation with zero deficit.

6. **Transparency close**
   - Point to accepted/rejected trade counts, incident feed, and observed auction/telemetry timings.
   - State clearly that the timings are measured simulation observations and the 200 ms/100 ms values are targets, not guarantees.

## API/WebSocket smoke checks

```text
GET  http://localhost:8000/health
GET  http://localhost:8000/api/v1/state
POST http://localhost:8000/api/v1/scenario/start
POST http://localhost:8000/api/v1/scenario/pause
POST http://localhost:8000/api/v1/scenario/reset
POST http://localhost:8000/api/v1/scenario/supply_20
POST http://localhost:8000/api/v1/scenario/feeder_loss
POST http://localhost:8000/api/v1/scenario/feeder_outage
POST http://localhost:8000/api/v1/scenario/renewable_drop
WS   ws://localhost:8000/ws/telemetry
```

The WebSocket sends a complete JSON `TelemetrySnapshot` immediately and then fresh snapshots while the simulator is running. Client disconnects are isolated from the simulation.

## Troubleshooting

- **Dashboard says demo fallback:** confirm the backend is running on port `8000`, then refresh the page.
- **No live telemetry:** check `/health`, then verify the browser is using `ws://localhost:8000/ws/telemetry`.
- **Controls appear to do nothing:** confirm the header says `BACKEND CONNECTED`; otherwise the dashboard is intentionally using local mock behavior.
- **Port already in use:** stop the existing process or use a different backend port and set `VITE_API_BASE_URL` plus `VITE_WS_BASE_URL` in `frontend/.env.local`.
- **Frontend build dependency issue:** run `npm install` in `frontend` before `npm run typecheck`/`npm run build`.

## Checks before submission

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
PYTHONPATH=. .venv/bin/python scripts/smoke_test.py
cd frontend && npm run typecheck && npm run build
```

## Remaining submission blocker

The local branch `feature/decision-transparency` contains the implementation commits, but the remote branch must be checked before claiming GitHub synchronization. The repository is not considered updated unless the remote branch visibly contains the final commit hash.
