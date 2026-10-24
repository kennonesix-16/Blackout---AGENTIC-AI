import pytest
from pydantic import ValidationError

from app.agents import default_agents
from app.auction import clear_market
from app.governor import validate_trade
from app.models import Order, TradeProposal
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


@pytest.mark.asyncio
async def test_scripted_flow_has_accepted_and_rejected_trade():
    simulator = Simulator()
    await simulator.reset()
    snapshot = await simulator.inject(__import__("app.models", fromlist=["ChaosEvent"]).ChaosEvent(event_type="feeder_loss", target_id="ward-4-feeder", magnitude=0.5))
    assert snapshot.scenario.shock_active
    assert any(decision.accepted for decision in snapshot.recent_decisions)
    assert any(not decision.accepted for decision in snapshot.recent_decisions)
    assert any("thermal" in decision.reason for decision in snapshot.recent_decisions if not decision.accepted)
