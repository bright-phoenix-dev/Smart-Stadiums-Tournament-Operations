"""
Stadium Simulation Engine
==========================
Generates realistic, time-varying stadium operational data that
drives the entire platform.  The engine models MetLife Stadium
across five match phases, producing gate congestion curves,
concession queue fluctuations, transit delays, and random
incidents on every tick.

Architecture:
    - The engine is a singleton managed by the FastAPI app lifespan.
    - On each tick (every SIMULATION_TICK_SECONDS), it mutates an
      internal StadiumState and broadcasts deltas to all connected
      WebSocket clients.
    - Congestion follows sinusoidal curves modulated by the phase's
      gate_load_factor, with Gaussian noise for realism.
    - Incidents are generated stochastically based on weighted
      probabilities from config.INCIDENT_WEIGHTS.

Thread Safety:
    - State reads are safe for concurrent coroutines because the
      event loop is single-threaded.  The `_lock` is provided as
      future-proofing for potential multi-worker deployments.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import time
from datetime import datetime
from typing import Optional

from backend.config import (
    CONCESSION_ZONES,
    GATES,
    INCIDENT_WEIGHTS,
    MATCH_PHASES,
    SIMULATION_TICK_SECONDS,
    STADIUM_CAPACITY,
    TRANSIT_HUBS,
)
from backend.models.stadium import (
    ConcessionZone,
    CongestionLevel,
    GateStatus,
    IncidentReport,
    IncidentType,
    MatchPhase,
    OperationalAlert,
    SeverityLevel,
    StadiumState,
    TransitHub,
    TransitType,
)

logger = logging.getLogger(__name__)


class StadiumSimulator:
    """
    Stateful simulation engine producing realistic stadium data.

    Usage:
        simulator = StadiumSimulator()
        await simulator.start()   # begins background tick loop
        state = simulator.get_current_state()
        await simulator.stop()
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        """
        Initialize the simulator.

        Args:
            seed: Optional random seed for reproducible simulations (useful in tests).
        """
        self._rng = random.Random(seed)
        self._tick: int = 0
        self._phase_index: int = 0
        self._phase_tick: int = 0
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._subscribers: list[asyncio.Queue] = []

        # Pre-allocate incident pool to avoid repeated object construction during ticks.
        self._incident_pool = [IncidentReport(
            incident_id=f"pool-{i}",
            incident_type=IncidentType.MEDICAL,
            location="",
            description="",
            severity=SeverityLevel.LOW,
            timestamp=datetime.utcnow()
        ) for i in range(500)]
        self._incident_pool_index = 0

        # Mutable state containers
        self._gate_congestions: dict[str, float] = {gid: 0.0 for gid in GATES}
        self._concession_queues: dict[str, int] = {
            cz["id"]: 0 for cz in CONCESSION_ZONES
        }
        self._transit_delays: dict[str, float] = {
            th["id"]: 0.0 for th in TRANSIT_HUBS
        }
        self._incidents: list[IncidentReport] = []
        self._alerts: list[OperationalAlert] = []
        self._attendance: int = 0

        logger.info("StadiumSimulator initialized (seed=%s)", seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Begin the background simulation loop."""
        if self._running:
            logger.warning("Simulator already running — ignoring start()")
            return
        self._running = True
        self._task = asyncio.create_task(self._tick_loop())
        logger.info("Simulation started — tick interval: %ds", SIMULATION_TICK_SECONDS)

    async def stop(self) -> None:
        """Gracefully stop the simulation loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Simulation stopped at tick %d", self._tick)

    def subscribe(self) -> asyncio.Queue:
        """
        Register a subscriber for real-time state updates.
        Returns an asyncio.Queue that will receive StadiumState
        snapshots on every tick.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    def get_current_state(self) -> StadiumState:
        """Build and return the current stadium state snapshot."""
        return self._build_state()

    @property
    def is_running(self) -> bool:
        """Whether the simulation loop is active."""
        return self._running

    @property
    def current_tick(self) -> int:
        """Current simulation tick number."""
        return self._tick

    # ------------------------------------------------------------------
    # Simulation Loop
    # ------------------------------------------------------------------

    async def _tick_loop(self) -> None:
        """Main simulation loop — runs until stopped."""
        while self._running:
            try:
                await self._advance_tick()
                state = self._build_state()
                await self._broadcast(state)
                await asyncio.sleep(SIMULATION_TICK_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in simulation tick %d", self._tick)
                await asyncio.sleep(SIMULATION_TICK_SECONDS)

    async def _advance_tick(self) -> None:
        """Compute the next simulation tick's data."""
        async with self._lock:
            self._tick += 1
            self._phase_tick += 1

            # Advance match phase if current phase duration is exhausted
            current_phase = MATCH_PHASES[self._phase_index]
            if self._phase_tick > current_phase["duration_ticks"]:
                if self._phase_index < len(MATCH_PHASES) - 1:
                    self._phase_index += 1
                    self._phase_tick = 1
                    logger.info(
                        "Phase transition → %s",
                        MATCH_PHASES[self._phase_index]["name"],
                    )

            phase = MATCH_PHASES[self._phase_index]
            load_factor = phase["gate_load_factor"]

            self._update_attendance(load_factor)
            self._update_gate_congestion(load_factor)
            self._update_concession_queues(phase["name"])
            self._update_transit_delays(phase["name"])
            self._maybe_generate_incident(phase["name"])
            self._generate_alerts()

    # ------------------------------------------------------------------
    # Data Generation Methods
    # ------------------------------------------------------------------

    def _update_attendance(self, load_factor: float) -> None:
        """
        Model attendance as a function of phase.
        Pre-match ramps up, post-match ramps down.
        """
        target = int(STADIUM_CAPACITY * min(1.0, 0.3 + load_factor * 0.8))
        # Smooth interpolation toward target
        delta = (target - self._attendance) * 0.1
        self._attendance = max(0, min(STADIUM_CAPACITY, int(self._attendance + delta)))

    def _update_gate_congestion(self, load_factor: float) -> None:
        """
        Compute gate congestion using a sinusoidal base curve
        modulated by load_factor, with per-gate Gaussian noise.

        The sinusoidal component creates natural ebb-and-flow patterns.
        """
        base_angle = (self._tick % 72) / 72 * 2 * math.pi
        for gate_id in GATES:
            # Sinusoidal base + load factor scaling
            sin_component = (math.sin(base_angle + hash(gate_id) % 7) + 1) / 2
            base_congestion = sin_component * load_factor * 100
            # Gaussian noise (σ = 8% of range) for realism
            noise = self._rng.gauss(0, 8)
            raw = base_congestion + noise
            # Clamp to [0, 100]
            self._gate_congestions[gate_id] = max(0.0, min(100.0, raw))

    def _update_concession_queues(self, phase_name: str) -> None:
        """
        Model concession queue lengths with phase-dependent demand.
        Halftime and pre-match see highest concession traffic.
        """
        demand_multipliers = {
            "Pre-Match": 0.6,
            "1st Half": 0.25,
            "Halftime": 0.95,
            "2nd Half": 0.20,
            "Post-Match": 0.15,
        }
        demand = demand_multipliers.get(phase_name, 0.3)

        for cz_config in CONCESSION_ZONES:
            zone_id = cz_config["id"]
            max_q = cz_config["max_queue"]
            # Random walk with drift toward demand-driven target
            target = int(max_q * demand)
            current = self._concession_queues[zone_id]
            step = self._rng.randint(-3, 5) + int((target - current) * 0.2)
            self._concession_queues[zone_id] = max(0, min(max_q, current + step))

    def _update_transit_delays(self, phase_name: str) -> None:
        """
        Simulate transit delays — higher during post-match exodus.
        Rail is more stable; rideshare has higher variance.
        """
        base_delay = 2.0 if phase_name == "Post-Match" else 0.5

        for th_config in TRANSIT_HUBS:
            hub_id = th_config["id"]
            type_variance = {
                "rail": 1.0,
                "bus": 2.5,
                "rideshare": 4.0,
            }
            variance = type_variance.get(th_config["type"], 2.0)
            noise = self._rng.gauss(0, variance)
            raw_delay = base_delay + abs(noise)
            self._transit_delays[hub_id] = max(0.0, round(raw_delay, 1))

    def _maybe_generate_incident(self, phase_name: str) -> None:
        """
        Stochastically generate incidents based on weighted probabilities.
        Probability is higher during high-traffic phases.
        """
        # Remove old resolved incidents (keep last 20)
        self._incidents = [i for i in self._incidents if not i.is_resolved][-20:]

        # Base probability per tick: 3%, scaled by phase
        phase_prob = {"Pre-Match": 1.2, "Halftime": 1.5, "Post-Match": 1.3}.get(
            phase_name, 1.0
        )
        if self._rng.random() > 0.03 * phase_prob:
            return

        # Weighted random incident type selection
        types = list(INCIDENT_WEIGHTS.keys())
        weights = list(INCIDENT_WEIGHTS.values())
        chosen_type = self._rng.choices(types, weights=weights, k=1)[0]

        # Random location
        gate_id = self._rng.choice(list(GATES.keys()))
        section = self._rng.choice(GATES[gate_id]["sections"])
        location = f"Section {section}, near Gate {gate_id}"

        # Severity distribution
        severity = self._rng.choices(
            [SeverityLevel.LOW, SeverityLevel.MEDIUM, SeverityLevel.HIGH, SeverityLevel.CRITICAL],
            weights=[0.4, 0.35, 0.2, 0.05],
            k=1,
        )[0]

        descriptions = {
            "medical": [
                "Fan reporting dizziness, requesting medical assistance",
                "Minor injury from trip on concourse stairs",
                "Heat-related complaint — fan requesting water and shade",
                "Allergic reaction reported at concession stand",
            ],
            "crowd_control": [
                "Crowd density exceeding safe limits in concourse",
                "Unauthorized entry attempt detected at gate perimeter",
                "Fan altercation requiring security intervention",
                "Standing crowd blocking emergency exit path",
            ],
            "facility": [
                "Restroom facility out of order — plumbing issue",
                "Escalator malfunction on Level 3",
                "Lighting failure in concourse section",
                "Spill hazard on main concourse — cleanup needed",
            ],
            "weather": [
                "Wind advisory — loose signage at Gate area",
                "Rain shelter capacity reaching limit",
                "Temperature alert — heat index exceeding comfort threshold",
                "Lightning detection within 10-mile radius",
            ],
        }

        incident = IncidentReport(
            incident_type=IncidentType(chosen_type),
            severity=severity,
            location=location,
            description=self._rng.choice(descriptions.get(chosen_type, ["Incident reported"])),
            timestamp=datetime.utcnow(),
        )
        self._incidents.append(incident)
        logger.info("Incident generated: [%s] %s at %s", severity.value, chosen_type, location)

    def _generate_alerts(self) -> None:
        """
        Generate operational alerts when thresholds are breached.
        Alerts auto-clear when conditions normalize.
        """
        self._alerts = []

        # Gate congestion alerts
        for gate_id, congestion in self._gate_congestions.items():
            if congestion > 85:
                self._alerts.append(OperationalAlert(
                    severity=SeverityLevel.CRITICAL if congestion > 95 else SeverityLevel.HIGH,
                    title=f"Gate {gate_id} Congestion Critical",
                    message=(
                        f"Gate {gate_id} ({GATES[gate_id]['zone']}) at {congestion:.0f}% capacity. "
                        f"Recommend rerouting fans to adjacent gates."
                    ),
                    source=f"gate_{gate_id}",
                ))
            elif congestion > 70:
                self._alerts.append(OperationalAlert(
                    severity=SeverityLevel.MEDIUM,
                    title=f"Gate {gate_id} Congestion Elevated",
                    message=f"Gate {gate_id} at {congestion:.0f}% — monitor closely.",
                    source=f"gate_{gate_id}",
                ))

        # Concession overflow alerts
        for cz_config in CONCESSION_ZONES:
            zone_id = cz_config["id"]
            queue = self._concession_queues[zone_id]
            if queue > cz_config["max_queue"] * 0.9:
                self._alerts.append(OperationalAlert(
                    severity=SeverityLevel.HIGH,
                    title=f"{cz_config['name']} Queue Overflow",
                    message=(
                        f"Queue at {queue}/{cz_config['max_queue']}. "
                        f"Consider opening express lane or redirecting fans."
                    ),
                    source=zone_id,
                ))

        # Critical incident alerts
        critical_incidents = [
            i for i in self._incidents
            if i.severity in (SeverityLevel.HIGH, SeverityLevel.CRITICAL) and not i.is_resolved
        ]
        for incident in critical_incidents:
            self._alerts.append(OperationalAlert(
                severity=incident.severity,
                title=f"{incident.incident_type.value.replace('_', ' ').title()} — {incident.location}",
                message=incident.description,
                source=f"incident_{incident.incident_id}",
            ))

    # ------------------------------------------------------------------
    # State Building
    # ------------------------------------------------------------------

    def _build_state(self) -> StadiumState:
        """Assemble the complete StadiumState from internal data."""
        phase = MATCH_PHASES[self._phase_index]
        match_phase = MatchPhase(phase["name"])

        # Calculate match minute from cumulative ticks
        elapsed_ticks = sum(
            MATCH_PHASES[i]["duration_ticks"]
            for i in range(self._phase_index)
        ) + self._phase_tick
        match_minute = max(0, int(elapsed_ticks * SIMULATION_TICK_SECONDS / 60))

        # Build gate statuses
        gates = []
        for gate_id, gate_config in GATES.items():
            congestion = self._gate_congestions[gate_id]
            gates.append(GateStatus(
                gate_id=gate_id,
                name=gate_config["name"],
                zone=gate_config["zone"],
                congestion_pct=round(congestion, 1),
                congestion_level=GateStatus.classify_congestion(congestion),
                throughput_current=int(gate_config["max_throughput"] * (1 - congestion / 100) / 720),
                max_throughput=gate_config["max_throughput"],
                is_open=True,
                sections_served=gate_config["sections"],
            ))

        # Build concession statuses
        concessions = []
        for cz_config in CONCESSION_ZONES:
            zone_id = cz_config["id"]
            queue = self._concession_queues[zone_id]
            wait = round(queue * 0.4, 1)  # ~24 seconds per person in queue
            concessions.append(ConcessionZone(
                zone_id=zone_id,
                name=cz_config["name"],
                level=cz_config["level"],
                zone=cz_config["zone"],
                zone_type=cz_config["type"],
                current_queue=queue,
                max_queue=cz_config["max_queue"],
                wait_minutes=wait,
                is_open=True,
            ))

        # Build transit hub statuses
        transit_hubs = []
        for th_config in TRANSIT_HUBS:
            hub_id = th_config["id"]
            delay = self._transit_delays[hub_id]
            capacity_used = min(95, max(10, 50 + self._rng.gauss(0, 15)))
            next_dep = max(1, self._rng.randint(3, 20) - int(delay))
            transit_hubs.append(TransitHub(
                hub_id=hub_id,
                name=th_config["name"],
                transit_type=TransitType(th_config["type"]),
                delay_minutes=delay,
                capacity_remaining_pct=round(100 - capacity_used, 1),
                next_departure_minutes=float(next_dep),
                gate_proximity=th_config["gate_proximity"],
                status="delayed" if delay > 5 else ("slight delay" if delay > 2 else "on-time"),
            ))

        return StadiumState(
            timestamp=datetime.utcnow(),
            match_phase=match_phase,
            match_minute=match_minute,
            total_attendance=self._attendance,
            stadium_capacity=STADIUM_CAPACITY,
            gates=gates,
            concessions=concessions,
            transit_hubs=transit_hubs,
            active_incidents=[i for i in self._incidents if not i.is_resolved],
            alerts=self._alerts,
            simulation_tick=self._tick,
        )

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------

    async def _broadcast(self, state: StadiumState) -> None:
        """Push state snapshot to all subscriber queues."""
        dead_queues = []
        for queue in self._subscribers:
            try:
                # Non-blocking put — drop oldest if queue is full
                if queue.full():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                queue.put_nowait(state)
            except Exception:
                dead_queues.append(queue)

        # Clean up dead subscribers
        for dq in dead_queues:
            self._subscribers.remove(dq)


# Module-level singleton instance
simulator = StadiumSimulator()
