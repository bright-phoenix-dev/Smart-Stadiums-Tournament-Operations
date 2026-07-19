/**
 * Shared Constants
 * =================
 * Application-wide constants shared across multiple components.
 * Centralized here to maintain DRY and ensure consistency.
 */

/**
 * Supported languages for the fan experience interface.
 * Each entry includes a language code, display name, and flag emoji.
 */
export const LANGUAGES = [
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
  { code: 'ar', name: 'العربية', flag: '🇸🇦' },
  { code: 'pt', name: 'Português', flag: '🇧🇷' },
  { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
];

export const INCIDENT_SEVERITY = {
  CRITICAL: 'critical',
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
};

export const ACOUSTIC_FREQUENCIES = {
  ULTRASONIC_CHIRP: 18500,
  RESONANCE_LOW: 50,
  ALERT_PITCH: 880,
};

/** One-click operational query presets */
export const STAFF_QUICK_ACTIONS = [
  { label: '🚪 Gate status', message: 'Give me a full gate congestion breakdown. Which gates need attention?' },
  { label: '🚨 Incidents', message: 'Summarize all active incidents and recommend priority actions.' },
  { label: '👥 Staffing', message: 'Based on current congestion, where should I redeploy staff?' },
  { label: '🍔 Concessions', message: 'Which concessions have the longest queues and need more staff?' },
  { label: '🚆 Transit', message: 'What is the transit situation? Any delays I should plan for?' },
];
