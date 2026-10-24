from __future__ import annotations

import asyncio

from .models import TelemetrySnapshot


class TelemetryHub:
    """Small bounded fan-out hub so slow WebSocket clients cannot block the loop."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[TelemetrySnapshot]] = set()

    def subscribe(self) -> asyncio.Queue[TelemetrySnapshot]:
        queue: asyncio.Queue[TelemetrySnapshot] = asyncio.Queue(maxsize=2)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[TelemetrySnapshot]) -> None:
        self._subscribers.discard(queue)

    def publish(self, snapshot: TelemetrySnapshot) -> None:
        for queue in list(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(snapshot)
            except asyncio.QueueFull:
                pass
