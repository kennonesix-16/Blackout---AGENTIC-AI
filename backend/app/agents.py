from __future__ import annotations

from dataclasses import dataclass

from .models import AgentState, Order, now_iso


@dataclass
class AgentPolicy:
    agent_id: str
    agent_type: str
    node_id: str
    baseline_kw: float
    available_kw: float = 0
    price: float = 0
    soc_pct: float | None = None
    policy_note: str = ""

    def state(self, served_kw: float = 0, curtailed_kw: float = 0) -> AgentState:
        return AgentState(
            agent_id=self.agent_id,
            type=self.agent_type,
            node_id=self.node_id,
            requested_kw=self.baseline_kw if self.agent_type in {"hospital", "residential"} else 0,
            served_kw=served_kw,
            availability_kw=self.available_kw,
            soc_pct=self.soc_pct,
            curtailed_kw=curtailed_kw,
            policy_note=self.policy_note,
        )

    def order(self, tick: int) -> Order:
        side = "buy" if self.agent_type == "hospital" else "sell"
        quantity = self.baseline_kw if side == "buy" else self.available_kw
        return Order(
            id=f"{self.agent_id}-order-{tick}",
            timestamp=now_iso(),
            node_id=self.node_id,
            side=side,
            quantity_kw=quantity,
            price_per_kwh=self.price,
            status="open",
            agent_type=self.agent_type,
        )


def default_agents() -> list[AgentPolicy]:
    return [
        AgentPolicy("hospital-ward4", "hospital", "hospital", 280, price=0.60, policy_note="inelastic critical load; priority policy"),
        AgentPolicy("ev-fleet", "ev", "ev-depot", 0, available_kw=120, price=0.18, soc_pct=78, policy_note="V2G offer limited by reserve SoC and degradation cost"),
        AgentPolicy("commercial-north-hvac", "commercial", "commercial-north", 0, available_kw=100, price=0.25, policy_note="negawatt offer limited by HVAC comfort budget"),
        AgentPolicy("residential-north", "residential", "residential-north", 60, available_kw=60, price=0.32, policy_note="modest response; feeder path intentionally constrained"),
        AgentPolicy("residential-south", "residential", "residential-south", 40, available_kw=40, price=0.35, policy_note="transparent residential curtailment policy"),
    ]
