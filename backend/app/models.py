from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


SCHEMA_VERSION = "1.0"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Order(BaseModel):
    id: str
    timestamp: str
    node_id: str
    side: Literal["buy", "sell"]
    quantity_kw: float = Field(gt=0)
    price_per_kwh: float = Field(ge=0)
    status: Literal["open", "filled", "partial", "rejected"] = "open"
    agent_type: str


class TradeProposal(BaseModel):
    trade_id: str
    buyer_id: str
    seller_id: str
    quantity_kw: float = Field(gt=0)
    clearing_price: float = Field(ge=0)
    buyer_node_id: str
    seller_node_id: str
    timestamp: str


class TradeDecision(BaseModel):
    trade_id: str
    buyer_id: str
    seller_id: str
    quantity_kw: float = Field(gt=0)
    clearing_price: float = Field(ge=0)
    accepted: bool
    reason: str
    physics_mode: str
    timestamp: str


class NodeState(BaseModel):
    id: str
    label: str
    type: str
    x: float
    y: float
    requested_kw: float = 0
    served_kw: float = 0
    unmet_kw: float = 0
    soc_pct: float | None = None
    curtailed_kw: float = 0
    status: str = "normal"


class LineState(BaseModel):
    id: str
    from_node: str
    to_node: str
    capacity_kw: float
    loading_pct: float
    status: Literal["normal", "warning", "overloaded"]


class AgentState(BaseModel):
    agent_id: str
    type: str
    node_id: str
    requested_kw: float = 0
    served_kw: float = 0
    availability_kw: float = 0
    soc_pct: float | None = None
    curtailed_kw: float = 0
    policy_note: str = ""


class ChaosEvent(BaseModel):
    event_type: Literal["feeder_loss", "supply_deficit", "clear"]
    target_id: str = "ward-4-feeder"
    magnitude: float = Field(ge=0, le=1)
    units: str = "fraction"
    seed: int = 42


class ScenarioStatus(BaseModel):
    name: str
    phase: str
    shock_active: bool
    shock_label: str
    seed: int
    physics_mode: str


class Metrics(BaseModel):
    auction_ms: float
    emission_ms: float
    telemetry_age_ms: float
    auction_target_ms: float = 200
    telemetry_target_ms: float = 100
    auction_samples: int
    telemetry_samples: int
    auction_p50_ms: float
    auction_p95_ms: float
    telemetry_p50_ms: float
    telemetry_p95_ms: float
    missed_auction_cycles: int


class TelemetrySnapshot(BaseModel):
    schema_version: str = SCHEMA_VERSION
    timestamp: str
    tick: int
    nodes: list[NodeState]
    lines: list[LineState]
    agents: list[AgentState]
    order_book: list[Order]
    recent_decisions: list[TradeDecision]
    metrics: Metrics
    scenario: ScenarioStatus


class ScenarioCommand(BaseModel):
    seed: int = 42
