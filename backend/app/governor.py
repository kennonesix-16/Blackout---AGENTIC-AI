from __future__ import annotations

import networkx as nx

from .models import TradeDecision, TradeProposal, now_iso
from .topology import GRAPH, LINES


def validate_trade(proposal: TradeProposal, available: dict[str, float], shock_fraction: float) -> TradeDecision:
    if proposal.quantity_kw <= 0:
        return _reject(proposal, "quantity must be positive")
    if available.get(proposal.seller_id, 0) < proposal.quantity_kw:
        return _reject(proposal, "seller inventory or flexibility is insufficient")
    try:
        path = nx.shortest_path(GRAPH, proposal.seller_node_id, proposal.buyer_node_id)
    except nx.NetworkXNoPath:
        return _reject(proposal, "seller and buyer are disconnected")
    for from_node, to_node in zip(path, path[1:]):
        edge = GRAPH.get_edge_data(from_node, to_node)
        capacity = float(edge["capacity_kw"])
        if from_node == "residential-north" or to_node == "residential-north":
            if proposal.quantity_kw > capacity:
                return _reject(proposal, f"line {edge['id']} thermal limit: {proposal.quantity_kw:.0f}kW > {capacity:.0f}kW")
        effective_capacity = capacity * (1 - shock_fraction * 0.25)
        if proposal.quantity_kw > effective_capacity * 1.35:
            return _reject(proposal, f"conservative feeder limit on {edge['id']}")
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
    )
