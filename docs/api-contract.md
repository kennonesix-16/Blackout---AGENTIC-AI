# Blackout Broker API Contract

Schema version: `1.0`

The backend owns a single atomic `TelemetrySnapshot`. The frontend renders that snapshot and never makes dispatch decisions.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Service status, simulator state, and physics mode |
| GET | `/api/health` | Backward-compatible health alias |
| GET | `/api/v1/state` | Most recent atomic snapshot |
| POST | `/api/v1/scenario/reset` | Reset deterministic seed and clear the shock |
| POST | `/api/v1/scenario/start` | Start the managed 10 Hz simulator loop; idempotent |
| POST | `/api/v1/scenario/pause` | Pause the managed simulator loop |
| POST | `/api/v1/chaos` | Inject `feeder_loss`, `feeder_reduction`, `feeder_outage`, `supply_deficit`, `renewable_drop`, or `clear` |
| POST | `/api/v1/scenario/{scenario_id}` | Activate a named scenario |
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
    "power_balance": {"total_demand_kw":280,"available_supply_kw":220,"served_load_kw":220,"unmet_demand_kw":60,"deficit_kw":60},
  "metrics": {"auction_ms":0.4,"emission_ms":0.1,"auction_target_ms":200,"telemetry_target_ms":100,"auction_p50_ms":0.4,"auction_p95_ms":0.6},
    "scenario": {"name":"Ward 4 feeder resilience","phase":"shock","shock_active":true,"shock_label":"Feeder Loss · 50%","seed":42,"physics_mode":"SIMULATION FALLBACK","scenario_id":"feeder_loss"},
    "generators": [{"generator_id":"renewable-ev-fleet","type":"renewable","node_id":"ev-depot","capacity_kw":120,"available_kw":120,"status":"online","allocation_kw":120,"reason":"V2G reserve and renewable-drop scenario policy"}],
    "event_log": [{"decision_id":"trade-12-1","kind":"trade","affected_id":"hospital","decision":"accepted","reason":"accepted by schema, path, capacity, and conservative thermal checks","timestamp":"2026-10-24T00:00:00+00:00"}]
}
```

## Decision semantics

- A `TradeProposal` is created by the deterministic continuous double auction.
- Every proposal creates one `TradeDecision`, accepted or rejected.
- Rejected trades remain visible and include a machine-readable reason string.
- Decision events include a stable decision ID, affected object, decision, reason, and before/after values where available.
- The current MVP uses a conservative graph/path and line-capacity validator. It is explicitly **not AC validation**.
- The midpoint clearing price is a modeled simulation rule, not a tariff or settlement price.

## Power balance semantics

- `total_demand_kw` is the current auction buy quantity.
- `available_supply_kw` is the current auction sell quantity after scenario reductions.
- `served_load_kw` is accepted allocation from the latest clearing cycle only.
- `unmet_demand_kw` and `deficit_kw` are current demand minus latest-cycle served load; they are equivalent in this MVP.
- These fields describe the emergency-market simulation in equivalent kW, not whole-city metering or a continuity guarantee.

## Named scenario IDs

`normal`, `supply_20`, `supply_40`, `feeder_reduction_50`, `feeder_loss`, `feeder_outage`, `renewable_drop`, and `solar_reduction`. Scenario activation is deterministic and replaces previous reductions before recalculating the next clearing cycle.
