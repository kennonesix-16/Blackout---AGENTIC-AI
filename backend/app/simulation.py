from __future__ import annotations

import asyncio
import statistics
import time
from collections import deque

from .agents import AgentPolicy, default_agents
from .auction import clear_market
from .governor import validate_trade
from .models import ChaosEvent, LineState, Metrics, NodeState, Order, PowerBalance, ScenarioStatus, TelemetrySnapshot, TradeDecision, now_iso
from .topology import LINES, NODES


class Simulator:
    def __init__(self) -> None:
        self.seed = 42
        self.tick = 0
        self.running = False
        self.task: asyncio.Task | None = None
        self.shock_fraction = 0.0
        self.supply_reduction = 0.0
        self.shock_label = "No active shock"
        self.agents: list[AgentPolicy] = default_agents()
        self.decisions: deque[TradeDecision] = deque(maxlen=20)
        self.current_decisions: list[TradeDecision] = []
        self.auction_samples: deque[float] = deque(maxlen=100)
        self.telemetry_samples: deque[float] = deque(maxlen=100)
        self.missed_auction_cycles = 0
        self.last_snapshot = self.snapshot()
        self.subscribers: set[asyncio.Queue[TelemetrySnapshot]] = set()
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

    async def reset(self, seed: int = 42) -> TelemetrySnapshot:
        async with self.lock:
            self.seed = seed
            self.tick = 0
            self.shock_fraction = 0
            self.supply_reduction = 0
            self.shock_label = "No active shock"
            self.agents = default_agents()
            self.decisions.clear()
            self.current_decisions.clear()
            self.auction_samples.clear()
            self.telemetry_samples.clear()
            self.missed_auction_cycles = 0
            self.last_snapshot = self.snapshot()
            return self.last_snapshot

    async def inject(self, event: ChaosEvent) -> TelemetrySnapshot:
        async with self.lock:
            # Scenarios replace each other: supply availability and feeder limits
            # are separate constraints, not two names for the same shock.
            self.shock_fraction = 0
            self.supply_reduction = 0
            if event.event_type == "clear":
                self.shock_label = "No active shock"
            else:
                if event.event_type == "supply_deficit":
                    self.supply_reduction = event.magnitude
                else:
                    self.shock_fraction = event.magnitude
                self.shock_label = f"{event.event_type.replace('_', ' ').title()} · {event.magnitude:.0%}"
            self.tick += 1
            self._run_tick_locked()
            self.last_snapshot = self.snapshot()
            return self.last_snapshot

    def subscribe(self) -> asyncio.Queue[TelemetrySnapshot]:
        queue: asyncio.Queue[TelemetrySnapshot] = asyncio.Queue(maxsize=2)
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[TelemetrySnapshot]) -> None:
        self.subscribers.discard(queue)

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
            quantity = agent.baseline_kw if agent.agent_type == "hospital" else agent.available_kw * (1 - self.supply_reduction)
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
        for proposal in clear_market(orders, self.tick):
            decision = validate_trade(proposal, available, self.shock_fraction)
            self.current_decisions.append(decision)
            self.decisions.appendleft(decision)
            if decision.accepted:
                available[decision.seller_id] = max(0, available.get(decision.seller_id, 0) - decision.quantity_kw)
        duration_ms = (time.monotonic() - started) * 1000
        self.auction_samples.append(duration_ms)
        if duration_ms > 200:
            self.missed_auction_cycles += 1

    def snapshot(self) -> TelemetrySnapshot:
        orders = self._orders()
        demand = sum(order.quantity_kw for order in orders if order.side == "buy")
        supply = sum(order.quantity_kw for order in orders if order.side == "sell")
        served = sum(d.quantity_kw for d in self.current_decisions if d.accepted)
        unmet = max(0, demand - served)
        shock_active = bool(self.shock_fraction or self.supply_reduction)
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
            lines.append(LineState(id=line.id, from_node=line.from_node, to_node=line.to_node, capacity_kw=line.capacity_kw, loading_pct=round(loading, 1), status="overloaded" if loading >= 100 else "warning" if loading >= 80 else "normal"))
        agents = [agent.state(served_kw=served_hospital if agent.agent_type == "hospital" else 0, curtailed_kw=curtailed_commercial if agent.agent_type == "commercial" else 0).model_copy(update={"availability_kw": agent.available_kw * (1 - self.supply_reduction)}) for agent in self.agents]
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
            scenario=ScenarioStatus(name="Ward 4 feeder resilience", phase="shock" if shock_active else "baseline", shock_active=shock_active, shock_label=self.shock_label, seed=self.seed, physics_mode="SIMULATION FALLBACK"),
        )

    def _broadcast(self, snapshot: TelemetrySnapshot) -> None:
        for queue in list(self.subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(snapshot)
            except asyncio.QueueFull:
                pass


def _percentile(values: deque[float], percentile: int) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((percentile / 100) * (len(ordered) - 1)))
    return round(statistics.median([ordered[index], ordered[min(index + 1, len(ordered) - 1)]]), 3)
