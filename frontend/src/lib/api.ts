import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import {
  TokenResponse,
  UserResponse,
  UserListResponse,
  AdminDashboard,
  SystemStats,
  AIConfigResponse,
  AIConfigListResponse,
  AIConfigCreate,
  ConversationListResponse,
  MessageListResponse,
  KnowledgeSourceListResponse,
  KnowledgeChunkListResponse,
  MemoryListResponse,
  RetentionPolicyResponse,
  ToolResponse,
  ToolListResponse,
  ToolExecutionListResponse,
  ToolTestResponse,
  ObservabilityLogListResponse,
  UsageMetricsListResponse,
  AnalyticsSummaryResponse,
  APIKeyListResponse,
  APIKeyCreateResponse,
} from '@/types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ─── Axios Instance ────────────────────────────────────────────────────────────

const api: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

// ─── Request interceptor – inject JWT ─────────────────────────────────────────

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token =
    typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ─── Response interceptor – auto-refresh on 401 ───────────────────────────────

let isRefreshing = false;
let refreshQueue: Array<(token: string) => void> = [];

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          refreshQueue.push((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(api(originalRequest));
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) throw new Error('No refresh token');

        const { data } = await axios.post<TokenResponse>(
          `${BASE_URL}/api/v1/auth/refresh`,
          { refresh_token: refreshToken }
        );

        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);

        refreshQueue.forEach((cb) => cb(data.access_token));
        refreshQueue = [];

        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        return Promise.reject(error);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const authApi = {
  login: async (email: string, password: string): Promise<TokenResponse> => {
    const { data } = await api.post<TokenResponse>('/auth/login', {
      email,
      password,
    });
    return data;
  },

  refresh: async (refreshToken: string): Promise<TokenResponse> => {
    const { data } = await api.post<TokenResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return data;
  },

  me: async (): Promise<UserResponse> => {
    const { data } = await api.get<UserResponse>('/auth/me');
    return data;
  },

  changePassword: async (currentPassword: string, newPassword: string): Promise<void> => {
    await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  },
};

// ─── Users ────────────────────────────────────────────────────────────────────

export const usersApi = {
  list: async (page = 1, pageSize = 20): Promise<UserListResponse> => {
    const { data } = await api.get<UserListResponse>('/users', {
      params: { page, page_size: pageSize },
    });
    return data;
  },

  create: async (payload: {
    email: string;
    username: string;
    password: string;
    full_name?: string;
    role?: string;
  }): Promise<UserResponse> => {
    const { data } = await api.post<UserResponse>('/users', payload);
    return data;
  },

  update: async (
    id: string,
    payload: Partial<{
      email: string;
      username: string;
      full_name: string;
      role: string;
      is_active: boolean;
    }>
  ): Promise<UserResponse> => {
    const { data } = await api.patch<UserResponse>(`/users/${id}`, payload);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/users/${id}`);
  },
};

// ─── API Keys ─────────────────────────────────────────────────────────────────

export const apiKeysApi = {
  list: async (): Promise<APIKeyListResponse> => {
    const { data } = await api.get<APIKeyListResponse>('/auth/api-keys');
    return data;
  },

  create: async (payload: {
    name: string;
    description?: string;
    permissions?: string[];
    rate_limit?: number;
    expires_at?: string;
  }): Promise<APIKeyCreateResponse> => {
    const { data } = await api.post<APIKeyCreateResponse>('/auth/api-keys', payload);
    return data;
  },

  revoke: async (id: string): Promise<void> => {
    await api.delete(`/auth/api-keys/${id}`);
  },
};

// ─── Admin ────────────────────────────────────────────────────────────────────

export const adminApi = {
  dashboard: async (): Promise<AdminDashboard> => {
    const { data } = await api.get<AdminDashboard>('/admin/dashboard');
    return data;
  },

  stats: async (): Promise<SystemStats> => {
    const { data } = await api.get<SystemStats>('/admin/stats');
    return data;
  },

  listAIConfigs: async (): Promise<AIConfigListResponse> => {
    const { data } = await api.get<AIConfigListResponse>('/admin/ai-configs');
    return data;
  },

  createAIConfig: async (payload: AIConfigCreate): Promise<AIConfigResponse> => {
    const { data } = await api.post<AIConfigResponse>('/admin/ai-configs', payload);
    return data;
  },

  updateAIConfig: async (
    id: string,
    payload: Partial<AIConfigCreate & { is_active: boolean }>
  ): Promise<AIConfigResponse> => {
    const { data } = await api.patch<AIConfigResponse>(`/admin/ai-configs/${id}`, payload);
    return data;
  },

  deleteAIConfig: async (id: string): Promise<void> => {
    await api.delete(`/admin/ai-configs/${id}`);
  },

  flushCache: async (): Promise<{ message: string }> => {
    const { data } = await api.post<{ message: string }>('/admin/cache/flush');
    return data;
  },
};

// ─── Conversations ────────────────────────────────────────────────────────────

export const conversationsApi = {
  list: async (params: {
    page?: number;
    page_size?: number;
    status?: string;
    started_after?: string;
    started_before?: string;
  }): Promise<ConversationListResponse> => {
    const { data } = await api.get<ConversationListResponse>('/conversations', { params });
    return data;
  },

  getMessages: async (conversationId: string): Promise<MessageListResponse> => {
    const { data } = await api.get<MessageListResponse>(
      `/conversations/${conversationId}/messages`
    );
    return data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/conversations/${id}`);
  },
};

// ─── Knowledge ────────────────────────────────────────────────────────────────

export const knowledgeApi = {
  list: async (params: {
    page?: number;
    page_size?: number;
    status?: string;
    type?: string;
    search?: string;
  }): Promise<KnowledgeSourceListResponse> => {
    const { data } = await api.get<KnowledgeSourceListResponse>('/knowledge/sources', {
      params,
    });
    return data;
  },

  uploadFile: async (file: File, meta: { name: string; mode?: string; auto_approve?: boolean }): Promise<{ id: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', meta.name);
    if (meta.mode) formData.append('mode', meta.mode);
    if (meta.auto_approve !== undefined)
      formData.append('auto_approve', String(meta.auto_approve));

    const { data } = await api.post<{ id: string }>('/knowledge/sources/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  addUrl: async (payload: { name: string; url: string; mode?: string }): Promise<{ id: string }> => {
    const { data } = await api.post<{ id: string }>('/knowledge/sources', {
      ...payload,
      type: 'url',
    });
    return data;
  },

  approve: async (id: string): Promise<void> => {
    await api.post(`/knowledge/sources/${id}/approve`, { approved: true });
  },

  reject: async (id: string, reason: string): Promise<void> => {
    await api.post(`/knowledge/sources/${id}/approve`, {
      approved: false,
      reason,
    });
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/knowledge/sources/${id}`);
  },

  getChunks: async (sourceId: string): Promise<KnowledgeChunkListResponse> => {
    const { data } = await api.get<KnowledgeChunkListResponse>(
      `/knowledge/sources/${sourceId}/chunks`
    );
    return data;
  },
};

// ─── Memory ───────────────────────────────────────────────────────────────────

export const memoryApi = {
  list: async (params: {
    page?: number;
    page_size?: number;
    type?: string;
    session_id?: string;
    min_importance?: number;
  }): Promise<MemoryListResponse> => {
    const { data } = await api.get<MemoryListResponse>('/memory', { params });
    return data;
  },

  update: async (
    id: string,
    payload: {
      content?: string;
      importance_score?: number;
      is_active?: boolean;
    }
  ): Promise<{ id: string }> => {
    const { data } = await api.patch<{ id: string }>(`/memory/${id}`, payload);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/memory/${id}`);
  },

  listRetentionPolicies: async (): Promise<RetentionPolicyResponse[]> => {
    const { data } = await api.get<RetentionPolicyResponse[]>('/memory/retention-policies');
    return data;
  },

  createRetentionPolicy: async (payload: {
    name: string;
    type: string;
    max_count?: number;
    ttl_days?: number;
    min_importance?: number;
    auto_decay?: boolean;
    decay_formula?: string;
    description?: string;
  }): Promise<RetentionPolicyResponse> => {
    const { data } = await api.post<RetentionPolicyResponse>(
      '/memory/retention-policies',
      payload
    );
    return data;
  },
};

// ─── Tools ────────────────────────────────────────────────────────────────────

export const toolsApi = {
  list: async (params: {
    page?: number;
    page_size?: number;
    is_active?: boolean;
  }): Promise<ToolListResponse> => {
    const { data } = await api.get<ToolListResponse>('/tools', { params });
    return data;
  },

  get: async (id: string): Promise<ToolResponse> => {
    const { data } = await api.get<ToolResponse>(`/tools/${id}`);
    return data;
  },

  create: async (payload: {
    name: string;
    display_name?: string;
    description: string;
    type: string;
    schema: Record<string, unknown>;
    endpoint_url?: string;
    method?: string;
    timeout_seconds?: number;
    max_retries?: number;
    auth_type?: string;
    auth_config?: Record<string, unknown>;
    default_headers?: Record<string, string>;
    requires_approval?: boolean;
    tags?: string[];
  }): Promise<ToolResponse> => {
    const { data } = await api.post<ToolResponse>('/tools', payload);
    return data;
  },

  update: async (
    id: string,
    payload: Partial<{
      display_name: string;
      description: string;
      schema: Record<string, unknown>;
      endpoint_url: string;
      method: string;
      is_active: boolean;
      auth_type: string;
      auth_config: Record<string, unknown>;
    }>
  ): Promise<ToolResponse> => {
    const { data } = await api.patch<ToolResponse>(`/tools/${id}`, payload);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/tools/${id}`);
  },

  test: async (id: string, args: Record<string, unknown>): Promise<ToolTestResponse> => {
    const { data } = await api.post<ToolTestResponse>(`/tools/${id}/test`, {
      arguments: args,
    });
    return data;
  },

  executions: async (
    id: string,
    page = 1,
    pageSize = 20
  ): Promise<ToolExecutionListResponse> => {
    const { data } = await api.get<ToolExecutionListResponse>(
      `/tools/${id}/executions`,
      { params: { page, page_size: pageSize } }
    );
    return data;
  },

  allExecutions: async (page = 1, pageSize = 20): Promise<ToolExecutionListResponse> => {
    const { data } = await api.get<ToolExecutionListResponse>('/tools/executions', {
      params: { page, page_size: pageSize },
    });
    return data;
  },
};

// ─── Analytics ────────────────────────────────────────────────────────────────

export const analyticsApi = {
  summary: async (params: {
    start_date: string;
    end_date: string;
    granularity?: string;
  }): Promise<AnalyticsSummaryResponse> => {
    const { data } = await api.get<AnalyticsSummaryResponse>('/analytics/summary', {
      params,
    });
    return data;
  },

  metrics: async (params: {
    start_date: string;
    end_date: string;
    page?: number;
    page_size?: number;
  }): Promise<UsageMetricsListResponse> => {
    const { data } = await api.get<UsageMetricsListResponse>('/analytics/metrics', {
      params,
    });
    return data;
  },

  logs: async (params: {
    page?: number;
    page_size?: number;
    event_type?: string;
    model_selected?: string;
    provider_selected?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<ObservabilityLogListResponse> => {
    const { data } = await api.get<ObservabilityLogListResponse>('/analytics/logs', {
      params,
    });
    return data;
  },
};

export default api;
