/**
 * RAZE Chat Widget - Embeddable Chat SDK
 *
 * Usage:
 * <script>
 *   window.RAZE_CONFIG = {
 *     apiKey: 'raze_sk_xxxxx',
 *     apiUrl: 'https://your-raze-instance.com',
 *     position: 'bottom-right', // bottom-right, bottom-left, top-right, top-left
 *     theme: '#3B82F6'
 *   };
 * </script>
 * <script src="https://your-raze-instance.com/raze-chat-widget.js"></script>
 */

(function() {
  'use strict';

  const CONFIG = window.RAZE_CONFIG || {};
  const API_KEY = CONFIG.apiKey;
  const API_URL = CONFIG.apiUrl || 'http://localhost';
  const POSITION = CONFIG.position || 'bottom-right';
  const THEME_COLOR = CONFIG.theme || '#3B82F6';

  if (!API_KEY) {
    console.error('RAZE Chat Widget: apiKey not configured');
    return;
  }

  class RazeChatWidget {
    constructor() {
      this.isOpen = false;
      this.messages = [];
      this.selectedKnowledge = new Set();
      this.init();
    }

    init() {
      this.createStyles();
      this.createHTML();
      this.attachEventListeners();
    }

    createStyles() {
      const style = document.createElement('style');
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
          display: none;
          position: absolute;
          ${POSITION.includes('bottom') ? 'bottom: 80px;' : 'top: 80px;'}
          ${POSITION.includes('right') ? 'right: 0;' : 'left: 0;'}
          width: 400px;
          height: 600px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 5px 40px rgba(0, 0, 0, 0.16);
          display: flex;
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
          line-height: 1.4;
          word-wrap: break-word;
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

        .raze-input-area {
          padding: 12px 16px;
          background: white;
          border-top: 1px solid #e5e7eb;
          display: flex;
          gap: 8px;
        }

        .raze-knowledge-toggle {
          padding: 8px;
          background: #f3f4f6;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 12px;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .raze-knowledge-toggle.active {
          background: ${THEME_COLOR};
          color: white;
          border-color: ${THEME_COLOR};
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

    createHTML() {
      const container = document.createElement('div');
      container.className = 'raze-widget-container';
      container.innerHTML = `
        <button class="raze-chat-button" id="raze-toggle">
          <span>💬</span>
        </button>

        <div class="raze-chat-window" id="raze-window">
          <div class="raze-chat-header">
            <h3>Chat Assistant</h3>
            <button class="raze-close-btn" id="raze-close">×</button>
          </div>

          <div class="raze-messages" id="raze-messages">
            <div class="raze-message assistant">
              <div class="raze-message-content">
                👋 Hi! How can I help you today?
              </div>
            </div>
          </div>

          <div class="raze-input-area">
            <button class="raze-knowledge-toggle active" id="raze-knowledge-toggle" title="Use knowledge base">
              📚 Knowledge
            </button>
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
      const window = document.getElementById('raze-window');
      const input = document.getElementById('raze-input');
      const send = document.getElementById('raze-send');
      const knowledgeToggle = document.getElementById('raze-knowledge-toggle');

      toggle.addEventListener('click', () => this.openChat());
      close.addEventListener('click', () => this.closeChat());
      send.addEventListener('click', () => this.sendMessage());
      input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });

      knowledgeToggle.addEventListener('click', () => {
        knowledgeToggle.classList.toggle('active');
        this.useKnowledge = knowledgeToggle.classList.contains('active');
      });

      this.useKnowledge = true;
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
      messageDiv.innerHTML = `
        <div class="raze-message-content">${this.escapeHtml(content)}</div>
      `;
      messagesDiv.appendChild(messageDiv);
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    async sendMessage() {
      const message = this.inputElement.value.trim();
      if (!message) return;

      // Show user message
      this.addMessage(message, 'user');
      this.inputElement.value = '';
      this.sendBtn.disabled = true;

      // Show loading
      const messagesDiv = document.getElementById('raze-messages');
      const loadingDiv = document.createElement('div');
      loadingDiv.className = 'raze-message assistant';
      loadingDiv.innerHTML = `
        <div class="raze-loading">
          <div class="raze-loading-dot"></div>
          <div class="raze-loading-dot"></div>
          <div class="raze-loading-dot"></div>
        </div>
      `;
      messagesDiv.appendChild(loadingDiv);
      messagesDiv.scrollTop = messagesDiv.scrollHeight;

      try {
        const response = await fetch(`${API_URL}/api/v1/chat-sdk/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': API_KEY,
          },
          body: JSON.stringify({
            message: message,
            knowledge_ids: Array.from(this.selectedKnowledge),
          }),
        });

        loadingDiv.remove();

        if (response.ok) {
          const data = await response.json();
          let displayText = data.response;

          if (data.latency_ms) {
            displayText += `\n\n📊 Response time: ${data.latency_ms}ms`;
          }

          this.addMessage(displayText, 'assistant');
        } else {
          const error = await response.json().catch(() => ({}));
          const errorMsg = error.detail || 'Failed to get response. Please try again.';
          this.addMessage(`❌ Error: ${errorMsg}`, 'assistant');
        }
      } catch (error) {
        loadingDiv.remove();
        this.addMessage('❌ Connection error. Please check your API key and URL.', 'assistant');
        console.error('Chat error:', error);
      }

      this.sendBtn.disabled = false;
      this.inputElement.focus();
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
