/**
 * RAZE Chat SDK – TypeScript interfaces
 */

// ─── Configuration ────────────────────────────────────────────────────────────

export interface RazeChatTheme {
  /** Primary accent color (button, header background). Default: "#6366f1" */
  primaryColor?: string;
  /** Main text color inside the chat window. Default: "#111827" */
  textColor?: string;
  /** Chat window background color. Default: "#ffffff" */
  backgroundColor?: string;
  /** User message bubble background. Default: "#6366f1" */
  userBubbleColor?: string;
  /** Bot message bubble background. Default: "#f3f4f6" */
  botBubbleColor?: string;
  /** Border radius for bubbles (px). Default: 12 */
  bubbleBorderRadius?: number;
  /** Font family. Default: system-ui */
  fontFamily?: string;
}

export type ChatPosition = "bottom-right" | "bottom-left";

export interface RazeChatConfig {
  /** Base URL of the RAZE backend, e.g. "https://your-raze-instance.com" */
  apiUrl: string;
  /** Optional public API key (X-API-Key header). */
  apiKey?: string;
  /** Visual theme overrides. */
  theme?: RazeChatTheme;
  /** Display name shown in the chat header. Default: "AI Assistant" */
  botName?: string;
  /** First message displayed when the chat opens. */
  welcomeMessage?: string;
  /** Widget position on screen. Default: "bottom-right" */
  position?: ChatPosition;
  /** BCP-47 language tag for UI strings. Default: "en" */
  language?: string;
  /** Custom launcher button icon HTML/SVG (overrides default). */
  launcherIcon?: string;
  /** Extra CSS class added to the root container. */
  containerClass?: string;
  /** z-index of the widget. Default: 9999 */
  zIndex?: number;
}

// ─── Messages ────────────────────────────────────────────────────────────────

export type MessageRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  isError?: boolean;
}

// ─── SSE / Streaming ─────────────────────────────────────────────────────────

export type StreamEventType =
  | "start"
  | "delta"
  | "tool_call"
  | "tool_result"
  | "done"
  | "error";

export interface StreamChunk {
  event: StreamEventType;
  text?: string;
  tool_call?: {
    id: string;
    name: string;
    arguments: string;
  };
  tool_result?: Record<string, unknown>;
  message_id?: string;
  conversation_id?: string;
  tokens_used?: number;
  cost_usd?: number;
  latency_ms?: number;
  error?: string;
  error_code?: string;
}

// ─── Session ────────────────────────────────────────────────────────────────

export interface SessionInitResponse {
  session_id: string;
  conversation_id?: string;
}

// ─── SDK Public API ──────────────────────────────────────────────────────────

export interface RazeChatSDK {
  /** Initialise and mount the chat widget. Call once per page. */
  init(config: RazeChatConfig): void;
  /** Programmatically open the chat panel. */
  open(): void;
  /** Programmatically close the chat panel. */
  close(): void;
  /** Toggle open/close state. */
  toggle(): void;
  /** Send a message as if the user typed it. */
  sendMessage(text: string): void;
  /** Remove the widget from the DOM entirely. */
  destroy(): void;
  /** Current session ID (null before init). */
  readonly sessionId: string | null;
}

// ─── i18n ─────────────────────────────────────────────────────────────────────

export interface UIStrings {
  placeholder: string;
  sendButton: string;
  closeButton: string;
  errorMessage: string;
  typingIndicator: string;
  poweredBy: string;
}
