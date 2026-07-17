"""
Test Suite — Transit Service
==============================
Unit tests for transit delay classification, departure estimation,
and transit recommendation logic.
"""

import pytest

from backend.models.stadium import TransitHub, TransitType
from backend.services.transit_service import (
    classify_delay,
    compute_departure_estimate,
    get_transit_summary,
    recommend_transit,
)
from backend.simulation.engine import StadiumSimulator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simulator():
    """Create a deterministic simulator."""
    sim = StadiumSimulator(seed=99)
    import asyncio
    loop = asyncio.new_event_loop()
    for _ in range(5):
        loop.run_until_complete(sim._advance_tick())
    loop.close()
    return sim


@pytest.fixture
def stadium_state(simulator):
    """Get a deterministic stadium state."""
    return simulator.get_current_state()


@pytest.fixture
def sample_hub():
    """Create a sample transit hub for unit testing."""
    return TransitHub(
        hub_id="TH-TEST",
        name="Test Rail Station",
        transit_type=TransitType.RAIL,
        delay_minutes=3.0,
        capacity_remaining_pct=60.0,
        next_departure_minutes=8.0,
        gate_proximity="A",
        status="slight delay",
    )


# ---------------------------------------------------------------------------
# Delay Classification Tests
# ---------------------------------------------------------------------------

class TestDelayClassification:
    """Tests for transit delay severity classification."""

    def test_on_time(self):
        """Delays ≤ 2 minutes should be classified as normal."""
        result = classify_delay(0.0)
        assert result["level"] == "normal"
        assert result["color"] == "green"

    def test_slight_delay(self):
        """Delays 2–5 minutes should be slight."""
        result = classify_delay(3.5)
        assert result["level"] == "slight"
        assert result["color"] == "yellow"

    def test_moderate_delay(self):
        """Delays 5–10 minutes should be moderate."""
        result = classify_delay(7.0)
        assert result["level"] == "moderate"
        assert result["color"] == "orange"

    def test_severe_delay(self):
        """Delays > 10 minutes should be severe."""
        result = classify_delay(15.0)
        assert result["level"] == "severe"
        assert result["color"] == "red"

    def test_boundary_values(self):
        """Test exact boundary values."""
        assert classify_delay(2.0)["level"] == "normal"
        assert classify_delay(2.1)["level"] == "slight"
        assert classify_delay(5.0)["level"] == "slight"
        assert classify_delay(5.1)["level"] == "moderate"
        assert classify_delay(10.0)["level"] == "moderate"
        assert classify_delay(10.1)["level"] == "severe"

    def test_zero_delay(self):
        """Zero delay should be normal."""
        result = classify_delay(0.0)
        assert result["level"] == "normal"
        assert result["label"] == "On Time"


# ---------------------------------------------------------------------------
# Departure Estimate Tests
# ---------------------------------------------------------------------------

class TestDepartureEstimate:
    """Tests for departure time computation."""

    def test_total_time_formula(self, sample_hub):
        """Total time = walk + delay + next departure wait."""
        estimate = compute_departure_estimate(section=100, hub=sample_hub)
        expected = estimate["walk_minutes"] + estimate["delay_minutes"] + estimate["next_departure_minutes"]
        assert abs(estimate["total_estimated_minutes"] - expected) < 0.2

    def test_includes_delay_classification(self, sample_hub):
        """Estimate should include delay classification info."""
        estimate = compute_departure_estimate(section=100, hub=sample_hub)
        assert "delay_classification" in estimate
        assert "level" in estimate["delay_classification"]
        assert "color" in estimate["delay_classification"]

    def test_walk_time_varies_by_section(self, sample_hub):
        """Different sections should have different walk times to the same hub."""
        est1 = compute_departure_estimate(section=100, hub=sample_hub)  # Near Gate A
        est2 = compute_departure_estimate(section=150, hub=sample_hub)  # Near Gate E
        # Gate A hub → section 100 is close, section 150 is far
        assert est1["walk_minutes"] < est2["walk_minutes"]

    def test_response_structure(self, sample_hub):
        """Verify all required fields are present."""
        estimate = compute_departure_estimate(section=120, hub=sample_hub)
        required_keys = {
            "hub_id", "hub_name", "transit_type", "walk_minutes",
            "delay_minutes", "next_departure_minutes",
            "total_estimated_minutes", "delay_classification",
            "capacity_remaining_pct", "status",
        }
        assert required_keys.issubset(estimate.keys())


# ---------------------------------------------------------------------------
# Transit Recommendation Tests
# ---------------------------------------------------------------------------

class TestTransitRecommendation:
    """Tests for transit recommendation logic."""

    def test_returns_results(self, stadium_state):
        """Should return transit recommendations."""
        recs = recommend_transit(section=120, state=stadium_state)
        assert len(recs) > 0

    def test_sorted_by_total_time(self, stadium_state):
        """Results should be sorted by total estimated time."""
        recs = recommend_transit(section=120, state=stadium_state, max_results=6)
        times = [r["total_estimated_minutes"] for r in recs]
        assert times == sorted(times)

    def test_type_filter_rail(self, stadium_state):
        """Filtering by 'rail' should return only rail hubs."""
        recs = recommend_transit(
            section=120, state=stadium_state, preferred_type="rail"
        )
        for rec in recs:
            assert rec["transit_type"] == "rail"

    def test_type_filter_bus(self, stadium_state):
        """Filtering by 'bus' should return only bus hubs."""
        recs = recommend_transit(
            section=120, state=stadium_state, preferred_type="bus"
        )
        for rec in recs:
            assert rec["transit_type"] == "bus"

    def test_max_results_respected(self, stadium_state):
        """Should return at most max_results."""
        recs = recommend_transit(section=120, state=stadium_state, max_results=2)
        assert len(recs) <= 2


# ---------------------------------------------------------------------------
# Transit Summary Tests
# ---------------------------------------------------------------------------

class TestTransitSummary:
    """Tests for the operational transit summary."""

    def test_summary_structure(self, stadium_state):
        """Summary should have all required fields."""
        summary = get_transit_summary(stadium_state)
        required_keys = {
            "overall_status", "average_delay_minutes",
            "total_hubs", "type_breakdown", "delayed_hubs",
        }
        assert required_keys.issubset(summary.keys())

    def test_total_hubs_count(self, stadium_state):
        """Total hubs should match state."""
        summary = get_transit_summary(stadium_state)
        assert summary["total_hubs"] == len(stadium_state.transit_hubs)

    def test_type_breakdown_has_all_types(self, stadium_state):
        """Type breakdown should cover all transit types present."""
        summary = get_transit_summary(stadium_state)
        types_in_state = {h.transit_type.value for h in stadium_state.transit_hubs}
        assert types_in_state.issubset(summary["type_breakdown"].keys())

    def test_average_delay_non_negative(self, stadium_state):
        """Average delay should be non-negative."""
        summary = get_transit_summary(stadium_state)
        assert summary["average_delay_minutes"] >= 0
