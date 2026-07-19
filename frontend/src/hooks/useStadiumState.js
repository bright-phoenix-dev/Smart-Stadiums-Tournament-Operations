/**
 * useStadiumState Hook
 * =====================
 * Central state manager for live stadium data.
 * Wraps the WebSocket hook and exposes memoized computed selectors
 * for dashboard components to consume efficiently.
 *
 * Performance: All derived values (criticalAlerts, congestionSummary)
 * are memoized with useMemo to prevent unnecessary re-computation
 * when unrelated state changes occur.
 */

import { useCallback, useMemo, useRef, useState, useEffect } from 'react';
import { useWebSocket } from './useWebSocket';

/**
 * @returns {{
 *   state: object|null,
 *   isConnected: boolean,
 *   error: string|null,
 *   criticalAlerts: array,
 *   congestionSummary: object,
 *   lastUpdate: Date|null
 * }}
 */
export function useStadiumState() {
  const [state, setState] = useState(() => {
    try {
      const cached = localStorage.getItem('stadium_state_cache');
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  });
  const [lastUpdate, setLastUpdate] = useState(null);
  const [congestionSummary, setCongestionSummary] = useState({ avgCongestion: 0, criticalGates: 0, heavyGates: 0, clearGates: 0 });
  const stateRef = useRef(null);
  const lastUpdateRef = useRef(0);
  const workerRef = useRef(null);

  // Initialize Web Worker for off-thread congestion computation
  useEffect(() => {
    workerRef.current = new Worker(new URL('../workers/telemetryWorker.js', import.meta.url));
    workerRef.current.onmessage = (e) => {
      setCongestionSummary(e.data);
    };
    return () => {
      workerRef.current?.terminate();
    };
  }, []);

  /** Stable callback ref — won't cause WebSocket reconnects on re-render */
  const handleMessage = useCallback((stadiumAnalytics) => {
    // Out-of-order packet guard: discard packets older than the last processed one
    const packetTime = new Date(stadiumAnalytics.timestamp).getTime();

    if (packetTime <= lastUpdateRef.current) {
      return;
    }

    lastUpdateRef.current = packetTime;

    // Debounce high-frequency updates: only re-render if packet is >2s newer than current state
    const shouldUpdate = !stateRef.current || Math.abs((stateRef.current.timestamp || 0) - packetTime) > 2000;
    if (!shouldUpdate) return;

    // Merge incoming packet with previous state (last-write-wins for all fields except timestamp)
    setState(prevState => {
      if (!prevState) return stadiumAnalytics;
      return {
        ...prevState,
        ...stadiumAnalytics,
        timestamp: Math.max(prevState.timestamp || 0, stadiumAnalytics.timestamp || 0),
      };
    });

    setLastUpdate(new Date(packetTime));

    // Offload gate congestion math to background Web Worker thread
    if (workerRef.current && stadiumAnalytics?.gates) {
      workerRef.current.postMessage({ gates: stadiumAnalytics.gates });
    }

    try {
      localStorage.setItem('stadium_state_cache', JSON.stringify(stadiumAnalytics));
    } catch {
      // Ignore storage quota errors
    }
  }, []);

  const { isConnected, error, reconnect } = useWebSocket(handleMessage);

  /** Memoized: critical alerts (high + critical severity) */
  const criticalAlerts = useMemo(() => {
    if (!state?.alerts) return [];
    return state.alerts.filter(
      (a) => a.severity === 'high' || a.severity === 'critical'
    );
  }, [state?.alerts]);

  return {
    state,
    isConnected,
    error,
    reconnect,
    criticalAlerts,
    congestionSummary,
    lastUpdate,
  };
}
