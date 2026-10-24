from __future__ import annotations

import networkx as nx

from .models import TradeDecision, TradeProposal, now_iso
from .topology import GRAPH, LINES


def validate_trade(
    proposal: TradeProposal,
    available: dict[str, float],
    shock_fraction: float,
    feeder_capacities: dict[str, float] | None = None,
    feeder_loads: dict[str, float] | None = None,
) -> TradeDecision:
    if proposal.quantity_kw <= 0:
        return _reject(proposal, "quantity must be positive")
    if available.get(proposal.seller_id, 0) < proposal.quantity_kw:
        return _reject(proposal, "seller inventory or flexibility is insufficient")
    try:
        path = nx.shortest_path(GRAPH, proposal.seller_node_id, proposal.buyer_node_id)
    except nx.NetworkXNoPath:
        return _reject(proposal, "seller and buyer are disconnected")
    loads = feeder_loads if feeder_loads is not None else {}
    proposed_loads: dict[str, float] = {}
    for from_node, to_node in zip(path, path[1:]):
        edge = GRAPH.get_edge_data(from_node, to_node)
        line_id = str(edge["id"])
        if feeder_capacities is not None and line_id in feeder_capacities:
            capacity = float(feeder_capacities[line_id])
        else:
            capacity = float(edge["capacity_kw"])
        remaining_capacity = max(0.0, capacity - loads.get(line_id, 0.0))
        if capacity <= 0:
            return _reject(proposal, f"feeder {line_id} is out of service")
        if from_node == "residential-north" or to_node == "residential-north":
            if proposal.quantity_kw > remaining_capacity:
                return _reject(proposal, f"line {line_id} thermal limit: {proposal.quantity_kw:.0f}kW > {remaining_capacity:.0f}kW")
            if shock_fraction > 0 and proposal.quantity_kw >= remaining_capacity:
                return _reject(proposal, f"line {line_id} thermal limit: {proposal.quantity_kw:.0f}kW reaches the derated {remaining_capacity:.0f}kW limit during feeder shock")
        effective_capacity = capacity * (1 - shock_fraction * 0.25)
        if proposal.quantity_kw > min(remaining_capacity, effective_capacity * 1.35):
            return _reject(proposal, f"conservative feeder limit on {line_id}")
        proposed_loads[line_id] = proposed_loads.get(line_id, 0.0) + proposal.quantity_kw
    for line_id, quantity in proposed_loads.items():
        loads[line_id] = loads.get(line_id, 0.0) + quantity
    return TradeDecision(
        trade_id=proposal.trade_id,
        buyer_id=proposal.buyer_id,
        seller_id=proposal.seller_id,
        quantity_kw=proposal.quantity_kw,
        clearing_price=proposal.clearing_price,
        accepted=True,
        reason="accepted by schema, path, capacity, and conservative thermal checks",
        physics_mode="SIMULATION FALLBACK",
        timestamp=now_iso(),
        decision_id=proposal.trade_id,
        affected_id=proposal.buyer_node_id,
        before={"seller_available_kw": 0.0},
        after={"seller_available_kw": 0.0},
    )


def _reject(proposal: TradeProposal, reason: str) -> TradeDecision:
    return TradeDecision(
        trade_id=proposal.trade_id,
        buyer_id=proposal.buyer_id,
        seller_id=proposal.seller_id,
        quantity_kw=proposal.quantity_kw,
        clearing_price=proposal.clearing_price,
        accepted=False,
        reason=reason,
        physics_mode="SIMULATION FALLBACK",
        timestamp=now_iso(),
        decision_id=proposal.trade_id,
        affected_id=proposal.buyer_node_id,
        before={"seller_available_kw": 0.0},
        after={"seller_available_kw": 0.0},
    )
