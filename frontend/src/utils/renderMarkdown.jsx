/**
 * renderMarkdown — Shared Markdown Renderer
 * ============================================
 * Converts a plain-text string with lightweight markdown syntax
 * into React elements. Supports:
 *   - **bold** → <strong>
 *   - Newlines → <br />
 *
 * Used by both StaffAssistant and FanChatWidget to avoid
 * duplicating rendering logic (DRY principle).
 *
 * @param {string} content - Raw text with optional **bold** markers
 * @returns {React.ReactNode[]} Array of React elements
 */

import React from 'react';

export default function renderMarkdown(content) {
  return (content?.split('\n') || []).map((line, i, arr) => (
    <React.Fragment key={i}>
      {line.split(/(\*\*[^*]+\*\*)/).map((part, j) =>
        part.startsWith('**') && part.endsWith('**') ? (
          <strong key={j}>{part.slice(2, -2)}</strong>
        ) : (
          <span key={j}>{part}</span>
        )
      )}
      {i < arr.length - 1 && <br />}
    </React.Fragment>
  ));
}
