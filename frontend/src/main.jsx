/**
 * Application Entry Point
 * ========================
 * Renders the React application with StrictMode enabled
 * for development warnings and the global CSS import.
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
);
