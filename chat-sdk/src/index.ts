/**
 * RAZE Chat SDK - Embeddable Widget
 * Complete TypeScript implementation of the embeddable chat widget
 */

interface RazeChatConfig {
  apiUrl: string;
  apiKey?: string;
  theme?: {
    primaryColor?: string;
    textColor?: string;
    backgroundColor?: string;
  };
  botName?: string;
  welcomeMessage?: string;
  position?: 'bottom-right' | 'bottom-left';
  language?: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

class RazeChatWidget {
  private config: RazeChatConfig;
  private sessionId: string = '';
  private messages: Message[] = [];
  private container: HTMLElement | null = null;
  private inputElement: HTMLInputElement | null = null;
  private messagesContainer: HTMLElement | null = null;
  private isOpen: boolean = false;

  constructor(config: RazeChatConfig) {
    this.config = {
      position: 'bottom-right',
      botName: 'RAZE AI',
      welcomeMessage: 'Hi! How can I help?',
      ...config
    };
    this.init();
  }

  private async init() {
    // Inject styles
    this.injectStyles();

    // Create DOM elements
    this.createWidget();

    // Initialize session
    await this.initializeSession();

    // Attach event listeners
    this.attachEventListeners();
  }

  private injectStyles() {
    if (document.getElementById('raze-chat-styles')) return;

    const style = document.createElement('style');
    style.id = 'raze-chat-styles';
    style.textContent = `
      .raze-chat-button {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: ${this.config.theme?.primaryColor || '#7C3AED'};
        border: none;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 9999;
        transition: transform 0.3s ease;
        font-size: 24px;
      }

      .raze-chat-button:hover {
        transform: scale(1.1);
      }

      .raze-chat-button.left {
        right: auto;
        left: 20px;
      }

      .raze-chat-window {
        position: fixed;
        bottom: 90px;
        right: 20px;
        width: 380px;
        height: 600px;
        background: ${this.config.theme?.backgroundColor || '#FFFFFF'};
        border-radius: 12px;
        box-shadow: 0 5px 30px rgba(0, 0, 0, 0.2);
        display: none;
        flex-direction: column;
        z-index: 9998;
        overflow: hidden;
      }

      .raze-chat-window.left {
        right: auto;
        left: 20px;
      }

      .raze-chat-window.open {
        display: flex;
      }

      .raze-chat-header {
        background: ${this.config.theme?.primaryColor || '#7C3AED'};
        color: white;
        padding: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-radius: 12px 12px 0 0;
      }

      .raze-chat-close {
        background: none;
        border: none;
        color: white;
        cursor: pointer;
        font-size: 24px;
        padding: 0;
      }

      .raze-messages {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        background: ${this.config.theme?.backgroundColor || '#FFFFFF'};
      }

      .raze-message {
        margin-bottom: 12px;
        display: flex;
        gap: 8px;
      }

      .raze-message.user {
        justify-content: flex-end;
      }

      .raze-message-content {
        max-width: 70%;
        padding: 10px 14px;
        border-radius: 8px;
        word-wrap: break-word;
      }

      .raze-message.assistant .raze-message-content {
        background: #E5E7EB;
        color: #1F2937;
      }

      .raze-message.user .raze-message-content {
        background: ${this.config.theme?.primaryColor || '#7C3AED'};
        color: white;
      }

      .raze-input-container {
        display: flex;
        gap: 8px;
        padding: 12px;
        border-top: 1px solid #E5E7EB;
      }

      .raze-input {
        flex: 1;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        padding: 10px;
        font-size: 14px;
        outline: none;
      }

      .raze-input:focus {
        border-color: ${this.config.theme?.primaryColor || '#7C3AED'};
      }

      .raze-send-btn {
        background: ${this.config.theme?.primaryColor || '#7C3AED'};
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 14px;
        cursor: pointer;
        font-size: 16px;
      }

      .raze-typing-indicator {
        display: flex;
        gap: 4px;
        padding: 10px;
      }

      .raze-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #7C3AED;
        animation: raze-bounce 1.4s infinite;
      }

      .raze-dot:nth-child(2) { animation-delay: 0.2s; }
      .raze-dot:nth-child(3) { animation-delay: 0.4s; }

      @keyframes raze-bounce {
        0%, 80%, 100% { opacity: 0.3; }
        40% { opacity: 1; }
      }
    `;

    document.head.appendChild(style);
  }

  private createWidget() {
    // Chat button
    const button = document.createElement('button');
    button.className = `raze-chat-button ${
      this.config.position === 'bottom-left' ? 'left' : ''
    }`;
    button.innerHTML = '💬';
    button.onclick = () => this.toggleWindow();
    document.body.appendChild(button);

    // Chat window
    const window = document.createElement('div');
    window.className = `raze-chat-window ${
      this.config.position === 'bottom-left' ? 'left' : ''
    }`;

    window.innerHTML = `
      <div class="raze-chat-header">
        <span>${this.config.botName}</span>
        <button class="raze-chat-close">&times;</button>
      </div>
      <div class="raze-messages"></div>
      <div class="raze-input-container">
        <input type="text" class="raze-input" placeholder="Type a message..."/>
        <button class="raze-send-btn">Send</button>
      </div>
    `;

    document.body.appendChild(window);

    this.container = window;
    this.messagesContainer = window.querySelector('.raze-messages');
    this.inputElement = window.querySelector('.raze-input') as HTMLInputElement;

    // Add close handler
    window.querySelector('.raze-chat-close')?.addEventListener('click', () => {
      this.toggleWindow();
    });
  }

  private async initializeSession() {
    try {
      const response = await fetch(`${this.config.apiUrl}/sdk/init`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.config.apiKey && {
            'X-API-Key': this.config.apiKey
          })
        }
      });

      const data = await response.json();
      this.sessionId = data.session_id;

      // Add welcome message
      this.addMessage({
        id: '0',
        role: 'assistant',
        content: this.config.welcomeMessage || data.config?.welcome_message,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('Failed to initialize RAZE Chat:', error);
    }
  }

  private attachEventListeners() {
    if (!this.inputElement) return;

    this.inputElement.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    const sendBtn = this.container?.querySelector('.raze-send-btn');
    sendBtn?.addEventListener('click', () => this.sendMessage());
  }

  private async sendMessage() {
    if (!this.inputElement || !this.inputElement.value.trim()) return;

    const userMessage = this.inputElement.value.trim();
    this.inputElement.value = '';

    // Add user message
    this.addMessage({
      id: Date.now().toString(),
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    });

    // Show typing indicator
    this.showTypingIndicator();

    try {
      const response = await fetch(`${this.config.apiUrl}/sdk/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.config.apiKey && {
            'X-API-Key': this.config.apiKey
          })
        },
        body: JSON.stringify({
          session_id: this.sessionId,
          message: userMessage
        })
      });

      // Handle streaming response
      const reader = response.body?.getReader();
      let assistantMessage = '';

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = new TextDecoder().decode(value);
        const lines = text.split('\n').filter((l) => l.startsWith('data: '));

        for (const line of lines) {
          try {
            const data = JSON.parse(line.replace('data: ', ''));
            if (data.type === 'text') {
              assistantMessage += data.content;
            }
          } catch (e) {
            // Ignore parse errors
          }
        }
      }

      this.hideTypingIndicator();
      this.addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: assistantMessage || 'I encountered an error. Please try again.',
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      this.hideTypingIndicator();
      this.addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString()
      });
    }
  }

  private addMessage(message: Message) {
    this.messages.push(message);

    const msgEl = document.createElement('div');
    msgEl.className = `raze-message ${message.role}`;
    msgEl.innerHTML = `<div class="raze-message-content">${this.escapeHtml(
      message.content
    )}</div>`;

    this.messagesContainer?.appendChild(msgEl);
    this.scrollToBottom();
  }

  private showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'raze-typing-indicator';
    indicator.id = 'raze-typing';
    indicator.innerHTML =
      '<div class="raze-dot"></div><div class="raze-dot"></div><div class="raze-dot"></div>';
    this.messagesContainer?.appendChild(indicator);
    this.scrollToBottom();
  }

  private hideTypingIndicator() {
    document.getElementById('raze-typing')?.remove();
  }

  private toggleWindow() {
    this.isOpen = !this.isOpen;
    this.container?.classList.toggle('open');

    if (this.isOpen) {
      this.inputElement?.focus();
    }
  }

  private scrollToBottom() {
    if (this.messagesContainer) {
      this.messagesContainer.scrollTop =
        this.messagesContainer.scrollHeight;
    }
  }

  private escapeHtml(text: string): string {
    const map: { [key: string]: string } = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, (m) => map[m]);
  }
}

// Export as global
(window as any).RazeChat = {
  init: (config: RazeChatConfig) => new RazeChatWidget(config)
};

export default RazeChatWidget;
export { RazeChatConfig, Message, RazeChatWidget };
