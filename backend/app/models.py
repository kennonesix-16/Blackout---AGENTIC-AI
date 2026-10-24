from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    decision_id: str | None = None
    affected_id: str | None = None
    decision_type: Literal["trade", "allocation", "scenario"] = "trade"
    before: dict[str, float] = Field(default_factory=dict)
    after: dict[str, float] = Field(default_factory=dict)


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
    allocation_reason: str = ""


class GeneratorState(BaseModel):
    generator_id: str
    type: Literal["renewable", "conventional"]
    node_id: str
    capacity_kw: float = Field(ge=0)
    available_kw: float = Field(ge=0)
    status: str = "online"
    allocation_kw: float = Field(ge=0)
    reason: str = ""


class DecisionEvent(BaseModel):
    decision_id: str
    kind: Literal["monitoring", "allocation", "trade", "scenario"]
    affected_id: str
    decision: str
    reason: str
    timestamp: str
    before: dict[str, float] = Field(default_factory=dict)
    after: dict[str, float] = Field(default_factory=dict)


class ChaosEvent(BaseModel):
    event_type: Literal[
        "feeder_loss",
        "feeder_reduction",
        "feeder_outage",
        "supply_deficit",
        "renewable_drop",
        "solar_reduction",
        "clear",
    ]
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
    scenario_id: str = "normal"


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


class PowerBalance(BaseModel):
    """Current emergency-market balance in equivalent kW, not whole-city metering."""

    model_config = ConfigDict(allow_inf_nan=False)

    total_demand_kw: float = Field(ge=0)
    available_supply_kw: float = Field(ge=0)
    served_load_kw: float = Field(ge=0)
    unmet_demand_kw: float = Field(ge=0)
    deficit_kw: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_invariants(self) -> "PowerBalance":
        if self.served_load_kw > self.total_demand_kw:
            raise ValueError("served_load_kw cannot exceed total_demand_kw")
        if self.served_load_kw > self.available_supply_kw:
            raise ValueError("served_load_kw cannot exceed available_supply_kw")
        expected_unmet = max(0.0, self.total_demand_kw - self.served_load_kw)
        if abs(self.unmet_demand_kw - expected_unmet) > 1e-9:
            raise ValueError("unmet_demand_kw must equal max(0, total_demand_kw - served_load_kw)")
        if abs(self.deficit_kw - self.unmet_demand_kw) > 1e-9:
            raise ValueError("deficit_kw must equal unmet_demand_kw")
        return self


class TelemetrySnapshot(BaseModel):
    schema_version: str = SCHEMA_VERSION
    timestamp: str
    tick: int
    nodes: list[NodeState]
    lines: list[LineState]
    agents: list[AgentState]
    order_book: list[Order]
    recent_decisions: list[TradeDecision]
    power_balance: PowerBalance
    metrics: Metrics
    scenario: ScenarioStatus
    generators: list[GeneratorState] = Field(default_factory=list)
    event_log: list[DecisionEvent] = Field(default_factory=list)


class ScenarioCommand(BaseModel):
    seed: int = 42
