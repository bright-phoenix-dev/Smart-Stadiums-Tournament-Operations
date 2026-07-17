"""
Stadium Data Models — Pydantic Schemas
=======================================
Defines every data structure flowing through the system: stadium
state snapshots, gate/concession/transit status, incidents, fan
profiles, and API request/response envelopes.

All models use Pydantic v2 for runtime validation, serialization,
and automatic OpenAPI schema generation via FastAPI.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class MatchPhase(str, Enum):
    """Current phase of the live match."""
    PRE_MATCH = "Pre-Match"
    FIRST_HALF = "1st Half"
    HALFTIME = "Halftime"
    SECOND_HALF = "2nd Half"
    POST_MATCH = "Post-Match"


class SeverityLevel(str, Enum):
    """Severity classification for incidents and alerts."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentType(str, Enum):
    """Category of a reported stadium incident."""
    MEDICAL = "medical"
    CROWD_CONTROL = "crowd_control"
    FACILITY = "facility"
    WEATHER = "weather"


class CongestionLevel(str, Enum):
    """Human-readable congestion classification derived from percentage."""
    CLEAR = "clear"           # 0–30%
    MODERATE = "moderate"     # 31–60%
    HEAVY = "heavy"           # 61–85%
    CRITICAL = "critical"     # 86–100%


class TransitType(str, Enum):
    """Type of transit service."""
    RAIL = "rail"
    BUS = "bus"
    RIDESHARE = "rideshare"


# ---------------------------------------------------------------------------
# Stadium Component Models
# ---------------------------------------------------------------------------

class GateStatus(BaseModel):
    """Real-time status of a single entry/exit gate."""
    model_config = ConfigDict(frozen=True)
    gate_id: str = Field(..., description="Gate identifier (A–H)")
    name: str = Field(..., description="Human-readable gate name")
    zone: str = Field(..., description="Stadium zone (e.g., North, South-East)")
    congestion_pct: float = Field(
        ..., ge=0, le=100,
        description="Current congestion percentage (0 = empty, 100 = blocked)"
    )
    congestion_level: CongestionLevel = Field(
        ..., description="Categorical congestion label"
    )
    throughput_current: int = Field(
        ..., ge=0,
        description="Current throughput (people processed this tick)"
    )
    max_throughput: int = Field(
        ..., gt=0,
        description="Maximum hourly throughput capacity"
    )
    is_open: bool = Field(True, description="Whether the gate is operational")
    sections_served: list[int] = Field(
        default_factory=list,
        description="Stadium section numbers served by this gate"
    )

    @classmethod
    def classify_congestion(cls, pct: float) -> CongestionLevel:
        """Derive the congestion level from a raw percentage value."""
        if pct <= 30:
            return CongestionLevel.CLEAR
        elif pct <= 60:
            return CongestionLevel.MODERATE
        elif pct <= 85:
            return CongestionLevel.HEAVY
        else:
            return CongestionLevel.CRITICAL


class ConcessionZone(BaseModel):
    """Status of a concession or merchandising zone."""
    model_config = ConfigDict(frozen=True)
    zone_id: str = Field(..., description="Zone identifier (CZ-01 to CZ-24)")
    name: str = Field(..., description="Human-readable zone name")
    level: int = Field(..., ge=1, le=4, description="Stadium level (1–4)")
    zone: str = Field(..., description="Nearest gate zone")
    zone_type: str = Field(..., description="Offering type (Food Court, Beverages, etc.)")
    current_queue: int = Field(..., ge=0, description="Current queue length (people)")
    max_queue: int = Field(..., gt=0, description="Queue capacity before overflow")
    wait_minutes: float = Field(..., ge=0, description="Estimated wait time in minutes")
    is_open: bool = Field(True, description="Whether the zone is open and serving")


class TransitHub(BaseModel):
    """Status of surrounding transit infrastructure."""
    model_config = ConfigDict(frozen=True)
    hub_id: str = Field(..., description="Hub identifier (TH-01 to TH-06)")
    name: str = Field(..., description="Human-readable hub name")
    transit_type: TransitType = Field(..., description="Type of transit service")
    delay_minutes: float = Field(
        ..., ge=0,
        description="Current delay from normal schedule (minutes)"
    )
    capacity_remaining_pct: float = Field(
        ..., ge=0, le=100,
        description="Remaining capacity as percentage"
    )
    next_departure_minutes: float = Field(
        ..., ge=0,
        description="Minutes until next departure"
    )
    gate_proximity: str = Field(
        ..., description="Nearest gate for walking directions"
    )
    status: str = Field("on-time", description="Schedule status label")


class IncidentReport(BaseModel):
    """A tracked operational or safety incident."""
    model_config = ConfigDict(frozen=True)
    incident_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())[:8],
        description="Short unique identifier"
    )
    incident_type: IncidentType = Field(..., description="Incident category")
    severity: SeverityLevel = Field(..., description="Severity level")
    location: str = Field(..., description="Location description (e.g., Section 142, Gate D)")
    description: str = Field(..., description="Brief incident description")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the incident was reported"
    )
    is_resolved: bool = Field(False, description="Whether the incident is resolved")
    assigned_to: Optional[str] = Field(None, description="Staff member assigned")


class OperationalAlert(BaseModel):
    """System-generated alert for operations staff."""
    model_config = ConfigDict(frozen=True)
    alert_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())[:8],
        description="Short unique identifier"
    )
    severity: SeverityLevel = Field(..., description="Alert severity")
    title: str = Field(..., description="Alert headline")
    message: str = Field(..., description="Detailed alert message")
    source: str = Field(..., description="Component that triggered the alert")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the alert was generated"
    )
    is_acknowledged: bool = Field(False, description="Staff acknowledgement status")


# ---------------------------------------------------------------------------
# Aggregate State Model
# ---------------------------------------------------------------------------

class StadiumState(BaseModel):
    """Master aggregate representing the full stadium snapshot."""
    model_config = ConfigDict(frozen=True)
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Snapshot timestamp"
    )
    match_phase: MatchPhase = Field(..., description="Current match phase")
    match_minute: int = Field(
        ..., ge=0,
        description="Current match minute (0 = pre-match start)"
    )
    total_attendance: int = Field(..., ge=0, description="Fans currently inside")
    stadium_capacity: int = Field(82_500, description="Total capacity")
    gates: list[GateStatus] = Field(..., description="All gate statuses")
    concessions: list[ConcessionZone] = Field(..., description="All concession statuses")
    transit_hubs: list[TransitHub] = Field(..., description="All transit hub statuses")
    active_incidents: list[IncidentReport] = Field(
        default_factory=list,
        description="Unresolved incidents"
    )
    alerts: list[OperationalAlert] = Field(
        default_factory=list,
        description="Active operational alerts"
    )
    simulation_tick: int = Field(0, ge=0, description="Current simulation tick number")


# ---------------------------------------------------------------------------
# Fan Profile
# ---------------------------------------------------------------------------

class FanProfile(BaseModel):
    """Context about a fan for personalized assistant responses."""
    model_config = ConfigDict(frozen=True)
    seat_section: int = Field(
        ..., ge=100, le=199,
        description="Stadium section number (100–199)"
    )
    seat_row: Optional[str] = Field(None, description="Row letter/number")
    seat_number: Optional[int] = Field(None, ge=1, description="Seat number")
    language: str = Field("en", description="Preferred language (ISO 639-1)")
    accessibility_needs: bool = Field(
        False, description="Whether the fan needs accessible routes"
    )

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        """Ensure language code is one we support, fallback to English."""
        supported = {"en", "es", "fr", "ar", "pt", "de"}
        return value if value in supported else "en"


# ---------------------------------------------------------------------------
# API Request / Response Schemas
# ---------------------------------------------------------------------------

class AssistantRequest(BaseModel):
    """Payload for GenAI operations assistant queries."""
    model_config = ConfigDict(frozen=True)
    message: str = Field(
        ..., min_length=1, max_length=500,
        description="User's question or request"
    )
    fan_profile: Optional[FanProfile] = Field(
        None, description="Fan context (only for fan-facing queries)"
    )
    conversation_id: Optional[str] = Field(
        None, description="Conversation thread identifier for context continuity"
    )

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, value: str) -> str:
        """Basic input sanitization — strip control characters."""
        return "".join(
            char for char in value.strip()
            if char.isprintable() or char in ("\n", "\t")
        )


class AssistantResponse(BaseModel):
    """Response envelope from the GenAI assistant."""
    model_config = ConfigDict(frozen=True)
    reply: str = Field(..., description="Assistant's response text")
    context_used: Optional[str] = Field(
        None, description="Summary of stadium context injected (staff debug info)"
    )
    conversation_id: str = Field(..., description="Conversation thread identifier")
    processing_time_ms: float = Field(
        ..., ge=0, description="End-to-end processing time in milliseconds"
    )


class NavigationRequest(BaseModel):
    """Fan wayfinding request."""
    from_section: int = Field(..., ge=100, le=199, description="Starting section")
    destination: str = Field(
        ..., description="Destination description (e.g., 'Gate A', 'Concession 5', 'Restroom')"
    )
    accessibility_needs: bool = Field(False, description="Require accessible route")


class NavigationResponse(BaseModel):
    """Wayfinding result with step-by-step directions."""
    from_section: int = Field(..., description="Starting section")
    destination: str = Field(..., description="Destination")
    estimated_walk_minutes: float = Field(..., ge=0, description="Estimated walk time")
    steps: list[str] = Field(..., description="Step-by-step directions")
    accessibility_route: bool = Field(False, description="Whether this is an accessible route")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field("healthy", description="Service status")
    version: str = Field(..., description="Application version")
    simulation_active: bool = Field(..., description="Whether simulation is running")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
