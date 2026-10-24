from __future__ import annotations

import asyncio
import statistics
import time
from collections import deque

from .allocation import AllocationDecisionEngine
from .agents import AgentPolicy, default_agents
from .auction import clear_market
from .engine import EventExplanationEngine
from .models import ChaosEvent, DecisionEvent, GeneratorState, LineState, Metrics, NodeState, Order, PowerBalance, ScenarioStatus, TelemetrySnapshot, TradeDecision, now_iso
from .telemetry import TelemetryHub
from .trading import TradeMatchingEngine
from .topology import LINES, NODES


class Simulator:
    def __init__(self) -> None:
        self.seed = 42
        self.tick = 0
        self.running = False
        self.task: asyncio.Task | None = None
        self.shock_fraction = 0.0
        self.supply_reduction = 0.0
        self.renewable_reduction = 0.0
        self.feeder_outage = False
        self.scenario_id = "normal"
        self.shock_label = "No active shock"
        self.agents: list[AgentPolicy] = default_agents()
        self.decisions: deque[TradeDecision] = deque(maxlen=20)
        self.current_decisions: list[TradeDecision] = []
        self.auction_samples: deque[float] = deque(maxlen=100)
        self.telemetry_samples: deque[float] = deque(maxlen=100)
        self.missed_auction_cycles = 0
        self.event_log: deque[DecisionEvent] = deque(maxlen=50)
        self.matcher = TradeMatchingEngine()
        self.allocator = AllocationDecisionEngine()
        self.explainer = EventExplanationEngine()
        self.last_snapshot = self.snapshot()
        self.telemetry = TelemetryHub()
        self.lock = asyncio.Lock()

    async def start(self) -> None:
        if self.running and self.task and not self.task.done():
            return
        self.running = True
        self.task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

    async def pause(self) -> None:
        await self.stop()

    async def reset(self, seed: int = 42) -> TelemetrySnapshot:
        async with self.lock:
            self.seed = seed
            self.tick = 0
            self.shock_fraction = 0
            self.supply_reduction = 0
            self.renewable_reduction = 0
            self.feeder_outage = False
            self.scenario_id = "normal"
            self.shock_label = "No active shock"
            self.agents = default_agents()
            self.decisions.clear()
            self.current_decisions.clear()
            self.auction_samples.clear()
            self.telemetry_samples.clear()
            self.missed_auction_cycles = 0
            self.event_log.clear()
            self.last_snapshot = self.snapshot()
            return self.last_snapshot

    async def inject(self, event: ChaosEvent) -> TelemetrySnapshot:
        async with self.lock:
            # Scenarios replace each other so repeated injections never compound.
            self.shock_fraction = 0
            self.supply_reduction = 0
            self.renewable_reduction = 0
            self.feeder_outage = False
            if event.event_type == "clear":
                self.scenario_id = "normal"
                self.shock_label = "No active shock"
            else:
                if event.event_type == "supply_deficit":
                    self.supply_reduction = event.magnitude
                    self.scenario_id = "supply_20" if event.magnitude == 0.2 else "supply_40" if event.magnitude == 0.4 else "supply_deficit"
                elif event.event_type in {"feeder_loss", "feeder_reduction"}:
                    self.shock_fraction = event.magnitude
                    self.scenario_id = "feeder_loss" if event.event_type == "feeder_loss" else "feeder_reduction_50"
                elif event.event_type == "feeder_outage":
                    self.shock_fraction = 1.0
                    self.feeder_outage = True
                    self.scenario_id = "feeder_outage"
                elif event.event_type in {"renewable_drop", "solar_reduction"}:
                    self.renewable_reduction = event.magnitude
                    self.scenario_id = "renewable_drop"
                self.shock_label = f"{event.event_type.replace('_', ' ').title()} · {event.magnitude:.0%}"
            self.tick += 1
            self._run_tick_locked()
            self.event_log.appendleft(
                self.explainer.event(
                    decision_id=f"scenario-{self.tick}",
                    kind="scenario",
                    affected_id=event.target_id,
                    decision=self.scenario_id,
                    reason=f"Scenario {self.scenario_id} applied without accumulating prior modifiers.",
                    before={},
                    after={"supply_reduction": self.supply_reduction, "feeder_reduction": self.shock_fraction, "renewable_reduction": self.renewable_reduction},
                )
            )
            self.last_snapshot = self.snapshot()
            self.telemetry.publish(self.last_snapshot)
            return self.last_snapshot

    def subscribe(self) -> asyncio.Queue[TelemetrySnapshot]:
        return self.telemetry.subscribe()

    def unsubscribe(self, queue: asyncio.Queue[TelemetrySnapshot]) -> None:
        self.telemetry.unsubscribe(queue)

    async def _loop(self) -> None:
        last_auction = time.monotonic()
        while self.running:
            started = time.monotonic()
            async with self.lock:
                self.tick += 1
                if started - last_auction >= 0.2:
                    self._run_tick_locked()
                    last_auction = started
                self.last_snapshot = self.snapshot()
                self._broadcast(self.last_snapshot)
            emission_ms = (time.monotonic() - started) * 1000
            self.telemetry_samples.append(emission_ms)
            await asyncio.sleep(0.1)

    def _orders(self) -> list[Order]:
        orders = []
        for agent in self.agents:
            renewable_factor = 1 - self.renewable_reduction if agent.agent_type == "ev" else 1
            quantity = agent.baseline_kw if agent.agent_type == "hospital" else agent.available_kw * (1 - self.supply_reduction) * renewable_factor
            if quantity > 0:
                orders.append(agent.order(self.tick).model_copy(update={"quantity_kw": quantity}))
        return orders

    def _run_tick_locked(self) -> None:
        started = time.monotonic()
        self.current_decisions = []
        orders = self._orders()
        available: dict[str, float] = {}
        for order in orders:
            if order.side == "sell":
                available[order.agent_type] = available.get(order.agent_type, 0) + order.quantity_kw
        feeder_loads: dict[str, float] = {}
        # Keep the auction function directly patchable for deterministic unit tests;
        # TradeMatchingEngine remains the public modular adapter for integrations.
        for proposal in clear_market(orders, self.tick):
            decision = self.allocator.decide(proposal, available, self.shock_fraction, self._line_capacities(), feeder_loads)
            self.current_decisions.append(decision)
            self.decisions.appendleft(decision)
            self.event_log.appendleft(
                self.explainer.event(
                    decision_id=decision.decision_id or decision.trade_id,
                    kind="trade",
                    affected_id=decision.affected_id or proposal.buyer_node_id,
                    decision="accepted" if decision.accepted else "rejected",
                    reason=decision.reason,
                    before=decision.before,
                    after=decision.after,
                )
            )
            if decision.accepted:
                available[decision.seller_id] = max(0, available.get(decision.seller_id, 0) - decision.quantity_kw)
        duration_ms = (time.monotonic() - started) * 1000
        self.auction_samples.append(duration_ms)
        if duration_ms > 200:
            self.missed_auction_cycles += 1
        hospital_served = sum(d.quantity_kw for d in self.current_decisions if d.accepted and d.buyer_id == "hospital")
        self.event_log.appendleft(
            self.explainer.event(
                decision_id=f"allocation-{self.tick}",
                kind="allocation",
                affected_id="hospital",
                decision="prioritized critical demand",
                reason=(
                    "Hospital demand was evaluated before flexible and residential offers; "
                    f"{hospital_served:.0f} kW was feasible and {max(0.0, 280 - hospital_served):.0f} kW remains unmet."
                ),
                before={"requested_kw": 280.0},
                after={"served_kw": hospital_served, "unmet_kw": max(0.0, 280 - hospital_served)},
            )
        )

    def snapshot(self) -> TelemetrySnapshot:
        orders = self._orders()
        demand = sum(order.quantity_kw for order in orders if order.side == "buy")
        supply = sum(order.quantity_kw for order in orders if order.side == "sell")
        served = sum(d.quantity_kw for d in self.current_decisions if d.accepted)
        unmet = max(0, demand - served)
        shock_active = bool(self.shock_fraction or self.supply_reduction or self.renewable_reduction)
        served_hospital = sum(d.quantity_kw for d in self.current_decisions if d.accepted and d.buyer_id == "hospital")
        served_hospital = min(served_hospital, 280)
        curtailed_commercial = min(100, sum(d.quantity_kw for d in self.current_decisions if d.accepted and d.seller_id == "commercial"))
        nodes: list[NodeState] = []
        for spec in NODES:
            if spec.id == "hospital":
                nodes.append(NodeState(id=spec.id, label=spec.label, type=spec.type, x=spec.x, y=spec.y, requested_kw=280, served_kw=served_hospital, unmet_kw=max(0, 280 - served_hospital), status="critical" if self.shock_fraction else "normal"))
            elif spec.id == "ev-depot":
                nodes.append(NodeState(id=spec.id, label=spec.label, type=spec.type, x=spec.x, y=spec.y, soc_pct=78, status="flexible"))
            elif spec.type == "commercial":
                nodes.append(NodeState(id=spec.id, label=spec.label, type=spec.type, x=spec.x, y=spec.y, curtailed_kw=curtailed_commercial, status="responsive"))
            elif spec.type == "residential":
                nodes.append(NodeState(id=spec.id, label=spec.label, type=spec.type, x=spec.x, y=spec.y, requested_kw=60 if "north" in spec.id else 40, status="normal"))
            else:
                nodes.append(NodeState(id=spec.id, label=spec.label, type=spec.type, x=spec.x, y=spec.y, status="shock" if self.shock_fraction else "normal"))
        lines = []
        for line in LINES:
            loading = 0
            if self.shock_fraction and line.id == "line-east-hospital":
                loading = min(130, 72 + self.shock_fraction * 70)
            elif self.shock_fraction and "residential-north" in {line.from_node, line.to_node}:
                loading = 118
            else:
                loading = 28 + (self.tick % 5) * 2
            capacity = self._line_capacities()[line.id]
            if capacity <= 0:
                loading = 0
            status = "overloaded" if capacity <= 0 or loading >= 100 else "warning" if loading >= 80 else "normal"
            lines.append(LineState(id=line.id, from_node=line.from_node, to_node=line.to_node, capacity_kw=round(capacity, 2), loading_pct=round(loading, 1), status=status))
        agents = []
        for agent in self.agents:
            renewable_factor = 1 - self.renewable_reduction if agent.agent_type == "ev" else 1
            agents.append(agent.state(served_kw=served_hospital if agent.agent_type == "hospital" else 0, curtailed_kw=curtailed_commercial if agent.agent_type == "commercial" else 0).model_copy(update={"availability_kw": agent.available_kw * (1 - self.supply_reduction) * renewable_factor, "allocation_reason": "Hospital priority allocation" if agent.agent_type == "hospital" else agent.policy_note}))
        renewable_available = next((agent.available_kw for agent in self.agents if agent.agent_type == "ev"), 0) * (1 - self.supply_reduction) * (1 - self.renewable_reduction)
        conventional_available = max(0.0, supply - renewable_available)
        return TelemetrySnapshot(
            timestamp=now_iso(),
            tick=self.tick,
            nodes=nodes,
            lines=lines,
            agents=agents,
            order_book=orders,
            recent_decisions=list(self.decisions),
            power_balance=PowerBalance(total_demand_kw=demand, available_supply_kw=supply, served_load_kw=served, unmet_demand_kw=unmet, deficit_kw=unmet),
            metrics=Metrics(
                auction_ms=self.auction_samples[-1] if self.auction_samples else 0,
                emission_ms=self.telemetry_samples[-1] if self.telemetry_samples else 0,
                telemetry_age_ms=0,
                auction_samples=len(self.auction_samples),
                telemetry_samples=len(self.telemetry_samples),
                auction_p50_ms=_percentile(self.auction_samples, 50),
                auction_p95_ms=_percentile(self.auction_samples, 95),
                telemetry_p50_ms=_percentile(self.telemetry_samples, 50),
                telemetry_p95_ms=_percentile(self.telemetry_samples, 95),
                missed_auction_cycles=self.missed_auction_cycles,
            ),
            scenario=ScenarioStatus(name="Ward 4 feeder resilience", phase="shock" if shock_active else "baseline", shock_active=shock_active, shock_label=self.shock_label, seed=self.seed, physics_mode="SIMULATION FALLBACK", scenario_id=self.scenario_id),
            generators=[
                GeneratorState(generator_id="renewable-ev-fleet", type="renewable", node_id="ev-depot", capacity_kw=120, available_kw=max(0.0, renewable_available), status="derated" if self.renewable_reduction else "online", allocation_kw=min(renewable_available, served), reason="V2G reserve and renewable-drop scenario policy"),
                GeneratorState(generator_id="conventional-flexibility", type="conventional", node_id="substation-east", capacity_kw=200, available_kw=max(0.0, conventional_available), status="derated" if self.supply_reduction else "online", allocation_kw=min(conventional_available, max(0.0, served - renewable_available)), reason="Dispatchable synthetic supply after grid constraints"),
            ],
            event_log=list(self.event_log),
        )

    def _broadcast(self, snapshot: TelemetrySnapshot) -> None:
        self.telemetry.publish(snapshot)

    def _line_capacities(self) -> dict[str, float]:
        # The named Ward 4 feeder scenario derates the hospital feeder. Other
        # paths keep their physical capacity, while the governor still applies
        # a conservative system-wide safety margin during a shock.
        capacities = {
            line.id: line.capacity_kw * (1 - self.shock_fraction) if line.id == "line-east-hospital" else line.capacity_kw
            for line in LINES
        }
        if self.feeder_outage:
            capacities["line-east-hospital"] = 0.0
        return capacities


def _percentile(values: deque[float], percentile: int) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((percentile / 100) * (len(ordered) - 1)))
    return round(statistics.median([ordered[index], ordered[min(index + 1, len(ordered) - 1)]]), 3)
