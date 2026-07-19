"""
Queue Routing Service
=====================
Core algorithmic engine for intelligent routing decisions:

1. **Gate Load Balancing** — Recommends optimal gates based on
   current congestion weighted by walking distance from a fan's
   section.
2. **Concession Routing** — Finds the nearest low-wait concession
   stand for a given seat location and preference.
3. **Walk-Time Estimation** — Uses the adjacency matrix from config
   to compute estimated walk times between any two points.

All functions are pure (no side effects) and operate on StadiumState
snapshots, making them straightforward to unit test.
"""

from __future__ import annotations

from backend.config import GATES, WALK_TIMES
from backend.models.stadium import ConcessionZone, GateStatus, StadiumState


# Precompute O(1) spatial index for instant section-to-gate routing
# This eliminates O(N^2) looping under 82,500 simultaneous fan queries
SECTION_TO_GATE_INDEX: dict[int, str] = {
    section: gate_id
    for gate_id, gate_config in GATES.items()
    for section in gate_config["sections"]
}

def get_gate_for_section(section: int) -> str:
    """
    Return the nearest stadium gate for a given section number.

    Sections 100–199 map to gates A–H as defined in config.GATES.
    Any section outside that range (including None, negative, or zero)
    falls back to Gate A as the default entry point.

    Args:
        section: Fan's stadium section number.

    Returns:
        Gate identifier string (e.g. 'A', 'B', ..., 'H').
    """
    # Guard against None or non-integer input — return the fallback gate
    # rather than crashing on a bitwise operation with an unexpected type.
    if not isinstance(section, int):
        return "A"

    return SECTION_TO_GATE_INDEX.get(section, "A")


def compute_walk_time(from_gate: str, to_gate: str) -> float:
    """
    Estimate the walking time between two stadium gates in minutes.

    Uses the pre-computed adjacency matrix (config.WALK_TIMES) which
    encodes real MetLife Stadium concourse distances:
        - Adjacent gates (e.g. A↔B, A↔H): 3 minutes
        - Two gates apart (e.g. A↔C):     5 minutes
        - Three gates apart (e.g. A↔D):   7 minutes
        - Opposite gates (e.g. A↔E):      8 minutes

    Args:
        from_gate: Starting gate identifier.
        to_gate:   Destination gate identifier.

    Returns:
        Walk time in minutes, or 5.0 if either gate is unknown/None.
    """
    if from_gate is None or to_gate is None:
        return 5.0

    if from_gate == to_gate:
        return 0.0

    return WALK_TIMES.get(from_gate, {}).get(to_gate, 5.0)


def recommend_gate(
    section: int,
    state: StadiumState,
    max_results: int = 3,
) -> list[dict]:
    """
    Recommend the best entry/exit gates for a fan in a given section.

    The scoring formula balances congestion and proximity:
        score = congestion_pct × 0.6 + walk_time_normalized × 0.4

    walk_time_normalized scales the walk time (0–8 min) to a 0–100 range
    so it is comparable to congestion_pct.  Lower scores are better.
    Gates that are closed are excluded.

    Args:
        section: Fan's stadium section number.
        state: Current stadium state snapshot.
        max_results: Maximum number of recommendations to return.

    Returns:
        List of recommendation dicts sorted by score (best first).
    """
    home_gate = get_gate_for_section(section)
    recommendations = []

    for gate in state.gates:
        if not gate.is_open:
            continue

        walk_time = compute_walk_time(home_gate, gate.gate_id)
        # Scale walk time to 0–100 so it is comparable to congestion_pct.
        # Maximum walk across the stadium is 8 minutes.
        walk_normalized = min(100.0, (walk_time / 8.0) * 100.0)

        score = gate.congestion_pct * 0.6 + walk_normalized * 0.4

        recommendations.append({
            "gate_id": gate.gate_id,
            "gate_name": gate.name,
            "zone": gate.zone,
            "congestion_pct": gate.congestion_pct,
            "congestion_level": gate.congestion_level.value,
            "walk_minutes": walk_time,
            "score": round(score, 2),
        })

    # Sort by composite score ascending (best first)
    recommendations.sort(key=lambda r: r["score"])
    return recommendations[:max_results]


def recommend_concession(
    section: int,
    state: StadiumState,
    preferred_type: str | None = None,
    max_results: int = 3,
) -> list[dict]:
    """
    Find the best concession stands for a fan based on proximity
    and current queue length.

    Scoring formula:
        score = wait_minutes × 0.5 + walk_time_normalized × 0.3
                + queue_ratio × 0.2

    Args:
        section: Fan's stadium section number.
        state: Current stadium state snapshot.
        preferred_type: Optional filter (e.g., "Food Court", "Beverages").
        max_results: Maximum number of recommendations.

    Returns:
        Sorted list of concession recommendation dicts.
    """
    home_gate = get_gate_for_section(section)
    recommendations = []

    for concession in state.concessions:
        if not concession.is_open:
            continue

        # Apply type filter if specified
        if preferred_type and concession.zone_type.lower() != preferred_type.lower():
            continue

        walk_time = compute_walk_time(home_gate, concession.zone)
        walk_normalized = min(100.0, (walk_time / 8.0) * 100.0)
        queue_ratio = (concession.current_queue / concession.max_queue) * 100.0

        score = (
            concession.wait_minutes * 0.5
            + walk_normalized * 0.3
            + queue_ratio * 0.2
        )

        recommendations.append({
            "zone_id": concession.zone_id,
            "name": concession.name,
            "type": concession.zone_type,
            "level": concession.level,
            "current_queue": concession.current_queue,
            "max_queue": concession.max_queue,
            "wait_minutes": concession.wait_minutes,
            "walk_minutes": walk_time,
            "total_time": round(concession.wait_minutes + walk_time, 1),
            "score": round(score, 2),
        })

    recommendations.sort(key=lambda r: r["score"])
    return recommendations[:max_results]


def find_nearest_facilities(
    section: int,
    facility_type: str = "restroom",
) -> list[dict]:
    """
    Return the nearest facilities of a given type relative to a section.

    This uses a simplified model where facilities are co-located
    with gates (each gate has restrooms and first-aid stations).

    Args:
        section: Fan's stadium section number.
        facility_type: Type of facility ("restroom", "first_aid", "info_desk").

    Returns:
        List of facility locations sorted by walk time.
    """
    home_gate = get_gate_for_section(section)
    results = []

    for gate_id in GATES:
        walk_time = compute_walk_time(home_gate, gate_id)
        results.append({
            "facility_type": facility_type,
            "location": f"Level 1, near Gate {gate_id} ({GATES[gate_id]['zone']})",
            "walk_minutes": walk_time,
            "gate_proximity": gate_id,
        })

    results.sort(key=lambda r: r["walk_minutes"])
    return results[:3]


def generate_navigation_steps(
    from_section: int,
    to_gate: str,
    accessibility: bool = False,
) -> list[str]:
    """
    Generate human-readable step-by-step navigation instructions.

    Args:
        from_section: Starting section number.
        to_gate: Destination gate identifier.
        accessibility: If True, prefer elevator/ramp routes.

    Returns:
        List of direction strings.
    """
    home_gate = get_gate_for_section(from_section)
    walk_time = compute_walk_time(home_gate, to_gate)
    home_zone = GATES[home_gate]["zone"]
    dest_zone = GATES[to_gate]["zone"]

    steps = [
        f"From Section {from_section}, head to the nearest concourse exit.",
    ]

    if accessibility:
        steps.append("Take the elevator or ramp to the main concourse level (Level 1).")
    else:
        steps.append("Take the stairs or escalator down to the main concourse level.")

    if home_gate == to_gate:
        steps.append(f"Gate {to_gate} is directly ahead — approximately 1 minute walk.")
    else:
        # Determine direction (clockwise vs counter-clockwise)
        gate_order = list(GATES.keys())
        from_idx = gate_order.index(home_gate)
        to_idx = gate_order.index(to_gate)
        clockwise_dist = (to_idx - from_idx) % len(gate_order)
        counter_dist = (from_idx - to_idx) % len(gate_order)

        if clockwise_dist <= counter_dist:
            direction = "clockwise (right)"
        else:
            direction = "counter-clockwise (left)"

        steps.append(
            f"Follow the main concourse {direction} from {home_zone} toward {dest_zone}."
        )
        steps.append(
            f"Continue along the concourse for approximately {walk_time:.0f} minutes."
        )
        steps.append(f"Gate {to_gate} ({dest_zone}) will be on your right.")

    steps.append(
        f"Estimated total walk time: {walk_time:.0f} minutes."
    )

    if accessibility:
        steps.append(
            "Accessible seating and restroom facilities are available at your destination."
        )

    return steps
