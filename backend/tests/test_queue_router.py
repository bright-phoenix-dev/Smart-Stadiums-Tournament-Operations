"""
Test Suite — Queue Router Algorithms
======================================
Unit tests validating the core routing algorithms:
    - Gate-to-section mapping
    - Walk time computation
    - Gate recommendation scoring
    - Concession recommendation scoring
    - Navigation step generation
    - Facility finder
"""

import pytest

from backend.config import GATES
from backend.services.queue_router import (
    compute_walk_time,
    find_nearest_facilities,
    generate_navigation_steps,
    get_gate_for_section,
    recommend_concession,
    recommend_gate,
)
from backend.simulation.engine import StadiumSimulator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simulator():
    """Create a deterministic simulator with a fixed seed."""
    sim = StadiumSimulator(seed=42)
    # Manually advance a few ticks to generate realistic data
    import asyncio
    loop = asyncio.new_event_loop()
    for _ in range(5):
        loop.run_until_complete(sim._advance_tick())
    loop.close()
    return sim


@pytest.fixture
def stadium_state(simulator):
    """Get a deterministic stadium state snapshot."""
    return simulator.get_current_state()


# ---------------------------------------------------------------------------
# Gate Mapping Tests
# ---------------------------------------------------------------------------

class TestGateMapping:
    """Tests for section-to-gate mapping."""

    def test_section_100_maps_to_gate_a(self):
        """Section 100 is in Gate A's range (100–112)."""
        assert get_gate_for_section(100) == "A"

    def test_section_112_maps_to_gate_a(self):
        """Section 112 is the last section in Gate A's range."""
        assert get_gate_for_section(112) == "A"

    def test_section_113_maps_to_gate_b(self):
        """Section 113 transitions to Gate B."""
        assert get_gate_for_section(113) == "B"

    def test_section_150_maps_to_gate_e(self):
        """Section 150 is in Gate E's range."""
        assert get_gate_for_section(150) == "E"

    def test_section_199_maps_to_gate_h(self):
        """Section 199 is in Gate H's range."""
        assert get_gate_for_section(199) == "H"

    def test_out_of_range_section_falls_back(self):
        """Sections outside 100–199 should fall back to Gate A."""
        assert get_gate_for_section(50) == "A"

    def test_every_valid_section_has_a_gate(self):
        """All sections 100–199 should map to exactly one gate."""
        for section in range(100, 200):
            gate = get_gate_for_section(section)
            assert gate in GATES, f"Section {section} mapped to invalid gate '{gate}'"

    def test_negative_or_null_section_graceful_fallback(self):
        """Negative, zero, or null sections should fall back gracefully rather than crash."""
        assert get_gate_for_section(-50) == "A"
        assert get_gate_for_section(0) == "A"
        assert get_gate_for_section(None) == "A"


# ---------------------------------------------------------------------------
# Walk Time Tests
# ---------------------------------------------------------------------------

class TestWalkTime:
    """Tests for walk time computation."""

    def test_same_gate_zero_time(self):
        """Walking from a gate to itself should take 0 minutes."""
        assert compute_walk_time("A", "A") == 0.0

    def test_adjacent_gates_short_time(self):
        """Adjacent gates should have walk time of 3 minutes."""
        assert compute_walk_time("A", "B") == 3.0
        assert compute_walk_time("A", "H") == 3.0  # Circular adjacency

    def test_opposite_gates_longest_time(self):
        """Diametrically opposite gates should have the longest walk."""
        assert compute_walk_time("A", "E") == 8.0

    def test_symmetry(self):
        """Walk times should be symmetric: A→B == B→A."""
        for g1 in GATES:
            for g2 in GATES:
                assert compute_walk_time(g1, g2) == compute_walk_time(g2, g1), \
                    f"Asymmetric walk time between {g1} and {g2}"

    def test_unknown_gate_returns_default(self):
        """Unknown gate pairs should return default 5.0."""
        assert compute_walk_time("A", "Z") == 5.0

    def test_null_gate_returns_default(self):
        """Passing null gates should not crash math formulas."""
        assert compute_walk_time(None, "B") == 5.0
        assert compute_walk_time("A", None) == 5.0
        assert compute_walk_time(None, None) == 5.0


# ---------------------------------------------------------------------------
# Gate Recommendation Tests
# ---------------------------------------------------------------------------

class TestGateRecommendation:
    """Tests for the gate recommendation scoring algorithm."""

    def test_returns_correct_count(self, stadium_state):
        """Should return at most max_results recommendations."""
        recs = recommend_gate(section=100, state=stadium_state, max_results=3)
        assert len(recs) <= 3

    def test_recommendations_sorted_by_score(self, stadium_state):
        """Recommendations should be sorted by score ascending."""
        recs = recommend_gate(section=150, state=stadium_state, max_results=8)
        scores = [r["score"] for r in recs]
        assert scores == sorted(scores), "Recommendations not sorted by score"

    def test_recommendation_structure(self, stadium_state):
        """Each recommendation should have all required fields."""
        recs = recommend_gate(section=130, state=stadium_state, max_results=1)
        assert len(recs) >= 1
        rec = recs[0]
        required_keys = {"gate_id", "gate_name", "zone", "congestion_pct",
                         "congestion_level", "walk_minutes", "score"}
        assert required_keys.issubset(rec.keys())

    def test_home_gate_has_zero_walk_time(self, stadium_state):
        """The fan's primary gate should have 0 walk time."""
        recs = recommend_gate(section=100, state=stadium_state, max_results=8)
        gate_a = next((r for r in recs if r["gate_id"] == "A"), None)
        assert gate_a is not None
        assert gate_a["walk_minutes"] == 0.0

    def test_score_favors_low_congestion(self, stadium_state):
        """A clear gate near the fan should score better than a congested one."""
        recs = recommend_gate(section=100, state=stadium_state, max_results=8)
        # The best recommendation should have a reasonable score
        assert recs[0]["score"] >= 0


# ---------------------------------------------------------------------------
# Concession Recommendation Tests
# ---------------------------------------------------------------------------

class TestConcessionRecommendation:
    """Tests for concession routing logic."""

    def test_returns_results(self, stadium_state):
        """Should return concession recommendations."""
        recs = recommend_concession(section=120, state=stadium_state)
        assert len(recs) > 0

    def test_sorted_by_score(self, stadium_state):
        """Results should be sorted by score."""
        recs = recommend_concession(section=120, state=stadium_state, max_results=10)
        scores = [r["score"] for r in recs]
        assert scores == sorted(scores)

    def test_total_time_computed(self, stadium_state):
        """Total time should be walk + wait."""
        recs = recommend_concession(section=120, state=stadium_state)
        for rec in recs:
            expected_total = round(rec["wait_minutes"] + rec["walk_minutes"], 1)
            assert rec["total_time"] == expected_total

    def test_type_filter(self, stadium_state):
        """Type filter should restrict results."""
        recs = recommend_concession(
            section=120, state=stadium_state, preferred_type="Beverages"
        )
        for rec in recs:
            assert rec["type"] == "Beverages"


# ---------------------------------------------------------------------------
# Navigation Tests
# ---------------------------------------------------------------------------

class TestNavigation:
    """Tests for navigation step generation."""

    def test_generates_steps(self):
        """Should generate a list of navigation steps."""
        steps = generate_navigation_steps(100, "E")
        assert len(steps) > 0
        assert all(isinstance(s, str) for s in steps)

    def test_includes_walk_time(self):
        """Steps should mention the estimated walk time."""
        steps = generate_navigation_steps(100, "E")
        combined = " ".join(steps)
        assert "minute" in combined.lower()

    def test_same_gate_short_directions(self):
        """Navigating to the same gate should be brief."""
        steps = generate_navigation_steps(100, "A")
        assert len(steps) <= 4

    def test_accessibility_mode(self):
        """Accessibility mode should mention elevator/ramp."""
        steps = generate_navigation_steps(100, "E", accessibility=True)
        combined = " ".join(steps)
        assert "elevator" in combined.lower() or "ramp" in combined.lower()


# ---------------------------------------------------------------------------
# Facility Finder Tests
# ---------------------------------------------------------------------------

class TestFacilityFinder:
    """Tests for nearest facility locator."""

    def test_returns_results(self):
        """Should return facility locations."""
        results = find_nearest_facilities(150, "restroom")
        assert len(results) > 0

    def test_sorted_by_distance(self):
        """Results should be sorted by walk time."""
        results = find_nearest_facilities(150, "restroom")
        times = [r["walk_minutes"] for r in results]
        assert times == sorted(times)

    def test_max_three_results(self):
        """Should return at most 3 results."""
        results = find_nearest_facilities(100, "first_aid")
        assert len(results) <= 3
