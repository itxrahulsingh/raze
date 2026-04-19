/**
 * RAZE Chat Widget - Embeddable Chat SDK
 *
 * Features:
 * - Session persistence (per visitor UUID)
 * - Config loading from backend (bot name, welcome message, colors)
 * - Real-time SSE streaming with live token append
 * - Pure JS markdown rendering (bold, italic, code, lists, links)
 * - Error handling with graceful fallbacks
 *
 * Usage:
 * <script>
 *   window.RAZE_CONFIG = {
 *     apiKey: 'raze_sk_xxxxx',
 *     apiUrl: 'https://your-raze-instance.com',
 *     position: 'bottom-right'
 *   };
 * </script>
 * <script src="https://your-raze-instance.com/raze-chat-widget.js"></script>
 */

(function() {
  'use strict';

  const CONFIG = window.RAZE_CONFIG || {};
  const API_KEY = CONFIG.apiKey;
  const RAW_API_URL = CONFIG.apiUrl || 'http://localhost:8000';
  const BASE_API_URL = RAW_API_URL.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
  const API_URL = (function normalizeApiUrl() {
    try {
      const parsed = new URL(BASE_API_URL, window.location.origin);
      // Avoid mixed-content errors on HTTPS host pages.
      if (window.location.protocol === 'https:' && parsed.protocol === 'http:' && !CONFIG.allowInsecureHttp) {
        parsed.protocol = 'https:';
      }
      return parsed.toString().replace(/\/$/, '');
    } catch (_) {
      return BASE_API_URL;
    }
  })();
  const POSITION = CONFIG.position || 'bottom-right';

  if (!API_KEY) {
    console.error('RAZE Chat Widget: apiKey not configured');
    return;
  }

  class RazeChatWidget {
    constructor() {
      this.isOpen = false;
      this.messages = [];
      this.config = null;
      this.sessionId = this.getOrCreateSessionId();
      this.isStreaming = false;
      this.init();
    }

    getOrCreateSessionId() {
      const key = `raze_session_${API_KEY.substring(0, 8)}`;
      let sessionId = sessionStorage.getItem(key);
      if (!sessionId) {
        sessionId = 'sdk_' + Math.random().toString(16).substr(2, 8);
        sessionStorage.setItem(key, sessionId);
      }
      return sessionId;
    }

    async init() {
      this.createStyles();
      // Load config before rendering HTML
      const configLoaded = await this.loadConfig();
      this.createHTML(configLoaded);
      this.attachEventListeners();
    }

    async loadConfig() {
      try {
        const response = await this.fetchWithRetry(`${API_URL}/api/v1/chat-sdk/config`, {
          method: 'GET',
          headers: {
            'X-API-Key': API_KEY,
          },
        }, 2);
        if (response.ok) {
          this.config = await response.json();
          return true;
        }
        const errorText = await response.text().catch(() => '');
        console.warn(`Widget config request failed (${response.status}):`, errorText);
      } catch (error) {
        console.warn('Failed to load widget config:', error);
      }
      // Use defaults if config load fails
      this.config = {
        bot_name: 'Assistant',
        welcome_message: 'How can I help you today?',
        widget_color: '#007bff',
        show_knowledge_sources: true,
      };
      return false;
    }

    async fetchWithRetry(url, options, retries = 1) {
      let lastError;
      for (let i = 0; i <= retries; i++) {
        try {
          const res = await fetch(url, options);
          if (res.ok || i === retries) return res;
        } catch (error) {
          lastError = error;
          if (i === retries) throw error;
        }
        await new Promise((resolve) => setTimeout(resolve, 400 * (i + 1)));
      }
      throw lastError || new Error('Request failed');
    }

    createStyles() {
      const style = document.createElement('style');
      const THEME_COLOR = (this.config && this.config.widget_color) || '#007bff';

      style.textContent = `
        .raze-widget-container {
          position: fixed;
          ${POSITION.includes('bottom') ? 'bottom: 20px;' : 'top: 20px;'}
          ${POSITION.includes('right') ? 'right: 20px;' : 'left: 20px;'}
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          z-index: 999999;
        }

        .raze-chat-button {
          width: 56px;
          height: 56px;
          border-radius: 50%;
          background: ${THEME_COLOR};
          color: white;
          border: none;
          cursor: pointer;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 24px;
          transition: all 0.3s ease;
        }

        .raze-chat-button:hover {
          transform: scale(1.1);
          box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
        }

        .raze-chat-button.open {
          display: none;
        }

        .raze-chat-window {
          position: absolute;
          ${POSITION.includes('bottom') ? 'bottom: 80px;' : 'top: 80px;'}
          ${POSITION.includes('right') ? 'right: 0;' : 'left: 0;'}
          width: 400px;
          height: 600px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 5px 40px rgba(0, 0, 0, 0.16);
          display: none;
          flex-direction: column;
          overflow: hidden;
          animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
          from {
            opacity: 0;
            transform: scale(0.95);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }

        .raze-chat-window.open {
          display: flex;
        }

        .raze-chat-header {
          background: ${THEME_COLOR};
          color: white;
          padding: 16px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          border-radius: 12px 12px 0 0;
        }

        .raze-chat-header h3 {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
        }

        .raze-close-btn {
          background: none;
          border: none;
          color: white;
          font-size: 24px;
          cursor: pointer;
          padding: 0;
        }

        .raze-messages {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
          background: #f9fafb;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .raze-message {
          display: flex;
          gap: 8px;
          animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        .raze-message.user {
          justify-content: flex-end;
        }

        .raze-message-content {
          max-width: 80%;
          padding: 10px 14px;
          border-radius: 12px;
          font-size: 14px;
          line-height: 1.5;
          word-wrap: break-word;
          white-space: pre-wrap;
        }

        .raze-message.assistant .raze-message-content {
          background: white;
          color: #1f2937;
          border: 1px solid #e5e7eb;
        }

        .raze-message.user .raze-message-content {
          background: ${THEME_COLOR};
          color: white;
        }

        /* Markdown styles */
        .raze-message-content strong {
          font-weight: 600;
        }

        .raze-message-content em {
          font-style: italic;
        }

        .raze-message-content code {
          background: #f0f0f0;
          padding: 2px 6px;
          border-radius: 3px;
          font-family: 'Courier New', monospace;
          font-size: 0.9em;
        }

        .raze-message.assistant .raze-message-content code {
          background: #e5e7eb;
          color: #1f2937;
        }

        .raze-message.user .raze-message-content code {
          background: rgba(255, 255, 255, 0.2);
          color: white;
        }

        .raze-message-content ul,
        .raze-message-content ol {
          margin: 8px 0;
          padding-left: 20px;
        }

        .raze-message-content li {
          margin: 4px 0;
        }

        .raze-message-content a {
          color: ${THEME_COLOR};
          text-decoration: underline;
          cursor: pointer;
        }

        .raze-message.user .raze-message-content a {
          color: white;
        }

        .raze-input-area {
          padding: 12px 16px;
          background: white;
          border-top: 1px solid #e5e7eb;
          display: flex;
          gap: 8px;
        }

        .raze-input-group {
          display: flex;
          gap: 8px;
          width: 100%;
        }

        .raze-input {
          flex: 1;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          padding: 10px;
          font-size: 14px;
          font-family: inherit;
          resize: none;
          height: 40px;
        }

        .raze-input:focus {
          outline: none;
          border-color: ${THEME_COLOR};
          box-shadow: 0 0 0 3px ${THEME_COLOR}20;
        }

        .raze-send-btn {
          background: ${THEME_COLOR};
          color: white;
          border: none;
          border-radius: 6px;
          width: 40px;
          height: 40px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 18px;
          transition: all 0.2s;
        }

        .raze-send-btn:hover:not(:disabled) {
          opacity: 0.9;
        }

        .raze-send-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .raze-loading {
          display: flex;
          gap: 4px;
          align-items: center;
          padding: 8px;
        }

        .raze-loading-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: ${THEME_COLOR};
          animation: bounce 1.4s infinite;
        }

        .raze-loading-dot:nth-child(2) { animation-delay: 0.2s; }
        .raze-loading-dot:nth-child(3) { animation-delay: 0.4s; }

        @keyframes bounce {
          0%, 80%, 100% { opacity: 0.5; }
          40% { opacity: 1; }
        }

        @media (max-width: 640px) {
          .raze-chat-window {
            width: calc(100vw - 32px);
            height: 70vh;
            max-height: 500px;
          }
        }
      `;
      document.head.appendChild(style);
    }

    createHTML(configLoaded) {
      const botName = (this.config && this.config.bot_name) || 'Assistant';
      const displayName = (this.config && this.config.display_name) || '';
      const welcomeMsg = (this.config && this.config.welcome_message) || 'How can I help you today?';

      const container = document.createElement('div');
      container.className = 'raze-widget-container';
      container.innerHTML = `
        <button class="raze-chat-button" id="raze-toggle">
          <span>💬</span>
        </button>

        <div class="raze-chat-window" id="raze-window">
          <div class="raze-chat-header">
            <div>
              <h3>${this.escapeHtml(botName)}</h3>
              ${displayName ? `<div style="font-size:12px;opacity:0.9;line-height:1.2">${this.escapeHtml(displayName)}</div>` : ''}
            </div>
            <button class="raze-close-btn" id="raze-close">×</button>
          </div>

          <div class="raze-messages" id="raze-messages">
            <div class="raze-message assistant">
              <div class="raze-message-content">
                👋 ${this.escapeHtml(welcomeMsg)}
              </div>
            </div>
          </div>

          <div class="raze-input-area">
            <div class="raze-input-group">
              <input
                type="text"
                class="raze-input"
                id="raze-input"
                placeholder="Type your message..."
                maxlength="500"
              />
              <button class="raze-send-btn" id="raze-send">➤</button>
            </div>
          </div>
        </div>
      `;

      document.body.appendChild(container);
    }

    attachEventListeners() {
      const toggle = document.getElementById('raze-toggle');
      const close = document.getElementById('raze-close');
      const input = document.getElementById('raze-input');
      const send = document.getElementById('raze-send');

      toggle.addEventListener('click', () => this.openChat());
      close.addEventListener('click', () => this.closeChat());
      send.addEventListener('click', () => this.sendMessage());
      input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });

      this.inputElement = input;
      this.sendBtn = send;
    }

    openChat() {
      document.getElementById('raze-window').classList.add('open');
      document.getElementById('raze-toggle').classList.add('open');
      this.inputElement.focus();
      this.isOpen = true;
    }

    closeChat() {
      document.getElementById('raze-window').classList.remove('open');
      document.getElementById('raze-toggle').classList.remove('open');
      this.isOpen = false;
    }

    addMessage(content, role = 'assistant') {
      const messagesDiv = document.getElementById('raze-messages');
      const messageDiv = document.createElement('div');
      messageDiv.className = `raze-message ${role}`;

      const contentDiv = document.createElement('div');
      contentDiv.className = 'raze-message-content';

      if (role === 'assistant') {
        contentDiv.innerHTML = this.parseMarkdown(content);
      } else {
        contentDiv.textContent = content;
      }

      messageDiv.appendChild(contentDiv);
      messagesDiv.appendChild(messageDiv);
      messagesDiv.scrollTop = messagesDiv.scrollHeight;

      return messageDiv;
    }

    parseMarkdown(text) {
      // Escape HTML first
      let escaped = this.escapeHtml(text);

      // Bold: **text** → <strong>text</strong>
      escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

      // Italic: *text* → <em>text</em> (but not in bold)
      escaped = escaped.replace(/\*(.*?)\*/g, '<em>$1</em>');

      // Inline code: `text` → <code>text</code>
      escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');

      // Links: [text](url) → <a href="url">text</a>
      escaped = escaped.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

      // Line breaks
      escaped = escaped.replace(/\n/g, '<br>');

      return escaped;
    }

    async sendMessage() {
      const message = this.inputElement.value.trim();
      if (!message || this.isStreaming) return;

      // Show user message
      this.addMessage(message, 'user');
      this.inputElement.value = '';
      this.sendBtn.disabled = true;
      this.isStreaming = true;

      // Create assistant message bubble for streaming
      const messagesDiv = document.getElementById('raze-messages');
      const messageDiv = document.createElement('div');
      messageDiv.className = 'raze-message assistant';

      const contentDiv = document.createElement('div');
      contentDiv.className = 'raze-message-content';
      contentDiv.textContent = '';

      messageDiv.appendChild(contentDiv);
      messagesDiv.appendChild(messageDiv);
      messagesDiv.scrollTop = messagesDiv.scrollHeight;

      try {
        await this.streamChat(message, contentDiv);
      } catch (error) {
        contentDiv.textContent = '❌ Connection error. Please try again.';
        console.error('Chat error:', error);
      }

      this.isStreaming = false;
      this.sendBtn.disabled = false;
      this.inputElement.focus();
    }

    async streamChat(message, contentDiv) {
      try {
        const response = await this.fetchWithRetry(`${API_URL}/api/v1/chat-sdk/chat/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': API_KEY,
          },
          body: JSON.stringify({
            message: message,
            session_id: this.sessionId,
            knowledge_ids: [],
          }),
        }, 1);

        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          const errorMsg = error.detail || 'Failed to get response';
          contentDiv.innerHTML = `<strong>Error:</strong> ${this.escapeHtml(errorMsg)}`;
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullContent = '';
        let pendingText = '';
        let metadata = null;
        let rafScheduled = false;

        const flush = () => {
          if (!pendingText) return;
          fullContent += pendingText;
          pendingText = '';
          // Render raw text while streaming for speed; markdown on final.
          contentDiv.textContent = fullContent;
          const messagesDiv = document.getElementById('raze-messages');
          if (messagesDiv) messagesDiv.scrollTop = messagesDiv.scrollHeight;
        };

        const scheduleFlush = () => {
          if (rafScheduled) return;
          rafScheduled = true;
          requestAnimationFrame(() => {
            rafScheduled = false;
            flush();
          });
        };

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const json = JSON.parse(line.slice(6));

                if (json.event === 'delta' && json.text) {
                  pendingText += json.text;
                  scheduleFlush();
                } else if (json.event === 'done') {
                  metadata = json;
                }
              } catch (e) {
                console.warn('Failed to parse SSE line:', line);
              }
            }
          }
        }

        // Flush any remaining buffered tokens.
        flush();

        // Final render with markdown
        if (fullContent) {
          contentDiv.innerHTML = this.parseMarkdown(fullContent);
        }

        // Store message in state
        this.messages.push({
          role: 'assistant',
          content: fullContent,
          metadata: metadata,
        });

      } catch (error) {
        contentDiv.innerHTML = '<strong>Error:</strong> Connection failed';
        throw error;
      }
    }

    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }
  }

  // Initialize widget when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      window.razeChat = new RazeChatWidget();
    });
  } else {
    window.razeChat = new RazeChatWidget();
  }
})();
