/**
 * GateMonitor Component
 * ======================
 * Displays real-time gate congestion status as a grid of
 * color-coded progress bars with percentage indicators.
 *
 * Accessibility: Each gate has an aria-label describing its
 * congestion level for screen readers.
 */

import React from 'react';

/** Map congestion level to CSS modifier class */
function getCongestionClass(level) {
  const map = {
    clear: 'clear',
    moderate: 'moderate',
    heavy: 'heavy',
    critical: 'critical',
  };
  return map[level] || 'clear';
}

/** Map congestion percentage to status color */
function getCongestionColor(pct) {
  if (pct <= 30) return 'var(--color-status-clear)';
  if (pct <= 60) return 'var(--color-status-moderate)';
  if (pct <= 85) return 'var(--color-status-heavy)';
  return 'var(--color-status-critical)';
}

const GateMonitor = React.memo(function GateMonitor({ gates = [] }) {
  if (!gates.length) {
    return (
      <div className="glass-card" role="region" aria-label="Gate Status Monitor">
        <div className="glass-card__header">
          <h2 className="glass-card__title">🚪 Gate Status</h2>
        </div>
        <div className="empty-state">
          <div className="empty-state__icon">📡</div>
          <p>Waiting for gate data...</p>
        </div>
      </div>
    );
  }

  return (
    <section className="glass-card" role="region" aria-label="Gate Status Monitor">
      <div className="glass-card__header">
        <h2 className="glass-card__title">🚪 Gate Status</h2>
        <span className="status-badge status-badge--clear">
          <span className="status-badge__dot" aria-hidden="true"></span>
          Live
        </span>
      </div>

      <div className="gate-grid" role="list">
        {gates.map((gate) => {
          const levelClass = getCongestionClass(gate.congestion_level);
          return (
            <div
              key={gate.gate_id}
              className="gate-item"
              role="listitem"
              aria-label={`Gate ${gate.gate_id}, ${gate.zone} zone, ${Math.round(gate.congestion_pct)}% congestion, status ${gate.congestion_level}`}
            >
              <div className="gate-item__name">Gate {gate.gate_id}</div>
              <div className="gate-item__zone">{gate.zone}</div>

              {/* Congestion bar */}
              <div
                className="gate-bar"
                role="progressbar"
                aria-valuenow={Math.min(100, Math.round(gate.congestion_pct))}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`Congestion: ${Math.round(gate.congestion_pct)}%`}
              >
                <div
                  className={`gate-bar__fill gate-bar__fill--${levelClass}`}
                  style={{ '--progress': Math.min(1, Math.max(0, gate.congestion_pct / 100)) }}
                />
              </div>

              <div className="gate-item__pct" style={{ color: getCongestionColor(gate.congestion_pct) }}>
                {Math.round(gate.congestion_pct)}%
              </div>
              <div className="gate-item__label">{gate.congestion_level}</div>
            </div>
          );
        })}
      </div>
    </section>
  );
});

export default GateMonitor;
