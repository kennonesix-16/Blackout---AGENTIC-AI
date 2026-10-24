# Blackout Broker API Contract

Schema version: `1.0`

The backend owns a single atomic `TelemetrySnapshot`. The frontend renders that snapshot and never makes dispatch decisions.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Service status, simulator state, and physics mode |
| GET | `/api/v1/state` | Most recent atomic snapshot |
| POST | `/api/v1/scenario/reset` | Reset deterministic seed and clear the shock |
| POST | `/api/v1/scenario/start` | Start the managed 10 Hz simulator loop |
| POST | `/api/v1/chaos` | Inject `feeder_loss`, `supply_deficit`, or `clear` |
| WS | `/ws/telemetry` | Full snapshot stream; target cadence is 100 ms |

## Chaos request

```json
{
  "event_type": "feeder_loss",
  "target_id": "ward-4-feeder",
  "magnitude": 0.5,
  "units": "fraction",
  "seed": 42
}
```

## Snapshot shape

```json
{
  "schema_version": "1.0",
  "timestamp": "2026-10-24T00:00:00+00:00",
  "tick": 12,
  "nodes": [{"id":"hospital","type":"hospital","requested_kw":280,"served_kw":260,"unmet_kw":20}],
  "lines": [{"id":"line-east-hospital","from_node":"substation-east","to_node":"hospital","capacity_kw":420,"loading_pct":107,"status":"overloaded"}],
  "agents": [{"agent_id":"ev-fleet","type":"ev","node_id":"ev-depot","availability_kw":120,"soc_pct":78}],
  "order_book": [],
  "recent_decisions": [{"trade_id":"trade-12-1","accepted":true,"reason":"accepted by schema, path, capacity, and conservative thermal checks"}],
  "metrics": {"auction_ms":0.4,"emission_ms":0.1,"auction_target_ms":200,"telemetry_target_ms":100,"auction_p50_ms":0.4,"auction_p95_ms":0.6},
  "scenario": {"name":"Ward 4 feeder resilience","phase":"shock","shock_active":true,"shock_label":"Feeder Loss · 50%","seed":42,"physics_mode":"SIMULATION FALLBACK"}
}
```

## Decision semantics

- A `TradeProposal` is created by the deterministic continuous double auction.
- Every proposal creates one `TradeDecision`, accepted or rejected.
- Rejected trades remain visible and include a machine-readable reason string.
- The current MVP uses a conservative graph/path and line-capacity validator. It is explicitly **not AC validation**.
- The midpoint clearing price is a modeled simulation rule, not a tariff or settlement price.
