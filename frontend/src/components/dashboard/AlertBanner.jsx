/**
 * AlertBanner Component
 * ======================
 * Animated top-bar alert for critical operational events.
 * Only renders when there are high/critical severity alerts.
 */

import React from 'react';

export default function AlertBanner({ alerts = [] }) {
  // Only show banner for high/critical alerts
  const critical = alerts.filter(
    (a) => a.severity === 'high' || a.severity === 'critical'
  );

  if (critical.length === 0) return null;

  const topAlert = critical[0];

  return (
    <div
      className="alert-banner"
      role="alert"
      aria-live="assertive"
      aria-label={`Critical alert: ${topAlert.title}`}
    >
      <span className="alert-banner__icon" aria-hidden="true">⚠️</span>
      <div className="alert-banner__content">
        <div className="alert-banner__title">{topAlert.title}</div>
        <div className="alert-banner__message">{topAlert.message}</div>
      </div>
      {critical.length > 1 && (
        <span
          className="alert-banner__count"
          aria-label={`${critical.length} total critical alerts`}
        >
          +{critical.length - 1}
        </span>
      )}
    </div>
  );
}
