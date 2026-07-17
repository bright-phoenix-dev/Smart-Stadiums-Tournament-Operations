/**
 * Global Error Boundary
 * =====================
 * Catches unhandled JavaScript exceptions anywhere in the React
 * component tree and displays a clean fallback UI instead of crashing.
 */

import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Frontend Error Caught by Boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          padding: 'var(--space-4)',
          textAlign: 'center'
        }}>
          <h2 style={{ color: 'var(--color-accent-coral)' }}>⚠️ Application Error</h2>
          <p style={{ marginTop: 'var(--space-2)' }}>
            We encountered an unexpected error processing live stadium data.
          </p>
          <button
            className="btn btn--primary"
            style={{ marginTop: 'var(--space-4)' }}
            onClick={() => window.location.reload()}
          >
            Reload Dashboard
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
