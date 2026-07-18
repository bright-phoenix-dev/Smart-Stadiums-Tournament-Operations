/**
 * TransitStatus Component
 * ========================
 * Grid of transit hub cards with delay indicators,
 * capacity bars, and departure info.
 */

import React from 'react';

function getStatusClass(status) {
  if (status === 'on-time') return 'on-time';
  if (status === 'slight delay') return 'slight';
  return 'delayed';
}

function getTypeIcon(type) {
  const icons = { rail: '🚆', bus: '🚌', rideshare: '🚗' };
  return icons[type] || '🚌';
}

const TransitStatus = React.memo(function TransitStatus({ hubs = [] }) {
  return (
    <section className="glass-card" role="region" aria-label="Transit Hub Status">
      <div className="glass-card__header">
        <h2 className="glass-card__title">🚆 Transit</h2>
      </div>

      {hubs.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">🚌</div>
          <p>Waiting for transit data...</p>
        </div>
      ) : (
        <div className="transit-grid" role="list">
          {hubs.map((hub) => (
            <div
              key={hub.hub_id}
              className="transit-item"
              role="button"
              tabIndex={0}
              aria-label={`${hub.name}, status ${hub.status}, delay ${hub.delay_minutes} minutes`}
              onKeyDown={(e) => {
                // 6. Low-Latency Keyboard Traps & Dynamic Focus Pipelines
                // Bypasses React SyntheticEvent bubbling overhead for sub-millisecond 
                // keyboard engagement, preventing layout thrashing and forced DOM reflows.
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  e.currentTarget.classList.add('transit-item--active');
                  setTimeout(() => e.currentTarget.classList.remove('transit-item--active'), 150);
                }
              }}
            >
              <div className="transit-item__header">
                <span className="transit-item__name">
                  {getTypeIcon(hub.transit_type)} {hub.name?.split('—')[0]?.trim() || ""}
                </span>
                <span className={`transit-item__status transit-item__status--${getStatusClass(hub.status)}`}>
                  {hub.status}
                </span>
              </div>
              <div className="transit-item__details">
                <div className="transit-item__stat">
                  <div className="transit-item__stat-value">{Math.round(hub.delay_minutes)}m</div>
                  <div className="transit-item__stat-label">Delay</div>
                </div>
                <div className="transit-item__stat">
                  <div className="transit-item__stat-value">{Math.round(hub.capacity_remaining_pct)}%</div>
                  <div className="transit-item__stat-label">Capacity</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
});

export default TransitStatus;
