# 🏟️ FIFA World Cup 2026 — Smart Stadium Platform

A **GenAI-powered solution** to optimize stadium operations and enhance the FIFA World Cup 2026 experience through intelligent, real-time assistance.

> **Dual-interface system**: An Operational Dashboard for tournament staff and an Intelligent Real-Time Assistant Widget for fans attending the match at **MetLife Stadium, East Rutherford, NJ**.

---

## 📋 Table of Contents

1. [Chosen Vertical](#chosen-vertical)
2. [Approach and Logic](#approach-and-logic)
3. [How the Solution Works](#how-the-solution-works)
4. [Assumptions Made](#assumptions-made)
5. [Evaluation Focus Areas](#evaluation-focus-areas)
6. [Project Structure](#project-structure)
7. [Getting Started](#getting-started)
8. [API Reference](#api-reference)

---

## 🏟️ Chosen Vertical

### MetLife Stadium — FIFA World Cup 2026 Final Venue

This solution specifically models **MetLife Stadium** in East Rutherford, New Jersey — the venue for the FIFA World Cup 2026 Final. The platform addresses two critical operational domains:

**1. Stadium Operations Optimization (Staff Interface)**
- Real-time monitoring of 8 entry/exit gates (A–H) with congestion tracking
- 24 concession zone queue management across 4 stadium levels
- 6 transit hub coordination (NJ Transit rail, 3 bus lots, 2 rideshare zones)
- Incident response management with severity classification
- GenAI-powered operational recommendations for crowd flow optimization

**2. Fan Experience Enhancement (Fan Interface)**
- Hyper-localized assistance based on seat section (100–199)
- Multi-language support (English, Spanish, French, Arabic, Portuguese, German)
- Real-time concession queue tracking with walk-time estimates
- Step-by-step wayfinding with accessibility route options
- Post-match transit planning with multi-modal comparison

---

## 🧠 Approach and Logic

### Architectural Philosophy

The system follows a **layered clean architecture** pattern with strict separation of concerns:

```
┌─────────────────────────────────────────────────┐
│  Frontend (React + Vite)                        │
│  ├── Pages (Dashboard, FanView)                 │
│  ├── Components (Presentational, stateless)     │
│  ├── Hooks (State management + WebSocket)       │
│  └── Services (API communication layer)         │
├─────────────────────────────────────────────────┤
│  Backend (FastAPI)                              │
│  ├── Routes (API endpoints — thin controllers)  │
│  ├── Services (Business logic — pure functions) │
│  ├── Middleware (Security, RBAC, rate limiting)  │
│  ├── Simulation (Data generation engine)        │
│  └── Models (Pydantic schemas — shared types)   │
└─────────────────────────────────────────────────┘
```

### Real-Time Context Injection Pipeline

The GenAI assistant receives live stadium context through a **token-efficient compression pipeline**:

1. **Simulation Engine** generates realistic data every 5 seconds via sinusoidal congestion curves, random-walk queue models, and stochastic incident generation.
2. **Context Compressor** transforms the full `StadiumState` (potentially thousands of tokens) into a structured text summary (~300–500 tokens) tailored by role:
   - **Staff context**: Full operational view (all gates, busy concessions, transit, incidents, alerts)
   - **Fan context**: Localized view (nearby gates, nearby food, transit status — no sensitive data)
3. **System Prompt Injection**: Role-specific system instructions are injected via Gemini's `system_instruction` parameter (never concatenated with user input).
4. **User input is sanitized** and passed as a separate message, preventing prompt injection.

### State Management

- **Backend**: Single `StadiumSimulator` singleton manages all state in-memory with asyncio lock for thread safety. State snapshots are broadcast to WebSocket subscribers on every tick.
- **Frontend**: Custom `useStadiumState` hook wraps the WebSocket connection and exposes computed selectors (critical alerts, congestion summary) to avoid unnecessary re-renders.

---

## ⚙️ How the Solution Works

### Data Flow Blueprint

```
[Simulation Engine] ─────tick────→ [StadiumState Snapshot]
         │                                    │
         │                           ┌────────┴────────┐
         │                           ▼                  ▼
    [WebSocket Broadcast]     [REST API Endpoints]  [GenAI Pipeline]
         │                           │                  │
         ▼                           │            ┌─────┴─────┐
    [Dashboard UI]                   │            ▼           ▼
    (Real-time updates)              │     [Staff System   [Fan System
                                     │      Prompt]        Prompt]
                                     │            │           │
                                     │            ▼           ▼
                                     │     [Context Compressor]
                                     │            │
                                     │            ▼
                                     │     [Gemini API / Fallback Engine]
                                     │            │
                                     ▼            ▼
                              [Fan Widget]  [Staff Chat Panel]
```

### Live Event Trigger → Fan UI Example

1. **Tick 47**: Simulation engine computes Gate G congestion at 92% (critical)
2. **Alert Generated**: `OperationalAlert` created: "Gate G Congestion Critical"
3. **WebSocket Broadcast**: State snapshot pushed to all connected dashboards
4. **Staff Dashboard**: `AlertBanner` renders with pulsing animation; `GateMonitor` shows Gate G in red
5. **Fan queries**: "Which gate should I use?" from Section 180 (near Gate G)
6. **Context Injection**: Compressor includes Gate G=92%, Gate H=35%, Gate F=41%
7. **GenAI Response**: "Gate H (North-West) is your best option — only 35% full and a 3-minute walk from Section 180!"
8. **Fallback**: If Gemini API unavailable, the rule-based engine runs `recommend_gate(180, state)` and formats the top 3 recommendations.

---

## 📐 Assumptions Made

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| Stadium capacity | 82,500 | MetLife Stadium actual capacity |
| Entry gates | 8 (A–H), evenly distributed | Standard NFL/FIFA venue layout |
| Gate throughput | ~1,200 people/hour/gate | Industry standard for turnstile-based entry |
| Concession zones | 24, across 4 levels | Proportional to 82,500 capacity |
| Average walk time between adjacent gates | 3 minutes | Based on MetLife concourse circumference (~1km) |
| Maximum walk time (opposite gates) | 8 minutes | Half-circumference at moderate pace |
| Concession service time | ~24 seconds/person | Fast food service industry average |
| Simulation tick rate | 5 seconds | Balances UI responsiveness with compute efficiency |
| Match duration | Pre-Match (5min) → 1st Half (9min) → Halftime (3min) → 2nd Half (9min) → Post-Match (5min) | Compressed from real 90-min match for demo |
| Transit hubs | 6 (1 rail, 3 bus, 2 rideshare) | Based on actual MetLife infrastructure |
| Incident probability | ~3% per tick, modulated by phase | Realistic for 82K+ venue |
| Queue model | Random walk with demand-driven drift | Captures natural variability |
| Congestion model | Sinusoidal + Gaussian noise | Models natural crowd flow patterns |

---

## ✅ Evaluation Focus Areas

### 💎 Code Quality

| Criterion | Implementation |
|----------|----------------|
| **Architecture** | Clean layered architecture: Models → Services → Routes → Frontend. No circular dependencies. |
| **Separation of Concerns** | Services contain pure business logic (no HTTP, no I/O). Routes are thin controllers. Components are presentational. |
| **Naming Conventions** | Descriptive, semantic names: `recommend_gate()`, `compress_stadium_context()`, `ConcessionTracker`, `useStadiumState`. |
| **Modularity** | 24 files, each with a single responsibility. Components are reusable. Services are independently testable. |
| **Documentation** | Every module has a docstring explaining purpose, architecture, and design decisions. Functions have typed args/returns. |

### 🔒 Security

| Criterion | Implementation |
|----------|----------------|
| **RBAC** | JWT tokens with `role` claim. Staff tokens access all endpoints; fan tokens are restricted. |
| **Input Sanitization** | `sanitize_input()` strips XSS payloads, SQL injection patterns, null bytes, and encodes HTML entities. |
| **Prompt Injection Defense** | Multi-layer: 11 regex patterns detect injection attempts. System prompts are injected via API parameter, never concatenated. Output is scanned for system instruction leaks. |
| **Rate Limiting** | Sliding window per-IP: 60 req/min (staff), 30 req/min (fan). Prevents API abuse. |
| **Data Isolation** | Fan endpoints never expose incidents, raw alerts, or operational data. Context compressor filters by role. |
| **Audit Logging** | All API requests logged with method, path, IP, role, status, and processing time. |

### ⚡ Efficiency

| Criterion | Implementation |
|----------|----------------|
| **Context Compression** | `compress_stadium_context()` reduces full state (~5KB JSON) to ~500 tokens of structured text. Only notable data (busy concessions, congested gates) included. |
| **WebSocket Streaming** | Real-time updates pushed via WebSocket (no polling). Subscriber queues are bounded (maxsize=10) with oldest-drop on overflow. |
| **Computed Selectors** | `useStadiumState` hook computes `criticalAlerts` and `congestionSummary` to prevent recomputation in child components. |
| **Algorithm Efficiency** | Gate/concession routing uses O(n) scoring with pre-computed adjacency matrix. No expensive graph traversals. |
| **Lazy Initialization** | Gemini model is initialized once on first use, not on import. |
| **Memory Management** | Incidents capped at 20. Alerts regenerated each tick (no unbounded growth). Subscriber cleanup on disconnect. |

### 🧪 Testing

| Test File | Coverage |
|-----------|----------|
| `test_queue_router.py` | 20 tests: gate mapping, walk times, symmetry, recommendation scoring, concession routing, navigation, facilities |
| `test_transit_service.py` | 16 tests: delay classification, boundary values, departure estimation, recommendation sorting, summary generation |
| `test_security.py` | 20 tests: JWT creation/validation, RBAC hierarchy, XSS stripping, SQL injection, prompt injection patterns, rate limiting |
| `test_simulation.py` | 18 tests: initialization, tick progression, data range validation, phase transitions, congestion classification, determinism |
| `test_api.py` | 17 tests: system endpoints, operations API, fan API, RBAC enforcement, input validation, accessibility routes |
| **Total** | **91 executable tests** |

Run with:
```bash
cd backend && pip install -r requirements.txt && python -m pytest tests/ -v
```

### ♿ Accessibility (WCAG 2.1 AA)

| Criterion | Implementation |
|----------|----------------|
| **Semantic HTML** | All components use `<section>`, `<nav>`, `<main>`, `<article>`, `<header>` with proper hierarchy. Single `<h1>` per page. |
| **ARIA Attributes** | `role="region"`, `role="log"`, `role="progressbar"`, `role="alert"`, `role="switch"`, `aria-live="polite"/"assertive"`, `aria-label` on all interactive elements. |
| **Keyboard Navigation** | All interactive elements are focusable. `:focus-visible` styles on all elements. Skip-to-content link. Enter key sends chat messages. |
| **High Contrast Mode** | Toggle switch activates `[data-theme="high-contrast"]` CSS overrides: black backgrounds, white text, boosted accent colors — all meeting 4.5:1 contrast ratio. |
| **Screen Reader Support** | Chat messages in `aria-live` regions. Alert banner uses `aria-live="assertive"`. Gate congestion described in `aria-label` text. |
| **Color Independence** | Status is conveyed via text labels AND color (never color alone). Severity badges include text. |

---

## 📁 Project Structure

```
├── backend/
│   ├── __init__.py
│   ├── config.py                  # Configuration & stadium constants
│   ├── main.py                    # FastAPI application entry point
│   ├── requirements.txt           # Python dependencies
│   ├── models/
│   │   ├── __init__.py
│   │   └── stadium.py             # Pydantic data models
│   ├── simulation/
│   │   ├── __init__.py
│   │   └── engine.py              # Stadium simulation engine
│   ├── services/
│   │   ├── __init__.py
│   │   ├── genai_service.py       # GenAI orchestration layer
│   │   ├── queue_router.py        # Gate/concession routing algorithms
│   │   └── transit_service.py     # Transit analysis service
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── security.py            # RBAC, sanitization, rate limiting
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── operations.py          # Staff API endpoints
│   │   └── fan.py                 # Fan API endpoints
│   └── tests/
│       ├── __init__.py
│       ├── test_queue_router.py    # Queue routing unit tests
│       ├── test_transit_service.py # Transit service unit tests
│       ├── test_security.py       # Security validation tests
│       ├── test_simulation.py     # Simulation engine tests
│       └── test_api.py            # API integration tests
├── frontend/
│   ├── index.html                 # HTML entry point
│   ├── package.json               # Node.js dependencies
│   ├── vite.config.js             # Vite configuration
│   └── src/
│       ├── main.jsx               # React entry point
│       ├── App.jsx                # Root component with routing
│       ├── index.css              # Design system & global styles
│       ├── services/
│       │   └── api.js             # API service layer
│       ├── hooks/
│       │   ├── useWebSocket.js    # WebSocket hook
│       │   └── useStadiumState.js # State management hook
│       ├── components/
│       │   ├── dashboard/
│       │   │   ├── AlertBanner.jsx
│       │   │   ├── ConcessionTracker.jsx
│       │   │   ├── GateMonitor.jsx
│       │   │   ├── IncidentPanel.jsx
│       │   │   ├── StaffAssistant.jsx
│       │   │   └── TransitStatus.jsx
│       │   └── fan/
│       │       └── FanChatWidget.jsx
│       └── pages/
│           ├── Dashboard.jsx      # Staff operations page
│           └── FanView.jsx        # Fan experience page
└── README.md                      # This file
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+** with pip
- **Node.js 18+** with npm
- (Optional) **Google Gemini API key** for GenAI features

### Backend Setup

```bash
# Navigate to backend
cd backend

# Install Python dependencies
pip install -r requirements.txt

# (Optional) Set Gemini API key for AI features
# Without this, the system uses rule-based fallback responses
export GEMINI_API_KEY="your-api-key-here"   # macOS/Linux
set GEMINI_API_KEY=your-api-key-here        # Windows

# Start the server
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# The API is now running at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# The app is now running at http://localhost:5173
```

### Running Tests

```bash
# Backend tests (from project root)
cd backend
python -m pytest tests/ -v

# Frontend build validation
cd frontend
npm run build
```

---

## 📡 API Reference

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API info and available endpoints |
| GET | `/health` | Health check |
| GET | `/dev/token/{role}` | Generate dev auth token |
| WS | `/ws/live` | Real-time stadium state feed |

### Operations (Staff)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ops/stadium-state` | Full stadium snapshot |
| GET | `/api/ops/alerts` | Active alerts |
| GET | `/api/ops/incidents` | Active incidents |
| GET | `/api/ops/transit-summary` | Transit operations summary |
| POST | `/api/ops/assistant` | Query AI operations assistant |

### Fan Experience
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/fan/assistant` | Query AI fan assistant |
| GET | `/api/fan/concessions?section=120` | Concession recommendations |
| GET | `/api/fan/gates?section=120` | Gate recommendations |
| POST | `/api/fan/navigation` | Step-by-step wayfinding |
| GET | `/api/fan/transit?section=120` | Transit recommendations |

---

## 📄 License

Built for the FIFA World Cup 2026 Smart Stadiums & Tournament Operations challenge.
#   S m a r t - S t a d i u m s - T o u r n a m e n t - O p e r a t i o n s  
 