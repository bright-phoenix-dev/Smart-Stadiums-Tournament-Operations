/**
 * ConcessionTracker Component
 * ============================
 * Grid display of concession zones with queue status,
 * wait times, and severity-coded left borders.
 */

import React from 'react';

function getQueueClass(queue, maxQueue) {
  const ratio = queue / maxQueue;
  if (ratio < 0.3) return 'low';
  if (ratio < 0.6) return 'medium';
  if (ratio < 0.9) return 'high';
  return 'overflow';
}

const ConcessionTracker = React.memo(function ConcessionTracker({ concessions = [] }) {
  if (!concessions.length) {
    return (
      <section className="glass-card" role="region" aria-label="Concession Queue Tracker">
        <div className="glass-card__header">
          <h2 className="glass-card__title">🍔 Concessions</h2>
        </div>
        <div className="empty-state">
          <div className="empty-state__icon">🍿</div>
          <p>Waiting for concession data...</p>
        </div>
      </section>
    );
  }

  // Sort by queue length descending (busiest first)
  const sorted = [...concessions].sort((a, b) => b.current_queue - a.current_queue);

  return (
    <section className="glass-card" role="region" aria-label="Concession Queue Tracker">
      <div className="glass-card__header">
        <h2 className="glass-card__title">🍔 Concessions</h2>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
          {concessions.filter((c) => c.current_queue > c.max_queue * 0.8).length} busy
        </span>
      </div>

      <div className="concession-grid" role="list" aria-label="Concession zones">
        {sorted.map((cz) => {
          const queueClass = getQueueClass(cz.current_queue, cz.max_queue);
          return (
            <div
              key={cz.zone_id}
              className={`concession-item concession-item--${queueClass}`}
              role="listitem"
              aria-label={`${cz.name}, ${cz.zone_type}, queue ${cz.current_queue} of ${cz.max_queue}, wait ${cz.wait_minutes} minutes`}
            >
              <div className="concession-item__name">{cz.name}</div>
              <div className="concession-item__type">{cz.zone_type} • Level {cz.level}</div>
              <div className="concession-item__stats">
                <span className="concession-item__queue">
                  {cz.current_queue}/{cz.max_queue}
                </span>
                <span className="concession-item__wait">
                  ~{Math.round(cz.wait_minutes)}min
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
});

export default ConcessionTracker;
