/**
 * Telemetry Parsing Web Worker
 * ============================
 * Offloads gate congestion aggregation to a background thread so the
 * main UI thread stays responsive during high-frequency telemetry updates.
 *
 * Receives: { gates: GateState[] }
 * Sends:    { avgCongestion, criticalGates, heavyGates, clearGates }
 */

self.onmessage = function (event) {
  // Validate payload structure before processing
  if (!event.data || !Array.isArray(event.data.gates)) {
    return;
  }

  const gates = event.data.gates;
  const len = gates.length;

  if (len === 0) {
    self.postMessage({
      avgCongestion: 0,
      criticalGates: 0,
      heavyGates: 0,
      clearGates: 0,
    });
    return;
  }

  let totalCongestion = 0;
  let criticalGates = 0;
  let heavyGates = 0;
  let clearGates = 0;

  for (let i = 0; i < len; i++) {
    const pct = gates[i].congestion_pct;
    totalCongestion += pct;

    if (pct > 85) {
      criticalGates++;
    } else if (pct > 60) {
      heavyGates++;
    } else if (pct <= 30) {
      clearGates++;
    }
  }

  self.postMessage({
    avgCongestion: Math.round(totalCongestion / len),
    criticalGates,
    heavyGates,
    clearGates,
  });
};
