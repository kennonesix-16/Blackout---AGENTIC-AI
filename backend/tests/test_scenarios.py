import pytest

from app.models import ChaosEvent
from app.simulation import Simulator


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("event_type", "magnitude"),
    [("supply_deficit", 0.2), ("supply_deficit", 0.4), ("feeder_reduction", 0.5), ("feeder_outage", 1.0), ("renewable_drop", 0.2)],
)
async def test_supported_scenario_changes_actual_state(event_type, magnitude):
    simulator = Simulator()
    baseline = simulator.snapshot()
    shocked = await simulator.inject(ChaosEvent(event_type=event_type, magnitude=magnitude))

    assert shocked.scenario.shock_active
    assert shocked.scenario.scenario_id != "normal"
    assert shocked.event_log
    if event_type == "supply_deficit":
        assert shocked.power_balance.available_supply_kw == pytest.approx(baseline.power_balance.available_supply_kw * (1 - magnitude))
    elif event_type == "renewable_drop":
        assert shocked.power_balance.available_supply_kw < baseline.power_balance.available_supply_kw
    elif event_type == "feeder_outage":
        assert next(line for line in shocked.lines if line.id == "line-east-hospital").capacity_kw == 0
    else:
        assert next(line for line in shocked.lines if line.id == "line-east-hospital").capacity_kw < next(line for line in baseline.lines if line.id == "line-east-hospital").capacity_kw


@pytest.mark.asyncio
async def test_clear_restores_baseline_without_accumulating_reductions():
    simulator = Simulator()
    baseline = simulator.snapshot()
    await simulator.inject(ChaosEvent(event_type="supply_deficit", magnitude=0.4))
    await simulator.inject(ChaosEvent(event_type="feeder_outage", magnitude=1))
    cleared = await simulator.inject(ChaosEvent(event_type="clear", magnitude=0))

    assert cleared.scenario.scenario_id == "normal"
    assert cleared.power_balance.available_supply_kw == baseline.power_balance.available_supply_kw
    assert all(line.capacity_kw == baseline_line.capacity_kw for line, baseline_line in zip(cleared.lines, baseline.lines))
