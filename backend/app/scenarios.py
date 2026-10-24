from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    label: str
    event_type: str
    magnitude: float


SCENARIOS: dict[str, ScenarioDefinition] = {
    "normal": ScenarioDefinition("normal", "Normal operation", "clear", 0.0),
    "supply_20": ScenarioDefinition("supply_20", "20% supply reduction", "supply_deficit", 0.2),
    "supply_40": ScenarioDefinition("supply_40", "40% supply reduction", "supply_deficit", 0.4),
    "feeder_reduction_50": ScenarioDefinition("feeder_reduction_50", "50% feeder capacity reduction", "feeder_reduction", 0.5),
    "feeder_loss": ScenarioDefinition("feeder_loss", "50% feeder capacity reduction", "feeder_loss", 0.5),
    "feeder_outage": ScenarioDefinition("feeder_outage", "Complete feeder outage", "feeder_outage", 1.0),
    "renewable_drop": ScenarioDefinition("renewable_drop", "Renewable generation drop", "renewable_drop", 0.2),
    "solar_reduction": ScenarioDefinition("solar_reduction", "Renewable generation drop", "renewable_drop", 0.2),
}


def get_scenario(scenario_id: str) -> ScenarioDefinition | None:
    return SCENARIOS.get(scenario_id.lower().strip())
