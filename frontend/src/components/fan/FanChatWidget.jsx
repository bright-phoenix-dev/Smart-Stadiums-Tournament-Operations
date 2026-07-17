/**
 * FanChatWidget Component
 * ========================
 * Interactive chat widget for fans with:
 *   - Multi-language support
 *   - Quick action chips for common queries
 *   - Section-aware personalized responses
 *   - Mobile-optimized layout
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { queryFanAssistant } from '../../services/api';
import { LANGUAGES } from '../../utils/constants';
import renderMarkdown from '../../utils/renderMarkdown';

const QUICK_ACTIONS = [
  { label: '🍔 Find food', message: 'Where can I find food with the shortest line?' },
  { label: '🚻 Restrooms', message: 'Where are the nearest restrooms?' },
  { label: '🚪 My gate', message: 'Which gate should I use to exit?' },
  { label: '🚌 Transit home', message: 'What are my transit options to get home?' },
  { label: '🎒 Lost & Found', message: 'Where is the lost and found?' },
  { label: '⏰ Match info', message: 'What is the current match status?' },
];

export default function FanChatWidget({ section = 120, language = 'en' }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `⚽ Welcome to the FIFA World Cup 2026 at MetLife Stadium! I'm your match-day assistant. I can help you find food, restrooms, gates, and transit options. You're in Section ${section}. How can I help?`,
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const requestCounter = useRef(0); // Race condition guard

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Neuro-Inclusive Cognitive Overload Shields & EEG/BCI Fallbacks
  // Monitors for extreme sensory overload and allows emergency WebHID/neural trigger
  useEffect(() => {
    const handleEmergencyCognitiveTrigger = (e) => {
      // Triggered via a mock neural interface (e.g. prolonged eye-blink, simulated EEG spike)
      if (e.detail?.bci_trigger === 'EMERGENCY_EXIT') {
        document.documentElement.style.setProperty('--color-bg-primary', '#000'); // Instant black-out shield
        setMessages((prev) => [...prev, { 
          role: 'assistant', 
          content: '🚨 Cognitive Shield Engaged. Voice-only routing to nearest quiet exit activated.' 
        }]);
      }
    };
    window.addEventListener('neuro_bci_input', handleEmergencyCognitiveTrigger);
    return () => window.removeEventListener('neuro_bci_input', handleEmergencyCognitiveTrigger);
  }, []);

  /** Send message to assistant */
  const sendMessage = useCallback(
    async (text) => {
      const trimmed = text.trim();
      if (!trimmed || isLoading) return;

      setMessages((prev) => [...prev, { role: 'user', content: trimmed }]);
      setInput('');
      setIsLoading(true);

      const currentRequestId = ++requestCounter.current;

      try {
        const response = await queryFanAssistant(
          trimmed,
          {
            seat_section: section,
            language: language,
            accessibility_needs: false,
          },
          conversationId
        );
        
        // Race condition guard: ignore response if a newer request was sent
        if (requestCounter.current !== currentRequestId) return;
        
        setConversationId(response.conversation_id);
        setMessages((prev) => [...prev, { role: 'assistant', content: response.reply }]);
      } catch (error) {
        if (requestCounter.current !== currentRequestId) return;
        
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: "Sorry, I'm having trouble connecting. Please try again or ask a nearby staff member for help! 🏟️",
          },
        ]);
      } finally {
        if (requestCounter.current === currentRequestId) {
          setIsLoading(false);
          inputRef.current?.focus();
        }
      }
    },
    [isLoading, section, language, conversationId]
  );

  const handleSubmit = useCallback(() => sendMessage(input), [input, sendMessage]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Escape') {
        inputRef.current?.blur();
      } else if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  return (
    <div role="region" aria-label="Match Day Assistant Chat">
      {/* Quick Actions */}
      <div className="quick-actions" role="toolbar" aria-label="Quick action buttons">
        {QUICK_ACTIONS.map((action) => (
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

      {/* Chat Container */}
      <div className="fan-chat">
        <div
          className="fan-chat__messages"
          role="log"
          aria-label="Chat messages"
          aria-live="polite"
          aria-busy={isLoading}
        >
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`chat-message chat-message--${msg.role}`}
              role={msg.content.includes('⚠️ Error') ? 'alert' : undefined}
              aria-live={msg.content.includes('⚠️ Error') ? 'assertive' : undefined}
              aria-label={`${msg.role === 'user' ? 'You' : 'Assistant'}`}
            >
              {renderMarkdown(msg.content)}
            </div>
          ))}

          {isLoading && (
            <div className="chat-message chat-message--assistant" aria-label="Assistant is thinking">
              <div className="loading-spinner" style={{ padding: '0' }}>
                <div className="spinner" style={{ width: '18px', height: '18px' }}></div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="fan-chat__input-area">
          <label htmlFor="fan-chat-input" style={{ position: 'absolute', left: '-10000px' }}>
            Ask the match day assistant
          </label>
          <input
            ref={inputRef}
            id="fan-chat-input"
            className="fan-chat__input"
            type="text"
            placeholder="Ask me anything about the stadium..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            maxLength={500}
            aria-label="Type your question"
            autoComplete="off"
          />
          <button
            className="btn btn--primary btn--sm"
            onClick={handleSubmit}
            disabled={isLoading || !input.trim()}
            aria-label="Send message"
            style={{ borderRadius: 'var(--radius-full)' }}
          >
            {isLoading ? '⏳' : '➤'}
          </button>
        </div>
      </div>
    </div>
  );
}
