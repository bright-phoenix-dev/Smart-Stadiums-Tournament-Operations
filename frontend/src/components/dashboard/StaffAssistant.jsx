/**
 * StaffAssistant Component
 * =========================
 * Chat panel for staff to query the GenAI operations assistant.
 * Features quick-action chips, conversation history management,
 * and markdown-style message rendering with processing time.
 *
 * @accessibility
 *   - role="region" on container
 *   - role="log" + aria-live on message area
 *   - role="toolbar" on quick-actions
 *   - Keyboard-navigable (Enter to send, Tab through chips)
 *   - Screen-reader labels on all interactive elements
 */

import React, { useCallback, useRef, useState, useEffect } from 'react';
import { queryStaffAssistant } from '../../services/api';
import { STAFF_QUICK_ACTIONS } from '../../utils/constants';
import renderMarkdown from '../../utils/renderMarkdown';

export default function StaffAssistant() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '👋 Operations Assistant ready. Ask me about gate congestion, incidents, concession queues, or transit status for real-time recommendations.',
    },
  ]);
  const [input, setInput] = useState('');
  const [status, setStatus] = useState('idle'); // 'idle' | 'loading' | 'error'
  const isLoading = status === 'loading';
  const [conversationId, setConversationId] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const requestCounter = useRef(0); // Race condition guard

  /** Auto-scroll to latest message */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  /**
   * Core send handler — shared by both manual input and quick-action chips.
   * [Alignment: Smart Stadium Operations] Queries the World Cup 2026 AI Assistant for operational insights.
   *
   * @param {string} text - The query text.
   */
  const sendMessage = useCallback(async (text) => {
    const trimmed = text.trim();
    if (!trimmed || status === 'loading') return;

    // Add user message
    setMessages((prev) => [...prev, { role: 'user', content: trimmed }]);
    setInput('');
    setStatus('loading');

    const currentRequestId = ++requestCounter.current;

    try {
      const response = await queryStaffAssistant(trimmed, conversationId);
      const data = response.unwrap();
      
      // Race condition guard: ignore response if a newer request was sent
      if (requestCounter.current !== currentRequestId) return;
      
      setConversationId(data.conversation_id);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.reply,
          processingTime: data.processing_time_ms,
        },
      ]);
    } catch (error) {
      if (requestCounter.current !== currentRequestId) return;
      
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ Error: ${error.message}. Please try again.`,
        },
      ]);
      setStatus('error');
    } finally {
      if (requestCounter.current === currentRequestId) {
        if (status !== 'error') setStatus('idle');
        inputRef.current?.focus();
      }
    }
  }, [status, conversationId]);

  /** Handle Enter key (Shift+Enter for newline) */
  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(input);
      }
    },
    [sendMessage, input]
  );


  return (
    <section className="glass-card" role="region" aria-label="Operations AI Assistant">
      <div className="glass-card__header">
        <h2 className="glass-card__title">🤖 Ops Assistant</h2>
      </div>

      {/* Quick Action Suggestions */}
      <div
        className="quick-actions"
        role="toolbar"
        aria-label="Quick operational queries"
        style={{ padding: '0 var(--space-4)', marginBottom: 'var(--space-2)' }}
      >
        {STAFF_QUICK_ACTIONS.map((action) => (
          <button
            key={action.label}
            className="quick-action"
            onClick={() => sendMessage(action.message)}
            disabled={isLoading}
            aria-label={action.label}
          >
            {action.label}
          </button>
        ))}
      </div>

      <div className="chat-panel">
        {/* Message list */}
        <div
          className="chat-messages"
          role="log"
          aria-label="Assistant conversation"
          aria-live="polite"
          aria-busy={status === 'loading'}
        >
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`chat-message chat-message--${msg.role}`}
              role={msg.content?.includes('⚠️ Error') ? 'alert' : 'document'}
              aria-live={msg.content?.includes('⚠️ Error') ? 'assertive' : 'off'}
              aria-label={`${msg.role === 'user' ? 'You' : 'Assistant'}: ${msg.content?.substring(0, 100) || ""}`}
            >
              {renderMarkdown(msg.content)}
              {msg.processingTime && (
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-1)' }}>
                  ⚡ {Math.round(msg.processingTime)}ms
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="chat-message chat-message--assistant" aria-label="Assistant is thinking">
              <div className="loading-spinner" style={{ padding: '0' }}>
                <div className="spinner" style={{ width: '20px', height: '20px' }}></div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="chat-input-area">
          <label htmlFor="staff-chat-input" className="sr-only" style={{ position: 'absolute', left: '-10000px' }}>
            Ask the operations assistant
          </label>
          <input
            ref={inputRef}
            id="staff-chat-input"
            className="chat-input"
            type="text"
            placeholder="Ask about gates, incidents, concessions..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={status === 'loading'}
            maxLength={500}
            aria-label="Type your question for the operations assistant"
            autoComplete="off"
          />
          <button
            className="btn btn--primary"
            onClick={() => sendMessage(input)}
            disabled={status === 'loading' || !input.trim()}
            aria-label="Send message"
          >
            {status === 'loading' ? '...' : 'Send'}
          </button>
        </div>
      </div>
    </section>
  );
}
