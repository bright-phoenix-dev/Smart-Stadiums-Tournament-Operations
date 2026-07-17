/**
 * MatchScoreboard Component
 * ==========================
 * Premium match header with team flags, live score,
 * match phase indicator, and animated phase dot.
 */

import React from 'react';

const PHASE_COLORS = {
  'Pre-Match': 'var(--color-accent-teal)',
  '1st Half': 'var(--color-accent-green)',
  'Halftime': 'var(--color-accent-gold)',
  '2nd Half': 'var(--color-accent-green)',
  'Post-Match': 'var(--color-accent-purple)',
};

export default function MatchScoreboard({ state }) {
  if (!state) return null;

  const phaseColor = PHASE_COLORS[state.match_phase] || 'var(--color-accent-teal)';

  return (
    <div
      className="glass-card"
      role="banner"
      aria-label="Match scoreboard"
      style={{
        marginBottom: 'var(--space-6)',
        padding: 'var(--space-6) var(--space-8)',
        background: 'linear-gradient(135deg, rgba(0, 180, 216, 0.08), rgba(167, 139, 250, 0.05), rgba(255, 215, 0, 0.05))',
        borderImage: 'linear-gradient(135deg, rgba(0, 180, 216, 0.3), rgba(255, 215, 0, 0.2)) 1',
      }}
    >
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 'var(--space-8)',
        flexWrap: 'wrap',
      }}>
        {/* Team A */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-4)',
          flex: '1',
          justifyContent: 'flex-end',
          minWidth: '120px',
        }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              fontSize: 'var(--text-xl)',
            }}>
              Team A
            </div>
            <div style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--color-text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}>
              Group Stage
            </div>
          </div>
          <span style={{ fontSize: '2rem' }} aria-hidden="true">🏳️</span>
        </div>

        {/* Score */}
        <div style={{
          textAlign: 'center',
          minWidth: '140px',
        }}>
          <div style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 800,
            fontSize: '2.5rem',
            letterSpacing: '0.08em',
            background: 'linear-gradient(135deg, var(--color-accent-teal), var(--color-accent-gold))',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}>
            0 — 0
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 'var(--space-2)',
            marginTop: 'var(--space-1)',
          }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: phaseColor,
                display: 'inline-block',
                animation: state.match_phase !== 'Post-Match' ? 'pulse-dot 2s ease-in-out infinite' : 'none',
              }}
              aria-hidden="true"
            />
            <span style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 600,
              fontSize: 'var(--text-sm)',
              color: phaseColor,
            }}>
              {state.match_phase} • {state.match_minute}'
            </span>
          </div>
        </div>

        {/* Team B */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-4)',
          flex: '1',
          justifyContent: 'flex-start',
          minWidth: '120px',
        }}>
          <span style={{ fontSize: '2rem' }} aria-hidden="true">🏳️</span>
          <div>
            <div style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              fontSize: 'var(--text-xl)',
            }}>
              Team B
            </div>
            <div style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--color-text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}>
              Group Stage
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
