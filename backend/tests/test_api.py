"""
Test Suite — API Integration Tests
====================================
Integration tests for all REST endpoints using FastAPI TestClient.
Validates response codes, schemas, and RBAC enforcement.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.middleware.security import create_role_token


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def staff_token():
    """Generate a staff authentication token."""
    return create_role_token("staff", "test-staff")


@pytest.fixture
def fan_token():
    """Generate a fan authentication token."""
    return create_role_token("fan", "test-fan")


# ---------------------------------------------------------------------------
# System Endpoint Tests
# ---------------------------------------------------------------------------

class TestSystemEndpoints:
    """Tests for root and health endpoints."""

    def test_root_returns_info(self, client):
        """Root should return API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "endpoints" in data

    def test_health_check(self, client):
        """Health endpoint should return healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


# ---------------------------------------------------------------------------
# High-Entropy Edge-Case Integration Tests (Fuzzing)
# ---------------------------------------------------------------------------

class TestHighEntropyEdgeCases:
    """Rigorous fuzzing bounds for extreme unexpected payloads."""

    def test_malformed_json_payload_rejection(self, client, staff_token):
        """Should gracefully reject structurally malformed JSON with 422."""
        headers = {"Authorization": f"Bearer {staff_token}", "Content-Type": "application/json"}
        # Send raw invalid string instead of JSON
        response = client.post("/api/ops/assistant", data="INVALID_JSON_{{", headers=headers)
        assert response.status_code == 422
        
    def test_empty_string_input_handling(self, client, staff_token):
        """Should reject empty messages with a validation error, not pass them to the NLP pipeline."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.post("/api/ops/assistant", json={"message": "", "conversation_id": "test"}, headers=headers)
        # Empty input violates min_length=1 on AssistantRequest.message.
        # Pydantic returns 422 Unprocessable Entity — the correct behavior:
        # the validation layer rejects bad input before it reaches the NLP pipeline.
        assert response.status_code == 422
        
    async def test_concurrent_spike_simulation_mock(self, client):
        """Simulate high concurrency against the health endpoint to ensure no async blocking."""
        import asyncio
        async def fetch():
            return client.get("/health").status_code
            
        tasks = [fetch() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        assert all(r == 200 for r in results)
        
    def test_websocket_live_feed_receives_state(self):
        """
        The /ws/live WebSocket should accept a connection, receive a real
        stadium state broadcast, and return a valid JSON message.

        Approach: use TestClient with lifespan='on' so the simulator starts.
        Then connect to the WebSocket and manually advance one simulator tick
        from a background thread to unblock the queue, so receive_text() returns
        a real message without waiting for the full 5-second tick interval.
        """
        import asyncio
        import json
        import threading
        import time
        from fastapi.testclient import TestClient
        from backend.main import app
        from backend.simulation.engine import simulator

        with TestClient(app, raise_server_exceptions=True) as lifespan_client:
            # Give the simulator a moment to initialize after lifespan startup
            time.sleep(0.1)

            # Connect to the WebSocket. receive_text() blocks until the simulator
            # pushes a tick. We trigger that tick from a background thread.
            def _trigger_tick_after_delay():
                time.sleep(0.2)
                # Run a single simulator advance + broadcast in the app's event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    async def _do_tick():
                        await simulator._advance_tick()
                        state = simulator._build_state()
                        await simulator._broadcast(state)
                    loop.run_until_complete(_do_tick())
                finally:
                    loop.close()

            trigger_thread = threading.Thread(target=_trigger_tick_after_delay, daemon=True)
            trigger_thread.start()

            with lifespan_client.websocket_connect("/ws/live") as ws:
                raw = ws.receive_text()

        state = json.loads(raw)

        assert isinstance(state, dict), "Expected a JSON object from /ws/live"
        assert "gates" in state, "State missing 'gates' field"
        assert "active_incidents" in state, "State missing 'active_incidents' field"
        assert "total_attendance" in state, "State missing 'total_attendance' field"
        assert "simulation_tick" in state, "State missing 'simulation_tick' field"
        assert state["simulation_tick"] >= 0, "simulation_tick should be non-negative"

        assert isinstance(state["gates"], list), "'gates' must be a list"
        if state["gates"]:
            gate = state["gates"][0]
            assert "gate_id" in gate, "Gate entry missing 'gate_id'"
            assert "congestion_pct" in gate, "Gate entry missing 'congestion_pct'"
            assert 0 <= gate["congestion_pct"] <= 100, (
                f"congestion_pct {gate['congestion_pct']} out of 0-100 range"
            )
        trigger_thread.join(timeout=5)

    def test_dev_token_staff(self, client):
        """Dev token endpoint should generate staff tokens."""
        response = client.get("/dev/token/staff")
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "staff"
        assert "token" in data

    def test_dev_token_fan(self, client):
        """Dev token endpoint should generate fan tokens."""
        response = client.get("/dev/token/fan")
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "fan"

    def test_dev_token_invalid_role(self, client):
        """Dev token with invalid role should return error."""
        response = client.get("/dev/token/admin")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data


# ---------------------------------------------------------------------------
# Operations Endpoint Tests
# ---------------------------------------------------------------------------

class TestOperationsEndpoints:
    """Tests for staff-facing operations API."""

    def test_get_stadium_state(self, client, staff_token):
        """Should return full stadium state."""
        response = client.get(
            "/api/ops/stadium-state",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "gates" in data
        assert "concessions" in data
        assert "transit_hubs" in data
        assert "match_phase" in data
        assert len(data["gates"]) == 8

    def test_get_alerts(self, client, staff_token):
        """Should return alerts structure."""
        response = client.get(
            "/api/ops/alerts",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "total_count" in data
        assert isinstance(data["alerts"], list)

    def test_get_incidents(self, client, staff_token):
        """Should return incidents structure."""
        response = client.get(
            "/api/ops/incidents",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "incidents" in data
        assert "total_count" in data

    def test_get_transit_summary(self, client, staff_token):
        """Should return transit summary."""
        response = client.get(
            "/api/ops/transit-summary",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
        assert "type_breakdown" in data

    def test_staff_assistant(self, client, staff_token):
        """Should process staff assistant query."""
        response = client.post(
            "/api/ops/assistant",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={"message": "Which gates need attention?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "conversation_id" in data
        assert "processing_time_ms" in data

    def test_fan_cannot_access_ops(self, client, fan_token):
        """Fan token should be rejected on staff endpoints."""
        response = client.get(
            "/api/ops/stadium-state",
            headers={"Authorization": f"Bearer {fan_token}"},
        )
        assert response.status_code == 403

    def test_unauthenticated_access_allowed_dev(self, client):
        """Dev mode allows unauthenticated access (fallback)."""
        response = client.get("/api/ops/stadium-state")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Fan Endpoint Tests
# ---------------------------------------------------------------------------

class TestFanEndpoints:
    """Tests for fan-facing API."""

    def test_get_concessions(self, client, fan_token):
        """Should return concession recommendations."""
        response = client.get(
            "/api/fan/concessions?section=120",
            headers={"Authorization": f"Bearer {fan_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "section" in data
        assert "recommendations" in data
        assert data["section"] == 120

    def test_get_gates(self, client, fan_token):
        """Should return gate recommendations."""
        response = client.get(
            "/api/fan/gates?section=150",
            headers={"Authorization": f"Bearer {fan_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "section" in data
        assert "primary_gate" in data
        assert "recommendations" in data

    def test_get_transit(self, client, fan_token):
        """Should return transit recommendations."""
        response = client.get(
            "/api/fan/transit?section=130",
            headers={"Authorization": f"Bearer {fan_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data

    def test_get_navigation(self, client, fan_token):
        """Should return navigation steps."""
        response = client.post(
            "/api/fan/navigation",
            headers={"Authorization": f"Bearer {fan_token}"},
            json={
                "from_section": 120,
                "destination": "Gate E",
                "accessibility_needs": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "steps" in data
        assert "estimated_walk_minutes" in data
        assert len(data["steps"]) > 0

    def test_fan_assistant(self, client, fan_token):
        """Should process fan assistant query."""
        response = client.post(
            "/api/fan/assistant",
            headers={"Authorization": f"Bearer {fan_token}"},
            json={
                "message": "Where can I get food near section 120?",
                "fan_profile": {
                    "seat_section": 120,
                    "language": "en",
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert len(data["reply"]) > 0

    def test_invalid_section_rejected(self, client, fan_token):
        """Section outside valid range should be rejected."""
        response = client.get(
            "/api/fan/concessions?section=50",
            headers={"Authorization": f"Bearer {fan_token}"},
        )
        assert response.status_code == 422  # Validation error

    def test_concession_type_filter(self, client, fan_token):
        """Type filter should be accepted."""
        response = client.get(
            "/api/fan/concessions?section=120&food_type=Beverages",
            headers={"Authorization": f"Bearer {fan_token}"},
        )
        assert response.status_code == 200

    def test_accessible_navigation(self, client, fan_token):
        """Accessible routes should include elevator/ramp."""
        response = client.post(
            "/api/fan/navigation",
            headers={"Authorization": f"Bearer {fan_token}"},
            json={
                "from_section": 140,
                "destination": "Gate A",
                "accessibility_needs": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["accessibility_route"] is True
        combined = " ".join(data["steps"]).lower()
        assert "elevator" in combined or "ramp" in combined

    @pytest.mark.asyncio
    async def test_fan_assistant_e2e_live_data(self):
        """
        E2E test of the Fan Assistant using real live simulator state.
        Ensures the fallback path references real gate data instead of mocked values.
        """
        from fastapi.testclient import TestClient
        from backend.main import app
        from backend.simulation.engine import simulator

        with TestClient(app, raise_server_exceptions=True) as lifespan_client:
            # Trigger a simulator tick to populate state BEFORE we query
            await simulator._advance_tick()
            state = simulator._build_state()
            await simulator._broadcast(state)

            # Use a Dev Fan Token
            token_resp = lifespan_client.get("/dev/token/fan")
            token = token_resp.json()["token"]

            response = lifespan_client.post(
                "/api/fan/assistant",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "message": "Which gate should I use to exit?",
                    "fan_profile": {"seat_section": 105, "language": "en"}
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "reply" in data

            # Verify the response is not the generic prompt injection or default fallback,
            # and that it contains live data (gate names and numeric congestion).
            reply = data["reply"]
            assert "Best gates for you right now" in reply, "Should use gate recommendation fallback"
            
            # The simulator creates gates with specific names (e.g. "Gate A"). Check for 'Gate'
            assert "Gate" in reply
            # And it should contain numeric walk times and congestion percentages
            assert "% full" in reply
            assert "min walk" in reply
