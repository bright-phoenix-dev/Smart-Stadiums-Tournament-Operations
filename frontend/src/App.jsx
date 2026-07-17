/**
 * App Component — Root Application
 * ==================================
 * Sets up React Router with two routes:
 *   - / (and /dashboard): Staff Operations Dashboard
 *   - /fan: Fan Experience Widget
 *
 * Includes the global header with navigation, accessibility
 * toggle, and skip-to-content link.
 */

import React, { useState, useCallback } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import FanView from './pages/FanView';
import ErrorBoundary from './components/ErrorBoundary';

export default function App() {
  const [highContrast, setHighContrast] = useState(false);

  const toggleContrast = useCallback(() => {
    setHighContrast((prev) => {
      const next = !prev;
      document.documentElement.setAttribute(
        'data-theme',
        next ? 'high-contrast' : ''
      );
      return next;
    });
  }, []);

  return (
    <BrowserRouter>
      <div className="app-layout">
        {/* Skip to main content — accessibility */}
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>

        {/* Global Header */}
        <header className="app-header" role="banner">
          <div className="app-header__logo">
            <span aria-hidden="true" style={{ fontSize: '1.5rem' }}>🏟️</span>
            <div>
              <div className="app-header__title">FIFA World Cup 2026</div>
              <div className="app-header__subtitle">Smart Stadium Platform</div>
            </div>
          </div>

          <nav className="app-header__nav" role="navigation" aria-label="Main navigation">
            <div className="nav-tabs">
              <NavLink
                to="/dashboard"
                className={({ isActive }) =>
                  `nav-tab ${isActive ? 'nav-tab--active' : ''}`
                }
                aria-label="Staff Operations Dashboard"
              >
                📊 Dashboard
              </NavLink>
              <NavLink
                to="/fan"
                className={({ isActive }) =>
                  `nav-tab ${isActive ? 'nav-tab--active' : ''}`
                }
                aria-label="Fan Match Day Assistant"
              >
                ⚽ Fan View
              </NavLink>
            </div>

            {/* High Contrast Toggle */}
            <div className="a11y-toggle">
              <span id="contrast-label" style={{ fontSize: 'var(--text-xs)' }}>
                {highContrast ? '◉' : '◎'}
              </span>
              <button
                className={`a11y-toggle__switch ${highContrast ? 'a11y-toggle__switch--active' : ''}`}
                onClick={toggleContrast}
                role="switch"
                aria-checked={highContrast}
                aria-labelledby="contrast-label"
                aria-label="Toggle high contrast mode"
                title="Toggle high contrast mode for accessibility"
              />
            </div>
          </nav>
        </header>

        {/* Route Content wrapped in Error Boundary */}
        <ErrorBoundary>
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/fan" element={<FanView />} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </ErrorBoundary>
      </div>
    </BrowserRouter>
  );
}
