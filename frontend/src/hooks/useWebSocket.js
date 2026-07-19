/**
 * useWebSocket Hook
 * ==================
 * Manages a persistent WebSocket connection to the simulator's live feed
 * with automatic reconnection on disconnect.
 *
 * @param {function} onMessage - Callback invoked with parsed JSON state on each tick
 * @returns {{ isConnected: boolean, error: string|null, reconnect: function }}
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const WS_BASE = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace('http', 'ws')
  : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;

export function useWebSocket(onMessage) {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const mountedRef = useRef(true);

  // Stable session ID persisted across reconnects (survives page refreshes within the tab)
  const sessionId = useMemo(() => {
    let id = sessionStorage.getItem('stadium_ws_session');
    if (!id) {
      id = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
      sessionStorage.setItem('stadium_ws_session', id);
    }
    return id;
  }, []);

  const connect = useCallback(() => {
    // Close any existing connection before opening a new one
    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      const ws = new WebSocket(`${WS_BASE}/ws/live?session_id=${sessionId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (mountedRef.current) {
          setIsConnected(true);
          setError(null);
        }
      };

      ws.onmessage = (event) => {
        try {
          // Guard: only process non-empty string payloads
          if (typeof event.data !== 'string' || event.data.length === 0) {
            return;
          }
          const data = JSON.parse(event.data);
          if (!data || typeof data !== 'object') {
            return;
          }
          onMessage?.(data);
        } catch (_parseError) {
          console.error('WebSocket message parse error:', _parseError.message);
        }
      };

      ws.onerror = () => {
        if (mountedRef.current) {
          setError('WebSocket connection error');
        }
      };

      ws.onclose = () => {
        if (mountedRef.current) {
          setIsConnected(false);
          // Auto-reconnect after 3 seconds
          reconnectTimerRef.current = setTimeout(() => {
            if (mountedRef.current) connect();
          }, 3000);
        }
      };
    } catch (err) {
      if (mountedRef.current) {
        setError(err.message);
      }
    }
  // sessionId is stable (useMemo with [] deps) — safe to omit from deps array
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onMessage]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const reconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
    }
    connect();
  }, [connect]);

  return { isConnected, error, reconnect };
}
