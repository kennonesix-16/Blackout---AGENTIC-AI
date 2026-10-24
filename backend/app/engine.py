from __future__ import annotations

from .models import DecisionEvent, now_iso


class EventExplanationEngine:
    """Creates structured, display-ready explanations for important decisions."""

    def event(
        self,
        decision_id: str,
        kind: str,
        affected_id: str,
        decision: str,
        reason: str,
        before: dict[str, float] | None = None,
        after: dict[str, float] | None = None,
    ) -> DecisionEvent:
        return DecisionEvent(
            decision_id=decision_id,
            kind=kind,
            affected_id=affected_id,
            decision=decision,
            reason=reason,
            timestamp=now_iso(),
            before=before or {},
            after=after or {},
        )
