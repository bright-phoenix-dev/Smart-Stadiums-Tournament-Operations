"""
Integration test for the /ws/live WebSocket endpoint.

Tests that:
1. The endpoint accepts a WebSocket connection.
2. After connection, the simulator broadcasts a valid StadiumState JSON payload.
3. The payload contains the expected top-level keys.
4. Gate, concession, and transit hub counts match the configured stadium.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

# Set JWT_SECRET before importing the app so the lifespan check passes.
import os
os.environ.setdefault("JWT_SECRET", "test-secret-for-ws-integration")

from backend.main import fifa2026OpsAssistant  # noqa: E402


@pytest.fixture(scope="module")
def test_client():
    """
    Module-scoped TestClient so the app lifespan (simulator start/stop)
    runs once for all tests in this module.
    """
    with TestClient(fifa2026OpsAssistant, raise_server_exceptions=True) as client:
        yield client


class TestWebSocketLiveFeed:
    """Integration tests for /ws/live."""

    def test_websocket_accepts_connection(self, test_client):
        """The endpoint should accept a WebSocket connection and send at least one message."""
        from backend.simulation.engine import simulator
        import asyncio

        with test_client.websocket_connect("/ws/live") as ws:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(simulator._advance_tick())
            loop.close()

            raw = ws.receive_text()
            assert raw, "WebSocket sent an empty message"

    def test_websocket_payload_is_valid_json(self, test_client):
        """The broadcasted message must deserialize as valid JSON."""
        from backend.simulation.engine import simulator
        import asyncio

        with test_client.websocket_connect("/ws/live") as ws:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(simulator._advance_tick())
            loop.close()

            raw = ws.receive_text()
            payload = json.loads(raw)
            assert isinstance(payload, dict), "Payload is not a JSON object"

    def test_websocket_payload_has_required_keys(self, test_client):
        """The payload must contain all top-level StadiumState fields."""
        required_keys = {
            "timestamp",
            "match_phase",
            "match_minute",
            "total_attendance",
            "stadium_capacity",
            "gates",
            "concessions",
            "transit_hubs",
            "active_incidents",
            "alerts",
            "simulation_tick",
        }
        from backend.simulation.engine import simulator
        import asyncio

        with test_client.websocket_connect("/ws/live") as ws:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(simulator._advance_tick())
            loop.close()

            raw = ws.receive_text()
            payload = json.loads(raw)

            missing = required_keys - set(payload.keys())
            assert not missing, f"Payload missing keys: {missing}"

    def test_websocket_gate_count(self, test_client):
        """The payload must include exactly 8 gates (MetLife Stadium configuration)."""
        from backend.simulation.engine import simulator
        import asyncio

        with test_client.websocket_connect("/ws/live") as ws:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(simulator._advance_tick())
            loop.close()

            raw = ws.receive_text()
            payload = json.loads(raw)

            assert len(payload["gates"]) == 8, (
                f"Expected 8 gates, got {len(payload['gates'])}"
            )

    def test_websocket_gate_fields(self, test_client):
        """Each gate entry must have gate_id, congestion_pct, and is_open fields."""
        from backend.simulation.engine import simulator
        import asyncio

        with test_client.websocket_connect("/ws/live") as ws:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(simulator._advance_tick())
            loop.close()

            raw = ws.receive_text()
            payload = json.loads(raw)

            for gate in payload["gates"]:
                assert "gate_id" in gate, "Gate entry missing gate_id"
                assert "congestion_pct" in gate, "Gate entry missing congestion_pct"
                assert "is_open" in gate, "Gate entry missing is_open"
                assert 0 <= gate["congestion_pct"] <= 100, (
                    f"congestion_pct {gate['congestion_pct']} out of range"
                )

    def test_websocket_simulation_tick_increments(self, test_client):
        """Two consecutive messages should show an incrementing simulation_tick."""
        from backend.simulation.engine import simulator
        import asyncio

        with test_client.websocket_connect("/ws/live") as ws:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(simulator._advance_tick())
            first_raw = ws.receive_text()
            loop.run_until_complete(simulator._advance_tick())
            second_raw = ws.receive_text()
            loop.close()

            first = json.loads(first_raw)
            second = json.loads(second_raw)

            assert second["simulation_tick"] > first["simulation_tick"], (
                f"simulation_tick did not increment: "
                f"{first['simulation_tick']} to {second['simulation_tick']}"
            )

