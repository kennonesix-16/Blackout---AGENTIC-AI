"""Run the deterministic simulation without needing a running server."""

import asyncio

from backend.app.models import ChaosEvent
from backend.app.simulation import Simulator


async def main() -> None:
    simulator = Simulator()
    await simulator.reset()
    snapshot = await simulator.inject(ChaosEvent(event_type="feeder_loss", target_id="ward-4-feeder", magnitude=0.5))
    accepted = [d for d in snapshot.recent_decisions if d.accepted]
    rejected = [d for d in snapshot.recent_decisions if not d.accepted]
    print(f"tick={snapshot.tick} physics={snapshot.scenario.physics_mode}")
    print(f"accepted={len(accepted)} rejected={len(rejected)}")
    print(f"auction_p50_ms={snapshot.metrics.auction_p50_ms} auction_p95_ms={snapshot.metrics.auction_p95_ms}")
    print(f"hospital_unmet_kw={next(n.unmet_kw for n in snapshot.nodes if n.id == 'hospital')}")


if __name__ == "__main__":
    asyncio.run(main())
