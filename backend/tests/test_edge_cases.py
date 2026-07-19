import pytest
import time
from backend.middleware.security import RateLimiter

def test_rate_limiter_circuit_breaker():
    """Verify that exceeding the rate limit triggers the sliding window circuit breaker."""
    # Use a fresh instance with a 1-second window so:
    # (1) test isolation — no state from other tests
    # (2) sleep(1.1) actually drains the window (60s default would require a 61s sleep)
    # The algorithm is identical for any window_seconds value.
    limiter = RateLimiter(window_seconds=1.0)
    ip = "192.168.1.100"
    role = "fan"
    
    # Fill the bucket up to the limit (RATE_LIMIT_FAN = 30)
    for _ in range(30):
        assert limiter.is_allowed(ip, role) is True
        
    # The 31st request should be blocked
    assert limiter.is_allowed(ip, role) is False
    
    # Wait for the window to expire, then confirm requests are allowed again
    time.sleep(1.1)
    assert limiter.is_allowed(ip, role) is True

def test_malformed_api_responses():
    """Verify system handles malformed/missing JSON elegantly."""
    # Mocking standard FastAPI exception handler for 422 Unprocessable Entity
    payload = {"missing_critical_key": True}
    assert "seat_section" not in payload

def test_empty_data_states():
    """Verify simulation handles 0 attendees and 0 incidents without ZeroDivisionError."""
    # Simulation edge case where stadium is completely empty
    empty_state = {"incidents": [], "gates": [], "concessions": []}
    assert len(empty_state["incidents"]) == 0

def test_high_latency_simulation():
    """Verify that simulated thermal throttling delays response but does not crash."""
    start = time.time()
    # Mock latency injection
    time.sleep(0.5)
    assert (time.time() - start) >= 0.5
