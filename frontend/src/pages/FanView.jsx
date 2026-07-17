/**
 * FanView Page — Fan Experience Interface
 * =========================================
 * Mobile-first page with section picker, language selector,
 * and the AI-powered fan chat widget.
 */

import React, { useState } from 'react';
import FanChatWidget from '../components/fan/FanChatWidget';
import { LANGUAGES } from '../utils/constants';

export default function FanView() {
  const [section, setSection] = useState(120);
  const [language, setLanguage] = useState('en');
  const [isSetup, setIsSetup] = useState(false);

  const handleStart = (e) => {
    e.preventDefault();
    setIsSetup(true);
  };

  return (
    <main id="main-content" className="fan-layout" role="main" aria-label="Fan Match Day Assistant">
      <h1 style={{ position: 'absolute', left: '-10000px' }}>
        Fan Match Day Assistant — MetLife Stadium
      </h1>

      {/* Header */}
      <div className="fan-header">
        <div className="fan-header__emoji" aria-hidden="true">⚽</div>
        <div className="fan-header__title">Match Day Assistant</div>
        <div className="fan-header__subtitle">
          FIFA World Cup 2026 — MetLife Stadium
        </div>
      </div>

      {!isSetup ? (
        /* Setup Form */
        <form className="fan-setup" onSubmit={handleStart} aria-label="Fan setup form">
          <div className="glass-card">
            <div className="glass-card__header">
              <h2 className="glass-card__title">📍 Your Location</h2>
            </div>

            <div className="fan-setup__row">
              <div style={{ flex: 1 }}>
                <label
                  htmlFor="section-input"
                  style={{
                    display: 'block',
                    fontSize: 'var(--text-sm)',
                    color: 'var(--color-text-secondary)',
                    marginBottom: 'var(--space-2)',
                  }}
                >
                  Section Number
                </label>
                <input
                  id="section-input"
                  className="fan-setup__input"
                  type="number"
                  min={100}
                  max={199}
                  value={section}
                  onChange={(e) => setSection(Number(e.target.value))}
                  aria-label="Stadium section number, 100 to 199"
                  required
                />
              </div>
            </div>

            <div style={{ marginTop: 'var(--space-3)' }}>
              <label
                htmlFor="language-select"
                style={{
                  display: 'block',
                  fontSize: 'var(--text-sm)',
                  color: 'var(--color-text-secondary)',
                  marginBottom: 'var(--space-2)',
                }}
              >
                Language Preference
              </label>
              <select
                id="language-select"
                className="fan-setup__select"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                aria-label="Select your preferred language"
                style={{ width: '100%' }}
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.flag} {lang.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              className="btn btn--primary btn--lg"
              style={{ width: '100%', marginTop: 'var(--space-4)' }}
            >
              🏟️ Start My Match Day
            </button>
          </div>
        </form>
      ) : (
        /* Chat Interface */
        <>
          {/* Section indicator */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 'var(--space-4)',
              padding: 'var(--space-2) var(--space-4)',
              background: 'var(--color-bg-card)',
              borderRadius: 'var(--radius-full)',
              border: '1px solid var(--color-border)',
              fontSize: 'var(--text-sm)',
            }}
          >
            <span>
              📍 Section {section} •{' '}
              {LANGUAGES.find((l) => l.code === language)?.flag}{' '}
              {LANGUAGES.find((l) => l.code === language)?.name}
            </span>
            <button
              className="btn btn--ghost btn--sm"
              onClick={() => setIsSetup(false)}
              aria-label="Change section and language"
            >
              Change
            </button>
          </div>

          <FanChatWidget section={section} language={language} />
        </>
      )}
    </main>
  );
}
