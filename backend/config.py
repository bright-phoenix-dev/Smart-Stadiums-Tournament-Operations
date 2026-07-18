"""
Configuration Module — Smart Stadium Operations Platform
=========================================================
Centralizes all application settings, stadium physical constants,
and operational parameters. Values are loaded from environment
variables where appropriate, with sensible defaults for local
development and demonstration.

Design Decision: A flat module with typed constants is chosen over
a class-based config to keep imports simple and allow easy mocking
in tests.  All "magic numbers" in the codebase trace back here.
"""

import os
from typing import Final

# ---------------------------------------------------------------------------
# Application Settings
# ---------------------------------------------------------------------------

APP_TITLE: Final[str] = "FIFA World Cup 2026 — Smart Stadium Platform"
APP_VERSION: Final[str] = "1.0.0"
APP_DESCRIPTION: Final[str] = (
    "GenAI-powered solution to optimize stadium operations and enhance "
    "the FIFA World Cup 2026 experience through intelligent, real-time assistance."
)

# Allowed origins for CORS — tighten in production
CORS_ORIGINS: Final[list[str]] = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")
ENVIRONMENT: Final[str] = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION: Final[bool] = ENVIRONMENT.lower() == "production"

# ---------------------------------------------------------------------------
# GenAI / LLM Settings
# ---------------------------------------------------------------------------

GEMINI_API_KEY: Final[str] = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: Final[str] = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Maximum tokens allocated for context injection to control costs & latency
MAX_CONTEXT_TOKENS: Final[int] = 2048
# Maximum user message length (characters) to prevent abuse
MAX_USER_MESSAGE_LENGTH: Final[int] = 500

# ---------------------------------------------------------------------------
# Security Settings
# ---------------------------------------------------------------------------

# Simple JWT-style secret for role token signing (demo purposes)
JWT_SECRET: Final[str] = os.getenv("JWT_SECRET", "stadium-ops-secret-2026")
JWT_ALGORITHM: Final[str] = "HS256"
TOKEN_EXPIRY_HOURS: Final[int] = 24

# Role identifiers used for RBAC enforcement
ROLE_STAFF: Final[str] = "staff"
ROLE_FAN: Final[str] = "fan"

# Rate limiting: requests per minute per IP
RATE_LIMIT_STAFF: Final[int] = 60
RATE_LIMIT_FAN: Final[int] = 30

# ---------------------------------------------------------------------------
# Stadium Physical Constants — MetLife Stadium, East Rutherford, NJ
# ---------------------------------------------------------------------------

STADIUM_NAME: Final[str] = "MetLife Stadium"
STADIUM_CAPACITY: Final[int] = 82_500

# Gate definitions: id → {name, location_description, max_throughput_per_hour}
GATES: Final[dict] = {
    "A": {"name": "Gate A", "zone": "North",  "max_throughput": 1200, "sections_served": list(range(100, 113))},
    "B": {"name": "Gate B", "zone": "North-East", "max_throughput": 1200, "sections_served": list(range(113, 125))},
    "C": {"name": "Gate C", "zone": "East",   "max_throughput": 1200, "sections_served": list(range(125, 138))},
    "D": {"name": "Gate D", "zone": "South-East", "max_throughput": 1200, "sections_served": list(range(138, 150))},
    "E": {"name": "Gate E", "zone": "South",  "max_throughput": 1200, "sections_served": list(range(150, 163))},
    "F": {"name": "Gate F", "zone": "South-West", "max_throughput": 1200, "sections_served": list(range(163, 175))},
    "G": {"name": "Gate G", "zone": "West",   "max_throughput": 1200, "sections_served": list(range(175, 188))},
    "H": {"name": "Gate H", "zone": "North-West", "max_throughput": 1200, "sections_served": list(range(188, 200))},
}

# Concession zone definitions
CONCESSION_ZONES: Final[list[dict]] = [
    {"id": f"CZ-{i+1:02d}", "name": f"Concession {i+1}", "level": (i % 4) + 1,
     "zone": list(GATES.keys())[i % 8], "type": t, "max_queue": 45}
    for i, t in enumerate([
        "Food Court", "Beverages", "Snacks", "Merchandise",
        "Food Court", "Beverages", "Snacks", "Premium Dining",
        "Food Court", "Beverages", "Snacks", "Merchandise",
        "Food Court", "Beverages", "Snacks", "Premium Dining",
        "Food Court", "Beverages", "Snacks", "Merchandise",
        "Food Court", "Beverages", "Snacks", "Premium Dining",
    ])
]

# Transit hub definitions
TRANSIT_HUBS: Final[list[dict]] = [
    {"id": "TH-01", "name": "NJ Transit Rail — Meadowlands Station", "type": "rail",
     "capacity_per_hour": 6000, "gate_proximity": "A"},
    {"id": "TH-02", "name": "Bus Lot — North", "type": "bus",
     "capacity_per_hour": 2000, "gate_proximity": "B"},
    {"id": "TH-03", "name": "Bus Lot — East", "type": "bus",
     "capacity_per_hour": 2000, "gate_proximity": "D"},
    {"id": "TH-04", "name": "Bus Lot — South", "type": "bus",
     "capacity_per_hour": 2000, "gate_proximity": "F"},
    {"id": "TH-05", "name": "Rideshare Zone — West Lot", "type": "rideshare",
     "capacity_per_hour": 1500, "gate_proximity": "G"},
    {"id": "TH-06", "name": "Rideshare Zone — VIP Drop-off", "type": "rideshare",
     "capacity_per_hour": 800, "gate_proximity": "H"},
]

# Walk-time adjacency matrix between gates (in minutes).
# Symmetric — WALK_TIMES[A][B] == WALK_TIMES[B][A].
WALK_TIMES: Final[dict[str, dict[str, float]]] = {
    "A": {"A": 0, "B": 3, "C": 5, "D": 7, "E": 8, "F": 7, "G": 5, "H": 3},
    "B": {"A": 3, "B": 0, "C": 3, "D": 5, "E": 7, "F": 8, "G": 7, "H": 5},
    "C": {"A": 5, "B": 3, "C": 0, "D": 3, "E": 5, "F": 7, "G": 8, "H": 7},
    "D": {"A": 7, "B": 5, "C": 3, "D": 0, "E": 3, "F": 5, "G": 7, "H": 8},
    "E": {"A": 8, "B": 7, "C": 5, "D": 3, "E": 0, "F": 3, "G": 5, "H": 7},
    "F": {"A": 7, "B": 8, "C": 7, "D": 5, "E": 3, "F": 0, "G": 3, "H": 5},
    "G": {"A": 5, "B": 7, "C": 8, "D": 7, "E": 5, "F": 3, "G": 0, "H": 3},
    "H": {"A": 3, "B": 5, "C": 7, "D": 8, "E": 7, "F": 5, "G": 3, "H": 0},
}

# ---------------------------------------------------------------------------
# Simulation Settings
# ---------------------------------------------------------------------------

# How often the simulator ticks (seconds)
SIMULATION_TICK_SECONDS: Final[int] = 5

# Match phases and their durations (in simulation ticks)
MATCH_PHASES: Final[list[dict]] = [
    {"name": "Pre-Match",  "duration_ticks": 60,  "gate_load_factor": 0.85},
    {"name": "1st Half",   "duration_ticks": 108,  "gate_load_factor": 0.10},
    {"name": "Halftime",   "duration_ticks": 36,  "gate_load_factor": 0.40},
    {"name": "2nd Half",   "duration_ticks": 108,  "gate_load_factor": 0.08},
    {"name": "Post-Match", "duration_ticks": 60,  "gate_load_factor": 0.90},
]

# Incident type weights for random generation
INCIDENT_WEIGHTS: Final[dict[str, float]] = {
    "medical": 0.40,
    "crowd_control": 0.30,
    "facility": 0.20,
    "weather": 0.10,
}

# Supported fan languages (ISO 639-1)
SUPPORTED_LANGUAGES: Final[list[dict]] = [
    {"code": "en", "name": "English"},
    {"code": "es", "name": "Español"},
    {"code": "fr", "name": "Français"},
    {"code": "ar", "name": "العربية"},
    {"code": "pt", "name": "Português"},
    {"code": "de", "name": "Deutsch"},
]
