# Blackout Broker frontend

The frontend is a React + TypeScript operations dashboard for the Blackout Broker **simulation**. It does not control electrical equipment and does not make dispatch decisions.

## Run

```bash
npm install
npm run dev
```

Open `http://localhost:5173`. The backend is expected at `http://localhost:8000` by default. Copy `.env.example` to `.env.local` to configure `VITE_API_BASE_URL` and, if needed, `VITE_WS_BASE_URL`.

## Backend contract used

The dashboard uses the implemented contract in `docs/api-contract.md`:

- `GET /health`
- `GET /api/v1/state`
- `POST /api/v1/scenario/start`
- `POST /api/v1/scenario/reset`
- `POST /api/v1/chaos`
- `WS /ws/telemetry`

Telemetry is validated before rendering. The app reconnects with backoff, preserves the last valid snapshot, and clearly shows when it is using the synthetic demo fallback. The current backend does not expose a pause endpoint, so Pause/Resume pauses only the local demo telemetry view and says so in the UI.

## Checks

```bash
npm run typecheck
npm run build
```

## Demo flow

1. Start the frontend without the backend to show the labeled fallback mode.
2. Use **-50% feeder** to show an overloaded line, hospital shortfall, accepted V2G/commercial trades, and a governor rejection.
3. Select nodes in the SVG schematic to inspect their live state.
4. Point to the grid balance chart, modeled clearing midpoint, agent cards, and incident feed.
5. Keep the footer limitation visible: this is a simulation, not a production dispatch controller or safety guarantee.
