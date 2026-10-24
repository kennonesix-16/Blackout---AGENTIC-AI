import pytest
from pydantic import ValidationError

from app.agents import default_agents
from app.auction import clear_market
from app.governor import validate_trade
from app.models import Order, PowerBalance, TradeProposal
from app.simulation import Simulator


def test_order_schema_rejects_negative_quantity():
    with pytest.raises(ValidationError):
        Order(id="bad", timestamp="now", node_id="hospital", side="buy", quantity_kw=-1, price_per_kwh=0.5, agent_type="hospital")


def test_double_auction_matches_sorted_orders():
    orders = [
        Order(id="b", timestamp="now", node_id="hospital", side="buy", quantity_kw=100, price_per_kwh=0.6, agent_type="hospital"),
        Order(id="s1", timestamp="now", node_id="ev-depot", side="sell", quantity_kw=60, price_per_kwh=0.2, agent_type="ev"),
        Order(id="s2", timestamp="now", node_id="commercial-north", side="sell", quantity_kw=60, price_per_kwh=0.3, agent_type="commercial"),
    ]
    proposals = clear_market(orders, tick=1)
    assert [round(p.quantity_kw) for p in proposals] == [60, 40]
    assert proposals[0].clearing_price == 0.4


def test_governor_rejects_residential_north_over_line_limit():
    proposal = TradeProposal(trade_id="unsafe", buyer_id="hospital", seller_id="residential", quantity_kw=60, clearing_price=0.46, buyer_node_id="hospital", seller_node_id="residential-north", timestamp="now")
    decision = validate_trade(proposal, {"residential": 60}, shock_fraction=0.5)
    assert not decision.accepted
    assert "thermal limit" in decision.reason


def test_agent_constraints_are_present():
    agents = {agent.agent_type: agent for agent in default_agents()}
    assert agents["ev"].soc_pct == 78
    assert agents["ev"].available_kw == 120
    assert agents["commercial"].available_kw == 100


def test_power_balance_accepts_valid_invariants():
    balance = PowerBalance(
        total_demand_kw=280,
        available_supply_kw=192,
        served_load_kw=192,
        unmet_demand_kw=88,
        deficit_kw=88,
    )
    assert balance.served_load_kw <= balance.total_demand_kw
    assert balance.served_load_kw <= balance.available_supply_kw


@pytest.mark.parametrize(
    "overrides",
    [
        {"served_load_kw": 281},
        {"served_load_kw": 193},
        {"unmet_demand_kw": 87},
        {"deficit_kw": 87},
        {"total_demand_kw": -1},
        {"total_demand_kw": float("inf")},
    ],
)
def test_power_balance_rejects_invalid_invariants(overrides):
    payload = {
        "total_demand_kw": 280,
        "available_supply_kw": 192,
        "served_load_kw": 192,
        "unmet_demand_kw": 88,
        "deficit_kw": 88,
        **overrides,
    }
    with pytest.raises(ValidationError):
        PowerBalance(**payload)


@pytest.mark.asyncio
async def test_scripted_flow_has_accepted_and_rejected_trade():
    simulator = Simulator()
    await simulator.reset()
    snapshot = await simulator.inject(__import__("app.models", fromlist=["ChaosEvent"]).ChaosEvent(event_type="feeder_loss", target_id="ward-4-feeder", magnitude=0.5))
    assert snapshot.scenario.shock_active
    assert any(decision.accepted for decision in snapshot.recent_decisions)
    assert any(not decision.accepted for decision in snapshot.recent_decisions)
    assert any("thermal" in decision.reason for decision in snapshot.recent_decisions if not decision.accepted)


@pytest.mark.asyncio
async def test_hospital_allocation_uses_only_latest_clearing_cycle():
    simulator = Simulator()
    for tick in range(1, 10):
        simulator.tick = tick
        simulator._run_tick_locked()
        snapshot = simulator.snapshot()
        current = [d for d in snapshot.recent_decisions if d.trade_id.startswith(f"trade-{tick}-")]
        allocated = sum(d.quantity_kw for d in current if d.accepted and d.buyer_id == "hospital")
        hospital = next(node for node in snapshot.nodes if node.id == "hospital")
        agent = next(agent for agent in snapshot.agents if agent.type == "hospital")
        assert hospital.served_kw == allocated
        assert hospital.unmet_kw == hospital.requested_kw - allocated
        assert agent.served_kw == allocated
        assert allocated <= hospital.requested_kw
    # The bounded activity feed still contains earlier cycles, not just current trades.
    snapshot = simulator.snapshot()
    assert len(snapshot.recent_decisions) == 20
    assert any(not d.trade_id.startswith("trade-9-") for d in snapshot.recent_decisions)


def test_empty_clearing_cycle_does_not_reuse_prior_allocation(monkeypatch):
    simulator = Simulator()
    simulator._run_tick_locked()
    history = list(simulator.decisions)
    assert any(d.accepted for d in history)
    monkeypatch.setattr("app.simulation.clear_market", lambda orders, tick: [])
    simulator.tick += 1
    simulator._run_tick_locked()
    snapshot = simulator.snapshot()
    hospital = next(node for node in snapshot.nodes if node.id == "hospital")
    commercial = next(agent for agent in snapshot.agents if agent.type == "commercial")
    assert hospital.served_kw == 0
    assert hospital.unmet_kw == hospital.requested_kw
    assert commercial.curtailed_kw == 0
    assert snapshot.recent_decisions == history


def test_baseline_clearing_fully_serves_hospital_when_grid_is_healthy():
    simulator = Simulator()
    simulator._run_tick_locked()
    snapshot = simulator.snapshot()
    hospital = next(node for node in snapshot.nodes if node.id == "hospital")
    assert snapshot.scenario.scenario_id == "normal"
    assert hospital.served_kw == hospital.requested_kw
    assert hospital.unmet_kw == 0
    assert snapshot.power_balance.deficit_kw == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("reduction", [0, 0.2, 0.4, 1])
async def test_supply_reduction_changes_offers_and_authoritative_balance(reduction):
    from app.models import ChaosEvent

    simulator = Simulator()
    baseline = simulator.snapshot()
    baseline_supply = sum(order.quantity_kw for order in baseline.order_book if order.side == "sell")
    snapshot = await simulator.inject(ChaosEvent(event_type="supply_deficit", magnitude=reduction))
    balance = snapshot.power_balance
    demand = sum(order.quantity_kw for order in snapshot.order_book if order.side == "buy")
    supply = sum(order.quantity_kw for order in snapshot.order_book if order.side == "sell")
    allocated = sum(d.quantity_kw for d in simulator.current_decisions if d.accepted)
    assert demand == sum(order.quantity_kw for order in baseline.order_book if order.side == "buy")
    assert supply == pytest.approx(baseline_supply * (1 - reduction))
    assert balance.total_demand_kw == demand
    assert balance.available_supply_kw == supply
    assert balance.served_load_kw == pytest.approx(allocated)
    assert 0 <= balance.served_load_kw <= min(demand, supply)
    assert balance.unmet_demand_kw == pytest.approx(demand - allocated)
    assert balance.deficit_kw == balance.unmet_demand_kw
    assert sum(agent.availability_kw for agent in snapshot.agents) == pytest.approx(supply)
    hospital = next(node for node in snapshot.nodes if node.id == "hospital")
    assert hospital.served_kw == balance.served_load_kw
    assert hospital.unmet_kw == balance.unmet_demand_kw
    if reduction == 1:
        assert snapshot.recent_decisions == []
        assert balance.available_supply_kw == balance.served_load_kw == 0
        assert balance.deficit_kw == demand


@pytest.mark.asyncio
async def test_offer_capacity_is_not_counted_again_as_served_supply():
    from app.models import ChaosEvent

    simulator = Simulator()
    snapshot = await simulator.inject(ChaosEvent(event_type="feeder_loss", magnitude=0.5))
    balance = snapshot.power_balance
    offers = sum(order.quantity_kw for order in snapshot.order_book if order.side == "sell")
    assert balance.available_supply_kw == offers
    assert balance.available_supply_kw > balance.served_load_kw
    # Offers may exceed demand while a thermal rejection still leaves unmet demand.
    assert balance.available_supply_kw > balance.total_demand_kw
    assert balance.deficit_kw > 0
    cleared = await simulator.inject(ChaosEvent(event_type="clear", magnitude=0))
    assert cleared.power_balance.available_supply_kw == offers
    reset = await simulator.reset()
    assert reset.recent_decisions == []
    assert reset.power_balance.served_load_kw == 0
    assert reset.power_balance.deficit_kw == reset.power_balance.total_demand_kw


@pytest.mark.asyncio
async def test_supply_reduction_does_not_persist_after_clear_or_feeder_scenario():
    from app.models import ChaosEvent

    simulator = Simulator()
    original_supply = sum(order.quantity_kw for order in simulator.snapshot().order_book if order.side == "sell")
    for next_event in ["clear", "feeder_loss"]:
        await simulator.inject(ChaosEvent(event_type="supply_deficit", magnitude=0.4))
        snapshot = await simulator.inject(ChaosEvent(event_type=next_event, magnitude=0.5 if next_event == "feeder_loss" else 0))
        assert snapshot.power_balance.available_supply_kw == original_supply
