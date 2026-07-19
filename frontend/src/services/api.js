/**
 * API Service Layer
 * ==================
 * Centralized API communication with error handling, request
 * interceptors, and typed response wrappers.
 *
 * All fetch calls go through this module for consistent behavior.
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

// Circuit Breaker: stops cascading failures when the backend is unhealthy
const _circuitBreaker = {
  failures: 0,
  isOpen: false,
  nextTry: 0,
  THRESHOLD: 3,
  COOLDOWN_MS: 5000,
};

/**
 * Generates a SHA-256 payload checksum for request integrity verification.
 * Attached as the X-Device-Signature header on mutating requests.
 * Note: This is a checksum, not a signed HMAC — it detects accidental
 * corruption, not active adversarial tampering.
 * @param {string} body - JSON-serialized request body
 * @returns {Promise<string>} Hex-encoded SHA-256 hash
 */
async function signPayload(body) {
  if (!body) return '';
  const msgUint8 = new TextEncoder().encode(body);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgUint8);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Category-Theoretic Monad: Either<Error, Data>
 * Functional error propagation wrapper. Forces callers to handle
 * both success and failure paths explicitly via .unwrap().
 */
class Either {
  constructor(error, data) {
    this.error = error;
    this.data = data;
  }
  static Left(error) { return new Either(error, null); }
  static Right(data) { return new Either(null, data); }
  isLeft() { return this.error !== null; }
  unwrap() { if (this.isLeft()) throw this.error; return this.data; }
}

/**
 * Generic fetch wrapper with circuit breaker, error handling, and JSON parsing.
 * Returns an Either monad — Right on success, Left on any error.
 *
 * @param {string} endpoint - API path (e.g., "/api/ops/stadium-state")
 * @param {RequestInit} [options={}] - Fetch options
 * @returns {Promise<Either<Error, any>>} Parsed JSON response
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;

  if (_circuitBreaker.isOpen) {
    if (Date.now() > _circuitBreaker.nextTry) {
      // Half-open: allow one canary request to test recovery
      _circuitBreaker.isOpen = false;
    } else {
      throw new Error(`Circuit breaker open: connection blocked to protect upstream servers. Retrying in ${Math.ceil((_circuitBreaker.nextTry - Date.now()) / 1000)}s.`);
    }
  }

  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

  // Attach SHA-256 payload checksum on mutating requests
  if (options.body && options.method && options.method !== 'GET') {
    defaultHeaders['X-Device-Signature'] = await signPayload(options.body);
  }

  // Merge headers
  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      _circuitBreaker.failures++;
      if (_circuitBreaker.failures >= _circuitBreaker.THRESHOLD) {
        _circuitBreaker.isOpen = true;
        _circuitBreaker.nextTry = Date.now() + _circuitBreaker.COOLDOWN_MS;
      }
      const isJson = response.headers.get('content-type')?.includes('application/json');
      const errorData = isJson ? await response.json().catch(() => ({})) : {};
      throw new Error(
        errorData.detail || `API error: ${response.status} ${response.statusText}`
      );
    }

    // Success resets the circuit
    _circuitBreaker.failures = 0;
    _circuitBreaker.isOpen = false;

    // Validate Content-Type before parsing
    const isSuccessJson = response.headers.get('content-type')?.includes('application/json');
    if (!isSuccessJson) {
      throw new Error(`Invalid response format from server (expected JSON, got ${response.headers.get('content-type')}).`);
    }

    const data = await response.json();
    return Either.Right(data);
  } catch (error) {
    _circuitBreaker.failures++;
    if (_circuitBreaker.failures >= _circuitBreaker.THRESHOLD) {
      _circuitBreaker.isOpen = true;
      _circuitBreaker.nextTry = Date.now() + _circuitBreaker.COOLDOWN_MS;
      console.warn('Circuit breaker opened after repeated API failures.');
    }
    return Either.Left(error);
  }
}

// ---------------------------------------------------------------------------
// Typed Endpoints Returning Formal Monads
// ---------------------------------------------------------------------------

/** Fetch the full stadium state snapshot. */
export async function getStadiumState() {
  return request('/api/ops/stadium-state');
}

/** Fetch active operational alerts. */
export async function getAlerts() {
  return request('/api/ops/alerts');
}

/** Fetch active incidents. */
export async function getIncidents() {
  return request('/api/ops/incidents');
}

/** Fetch transit operations summary. */
export async function getTransitSummary() {
  return request('/api/ops/transit-summary');
}

/**
 * Send a query to the staff AI assistant.
 * @param {string} message - Staff question
 * @param {string|null} conversationId - Thread ID
 */
export async function queryStaffAssistant(message, conversationId = null) {
  return request('/api/ops/assistant', {
    method: 'POST',
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
    }),
  });
}

/* ----------------------------------------------------------------
   Fan API
   ---------------------------------------------------------------- */

/**
 * Send a query to the fan AI assistant.
 * @param {string} message - Fan question
 * @param {object} fanProfile - Fan profile (seat_section, language, etc.)
 * @param {string|null} conversationId - Thread ID
 */
export async function queryFanAssistant(message, fanProfile = null, conversationId = null) {
  return request('/api/fan/assistant', {
    method: 'POST',
    body: JSON.stringify({
      message,
      fan_profile: fanProfile,
      conversation_id: conversationId,
    }),
  });
}

/**
 * Get concession recommendations for a section.
 * @param {number} section - Stadium section number
 * @param {string|null} foodType - Optional type filter
 */
export async function getConcessions(section, foodType = null) {
  let url = `/api/fan/concessions?section=${section}`;
  if (foodType) url += `&food_type=${encodeURIComponent(foodType)}`;
  return request(url);
}

/**
 * Get gate recommendations for a section.
 * @param {number} section - Stadium section number
 */
export async function getGates(section) {
  return request(`/api/fan/gates?section=${section}`);
}

/**
 * Get navigation directions.
 * @param {number} fromSection - Starting section
 * @param {string} destination - Destination description
 * @param {boolean} accessibilityNeeds - Require accessible route
 */
export async function getNavigation(fromSection, destination, accessibilityNeeds = false) {
  return request('/api/fan/navigation', {
    method: 'POST',
    body: JSON.stringify({
      from_section: fromSection,
      destination,
      accessibility_needs: accessibilityNeeds,
    }),
  });
}

/**
 * Get transit recommendations.
 * @param {number} section - Stadium section number
 * @param {string|null} transitType - Optional filter ("rail", "bus", "rideshare")
 */
export async function getTransit(section, transitType = null) {
  let url = `/api/fan/transit?section=${section}`;
  if (transitType) url += `&transit_type=${encodeURIComponent(transitType)}`;
  return request(url);
}

/* ----------------------------------------------------------------
   System API
   ---------------------------------------------------------------- */

/** Fetch API health status. */
export async function getHealth() {
  return request('/health');
}

/**
 * Create a WebSocket connection for real-time stadium updates.
 * @returns {WebSocket}
 */
export function createLiveSocket() {
  const wsBase = API_BASE.replace('http', 'ws');
  return new WebSocket(`${wsBase}/ws/live`);
}
