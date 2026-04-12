// ─── Auth / User ──────────────────────────────────────────────────────────────

export type UserRole = 'admin' | 'operator' | 'viewer';

export interface UserResponse {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  last_login: string | null;
  user_metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface UserListResponse {
  items: UserResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface APIKeyResponse {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  key_prefix: string;
  permissions: string[];
  rate_limit: number | null;
  last_used: string | null;
  total_requests: number;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface APIKeyCreateResponse {
  id: string;
  name: string;
  raw_key: string;
  key_prefix: string;
  permissions: string[];
  expires_at: string | null;
  created_at: string;
}

export interface APIKeyListResponse {
  items: APIKeyResponse[];
  total: number;
}

// ─── AI Config ────────────────────────────────────────────────────────────────

export type LLMProvider = 'openai' | 'anthropic' | 'gemini' | 'grok' | 'ollama';
export type RoutingStrategy = 'cost' | 'performance' | 'balanced' | 'round_robin' | 'latency';

export interface AIConfigResponse {
  id: string;
  name: string;
  description: string | null;
  is_default: boolean;
  is_active: boolean;
  provider: LLMProvider;
  model_name: string;
  temperature: number;
  max_tokens: number;
  top_p: number;
  presence_penalty: number;
  frequency_penalty: number;
  system_prompt: string | null;
  fallback_provider: LLMProvider | null;
  fallback_model: string | null;
  fallback_on_errors: string[];
  cost_limit_daily: number | null;
  cost_per_1k_input_tokens: number | null;
  cost_per_1k_output_tokens: number | null;
  routing_strategy: RoutingStrategy;
  streaming_enabled: boolean;
  tool_calling_enabled: boolean;
  memory_enabled: boolean;
  knowledge_enabled: boolean;
  extra_params: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface AIConfigListResponse {
  items: AIConfigResponse[];
  total: number;
}

export interface AIConfigCreate {
  name: string;
  description?: string | null;
  is_default?: boolean;
  provider: LLMProvider;
  model_name: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  presence_penalty?: number;
  frequency_penalty?: number;
  system_prompt?: string | null;
  fallback_provider?: LLMProvider | null;
  fallback_model?: string | null;
  fallback_on_errors?: string[];
  cost_limit_daily?: number | null;
  cost_per_1k_input_tokens?: number | null;
  cost_per_1k_output_tokens?: number | null;
  routing_strategy?: RoutingStrategy;
  streaming_enabled?: boolean;
  tool_calling_enabled?: boolean;
  memory_enabled?: boolean;
  knowledge_enabled?: boolean;
  extra_params?: Record<string, unknown>;
}

// ─── Admin Dashboard ─────────────────────────────────────────────────────────

export interface TrendPoint {
  label: string;
  value: number;
}

export interface DashboardChart {
  title: string;
  unit: string;
  trend: TrendPoint[];
  current: number;
  change_pct: number | null;
}

export interface TopTool {
  tool_id: string;
  tool_name: string;
  usage_count: number;
  success_rate: number;
  avg_latency_ms: number;
}

export interface TopModel {
  provider: string;
  model_name: string;
  request_count: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
}

export interface ProviderHealth {
  provider: string;
  reachable: boolean;
  latency_ms: number | null;
  last_checked: string;
}

export interface SystemStats {
  total_users: number;
  active_users_today: number;
  total_conversations: number;
  active_conversations: number;
  total_knowledge_sources: number;
  approved_knowledge_sources: number;
  total_tools: number;
  active_tools: number;
  requests_today: number;
  tokens_today: number;
  cost_today_usd: number;
  errors_today: number;
  avg_latency_ms_today: number;
  db_pool_size: number;
  db_checked_out_connections: number;
  redis_connected: boolean;
  redis_memory_used_mb: number | null;
  provider_health: ProviderHealth[];
  collected_at: string;
}

export interface AdminDashboard {
  period_days: number;
  stats: SystemStats;
  requests_chart: DashboardChart;
  tokens_chart: DashboardChart;
  cost_chart: DashboardChart;
  latency_chart: DashboardChart;
  error_rate_chart: DashboardChart;
  top_tools: TopTool[];
  top_models: TopModel[];
  ai_configs: AIConfigResponse[];
  generated_at: string;
}

// ─── Conversations ────────────────────────────────────────────────────────────

export type ConversationStatus = 'active' | 'closed' | 'archived';
export type MessageRole = 'user' | 'assistant' | 'system' | 'tool';

export interface ConversationResponse {
  id: string;
  session_id: string;
  user_id: string | null;
  title: string | null;
  status: ConversationStatus;
  message_count: number;
  total_tokens: number;
  total_cost_usd: number;
  started_at: string | null;
  ended_at: string | null;
  ai_config_id: string | null;
  conv_metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationListResponse {
  items: ConversationResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string | null;
  tool_calls: Record<string, unknown>[] | null;
  tool_results: Record<string, unknown>[] | null;
  tokens_used: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  model_used: string | null;
  provider_used: string | null;
  latency_ms: number | null;
  cost_usd: number | null;
  is_error: boolean;
  error_code: string | null;
  msg_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface MessageListResponse {
  items: MessageResponse[];
  total: number;
  conversation_id: string;
}

// ─── Knowledge ────────────────────────────────────────────────────────────────

export type KnowledgeSourceType = 'pdf' | 'docx' | 'txt' | 'url' | 'markdown' | 'html' | 'csv' | 'json';
export type KnowledgeSourceStatus = 'pending' | 'processing' | 'approved' | 'rejected' | 'failed';
export type KnowledgeSourceMode = 'persistent' | 'ephemeral' | 'session';

export interface KnowledgeSourceResponse {
  id: string;
  name: string;
  description: string | null;
  type: KnowledgeSourceType;
  status: KnowledgeSourceStatus;
  mode: KnowledgeSourceMode;
  file_path: string | null;
  url: string | null;
  file_size: number | null;
  mime_type: string | null;
  content_hash: string | null;
  chunk_count: number;
  embedding_model: string | null;
  processing_error: string | null;
  processed_at: string | null;
  approved_by: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  tags: string[];
  src_metadata: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeSourceListResponse {
  items: KnowledgeSourceResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface KnowledgeChunkResponse {
  id: string;
  source_id: string;
  content: string;
  chunk_index: number;
  token_count: number;
  page_number: number | null;
  section_title: string | null;
  chunk_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface KnowledgeChunkListResponse {
  items: KnowledgeChunkResponse[];
  total: number;
  source_id: string;
}

// ─── Memory ───────────────────────────────────────────────────────────────────

export type MemoryType = 'context' | 'user' | 'operational' | 'knowledge';

export interface MemoryResponse {
  id: string;
  user_id: string | null;
  session_id: string | null;
  type: MemoryType;
  content: string;
  summary: string | null;
  importance_score: number;
  decay_rate: number;
  access_count: number;
  last_accessed: string | null;
  expires_at: string | null;
  is_active: boolean;
  source_conversation_id: string | null;
  mem_metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryListResponse {
  items: MemoryResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface RetentionPolicyResponse {
  id: string;
  name: string;
  type: MemoryType;
  max_count: number | null;
  ttl_days: number | null;
  min_importance: number;
  auto_decay: boolean;
  decay_formula: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Tools ────────────────────────────────────────────────────────────────────

export type ToolType = 'http_api' | 'python_function' | 'database' | 'mcp';
export type ToolAuthType = 'none' | 'api_key' | 'bearer' | 'basic' | 'oauth2';
export type ToolExecutionStatus = 'pending' | 'running' | 'success' | 'failed' | 'timeout';

export interface ToolResponse {
  id: string;
  name: string;
  display_name: string | null;
  description: string;
  type: ToolType;
  schema: Record<string, unknown>;
  endpoint_url: string | null;
  method: string;
  timeout_seconds: number;
  max_retries: number;
  auth_type: ToolAuthType;
  default_headers: Record<string, string> | null;
  is_active: boolean;
  requires_approval: boolean;
  tags: string[];
  usage_count: number;
  success_rate: number;
  avg_latency_ms: number;
  last_used: string | null;
  tool_metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ToolListResponse {
  items: ToolResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface ToolExecutionResponse {
  id: string;
  tool_id: string;
  conversation_id: string | null;
  message_id: string | null;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown> | null;
  status: ToolExecutionStatus;
  error_message: string | null;
  error_code: string | null;
  latency_ms: number | null;
  executed_at: string | null;
  http_status_code: number | null;
  retry_count: number;
  exec_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface ToolExecutionListResponse {
  items: ToolExecutionResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface ToolTestResponse {
  tool_id: string;
  tool_name: string;
  success: boolean;
  output: unknown | null;
  error: string | null;
  latency_ms: number;
  http_status_code: number | null;
}

// ─── Analytics ────────────────────────────────────────────────────────────────

export interface ObservabilityLogResponse {
  id: string;
  conversation_id: string | null;
  message_id: string | null;
  event_type: string;
  intent_detected: string | null;
  model_selected: string | null;
  model_reason: string | null;
  provider_selected: string | null;
  routing_strategy_used: string | null;
  tools_considered: string[];
  tool_selected: string | null;
  tool_selection_reason: string | null;
  confidence_score: number | null;
  context_retrieved: Record<string, unknown>[];
  knowledge_chunks_used: number;
  memory_items_used: number;
  decision_path: Record<string, unknown>[];
  latency_ms: number | null;
  ttft_ms: number | null;
  cost_usd: number | null;
  tokens_prompt: number | null;
  tokens_completion: number | null;
  log_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface ObservabilityLogListResponse {
  items: ObservabilityLogResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface UsageMetricsResponse {
  id: string;
  date: string;
  total_requests: number;
  total_tokens: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  tool_executions: number;
  tool_failures: number;
  knowledge_queries: number;
  memory_reads: number;
  memory_writes: number;
  unique_users: number;
  unique_sessions: number;
  new_conversations: number;
  error_count: number;
  provider_breakdown: Record<string, unknown>;
  model_breakdown: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface UsageMetricsTotals {
  total_requests: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  tool_executions: number;
  knowledge_queries: number;
  unique_users: number;
  error_count: number;
}

export interface UsageMetricsListResponse {
  items: UsageMetricsResponse[];
  total: number;
  totals: UsageMetricsTotals;
}

export interface TimeSeriesPoint {
  timestamp: string;
  value: number;
}

export interface MetricSeries {
  metric: string;
  unit: string;
  data: TimeSeriesPoint[];
  total: number;
  avg: number;
  min: number;
  max: number;
}

export interface AnalyticsSummaryResponse {
  period: {
    start_date: string;
    end_date: string;
    granularity: string;
  };
  series: MetricSeries[];
  top_models: Record<string, unknown>[];
  top_tools: Record<string, unknown>[];
  geo_distribution: Record<string, unknown>[];
  device_distribution: Record<string, unknown>[];
  generated_at: string;
}
