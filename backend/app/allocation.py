from __future__ import annotations

from dataclasses import dataclass

from .models import TradeDecision, TradeProposal
from .governor import validate_trade


@dataclass
class AllocationDecisionEngine:
    """Applies the priority and grid-safety policy to proposed trades."""

    def decide(
        self,
        proposal: TradeProposal,
        available: dict[str, float],
        feeder_reduction: float,
        feeder_capacities: dict[str, float] | None = None,
        feeder_loads: dict[str, float] | None = None,
    ) -> TradeDecision:
        return validate_trade(
            proposal,
            available,
            feeder_reduction,
            feeder_capacities=feeder_capacities,
            feeder_loads=feeder_loads,
        )
