from fastapi.testclient import TestClient

from app.main import app, simulator


def test_health_state_and_frontend_contract():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        state = client.get("/api/v1/state")
        assert state.status_code == 200
        payload = state.json()
        assert payload["schema_version"] == "1.0"
        assert {"nodes", "lines", "agents", "order_book", "recent_decisions", "power_balance", "metrics", "scenario"} <= payload.keys()


def test_start_is_idempotent_and_pause_stops_loop():
    with TestClient(app) as client:
        first = client.post("/api/v1/scenario/start")
        first_task = simulator.task
        second = client.post("/api/simulation/start")
        assert first.status_code == second.status_code == 200
        assert simulator.task is first_task

        paused = client.post("/api/v1/scenario/pause")
        assert paused.status_code == 200
        assert paused.json()["status"] == "paused"
        assert simulator.running is False


def test_scenario_aliases_and_websocket_message():
    with TestClient(app) as client:
        response = client.post("/api/v1/scenario/supply_40")
        assert response.status_code == 200
        assert response.json()["scenario"]["scenario_id"] == "supply_40"
        assert response.json()["power_balance"]["available_supply_kw"] < response.json()["power_balance"]["total_demand_kw"]

        with client.websocket_connect("/ws/telemetry") as socket:
            message = socket.receive_json()
            assert message["schema_version"] == "1.0"
            assert "power_balance" in message


def test_invalid_scenario_has_actionable_error():
    with TestClient(app) as client:
        response = client.post("/api/v1/scenario/not-a-real-scenario")
        assert response.status_code == 400
        assert "Supported IDs" in response.json()["detail"]
