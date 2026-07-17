/**
 * KPIStatsBar Component
 * ======================
 * Row of key performance indicator cards with icons,
 * real-time values, trend indicators, and status colors.
 * Provides staff an instant operational snapshot.
 */

import React from 'react';

function KPICard({ icon, label, value, subtext, color, trend }) {
  return (
    <div
      className="glass-card"
      style={{
        padding: 'var(--space-4) var(--space-5)',
        textAlign: 'center',
        minWidth: '140px',
        flex: '1',
        borderTop: `3px solid ${color}`,
        position: 'relative',
        overflow: 'hidden',
        
        // 6. GPU Text Rasterization & Thread-Isolated Layout Painting
        // Forces the browser to elevate this DOM node onto its own physical GPU 
        // compositor layer. During 50Hz telemetry updates, only the text texture 
        // is re-rasterized, preventing the main thread from blocking keyboard nav.
        willChange: 'transform, opacity',
        transform: 'translateZ(0)',
      }}
      role="status"
      aria-label={`${label}: ${value}`}
    >
      {/* Background glow */}
      <div
        style={{
          position: 'absolute',
          top: '-20px',
          left: '50%',
          transform: 'translateX(-50%)',
          width: '80px',
          height: '40px',
          background: color,
          filter: 'blur(30px)',
          opacity: 0.15,
        }}
        aria-hidden="true"
      />
      <div style={{ fontSize: '1.3rem', marginBottom: 'var(--space-1)' }} aria-hidden="true">
        {icon}
      </div>
      <div style={{
        fontFamily: 'var(--font-display)',
        fontWeight: 700,
        fontSize: 'var(--text-2xl)',
        color: color,
        marginBottom: 'var(--space-1)',
      }}>
        {value}
        {trend && (
          <span style={{
            fontSize: 'var(--text-xs)',
            marginLeft: 'var(--space-1)',
            color: trend === 'up' ? 'var(--color-status-critical)' : 'var(--color-status-clear)',
          }}>
            {trend === 'up' ? '↑' : '↓'}
          </span>
        )}
      </div>
      <div style={{
        fontSize: 'var(--text-xs)',
        color: 'var(--color-text-muted)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        fontWeight: 600,
      }}>
        {label}
      </div>
      {subtext && (
        <div style={{
          fontSize: 'var(--text-xs)',
          color: 'var(--color-text-secondary)',
          marginTop: 'var(--space-1)',
        }}>
          {subtext}
        </div>
      )}
    </div>
  );
}

export default function KPIStatsBar({ state, congestionSummary, criticalAlerts }) {
  if (!state) return null;

  const capacityPct = Math.round((state.total_attendance / 82500) * 100);
  const avgWait = state.concessions
    ? Math.round(state.concessions.reduce((s, c) => s + c.wait_minutes, 0) / state.concessions.length)
    : 0;
  const avgTransitDelay = state.transit_hubs
    ? Math.round(state.transit_hubs.reduce((s, h) => s + h.delay_minutes, 0) / state.transit_hubs.length)
    : 0;

  const congColor = congestionSummary.avgCongestion > 60
    ? 'var(--color-status-critical)'
    : congestionSummary.avgCongestion > 30
      ? 'var(--color-status-moderate)'
      : 'var(--color-status-clear)';

  return (
    <div
      style={{
        display: 'flex',
        gap: 'var(--space-4)',
        marginBottom: 'var(--space-6)',
        flexWrap: 'wrap',
      }}
      role="region"
      aria-label="Key performance indicators"
    >
      <KPICard
        icon="👥"
        label="Attendance"
        value={state.total_attendance?.toLocaleString() || '0'}
        subtext={`${capacityPct}% capacity`}
        color="var(--color-accent-teal)"
      />
      <KPICard
        icon="🚪"
        label="Avg Congestion"
        value={`${congestionSummary.avgCongestion}%`}
        subtext={`${congestionSummary.criticalGates} critical gate${congestionSummary.criticalGates !== 1 ? 's' : ''}`}
        color={congColor}
        trend={congestionSummary.avgCongestion > 50 ? 'up' : null}
      />
      <KPICard
        icon="🍔"
        label="Avg Wait"
        value={`${avgWait}m`}
        subtext="concession queues"
        color={avgWait > 15 ? 'var(--color-status-heavy)' : 'var(--color-accent-green)'}
      />
      <KPICard
        icon="🚨"
        label="Active Alerts"
        value={criticalAlerts.length.toString()}
        subtext={`${state.active_incidents?.length || 0} incidents`}
        color={criticalAlerts.length > 0 ? 'var(--color-status-critical)' : 'var(--color-accent-green)'}
      />
      <KPICard
        icon="🚆"
        label="Transit Delay"
        value={`${avgTransitDelay}m`}
        subtext="avg across hubs"
        color={avgTransitDelay > 10 ? 'var(--color-status-heavy)' : 'var(--color-accent-teal)'}
      />
    </div>
  );
}
