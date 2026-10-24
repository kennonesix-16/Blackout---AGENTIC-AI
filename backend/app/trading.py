from __future__ import annotations

from .auction import clear_market
from .models import Order, TradeProposal


class TradeMatchingEngine:
    """Deterministic continuous double-auction adapter."""

    def match(self, orders: list[Order], tick: int) -> list[TradeProposal]:
        return clear_market(orders, tick)
