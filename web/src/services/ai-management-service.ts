import request from '@/utils/request';

export interface ResponseData<T = any> {
  code: number;
  message: string;
  data: T;
}

export interface GlobalInstanceStats {
  instance_id: string;
  name: string;
  status: string;
  total_users: number;
  total_models: number;
  total_providers: number;
  byok_connections: number;
  default_chat_model?: string;
  default_free_model_id?: string;
  default_plus_model_id?: string;
  default_pro_model_id?: string;
  default_embd_id?: string;
  default_rerank_id?: string;
  default_image2text_model?: string;
  default_asr_model?: string;
  default_tts_model?: string;
  byok_enabled: boolean;
  max_byok_models: number;
  byok_token_limit: number;
  byok_request_limit: number;
  create_time?: number;
  update_time?: number;
}

export interface SystemDefaultModels {
  default_chat_model?: string;
  default_free_model_id?: string;
  default_plus_model_id?: string;
  default_pro_model_id?: string;
  default_embd_id?: string;
  default_rerank_id?: string;
  default_image2text_model?: string;
  default_asr_model?: string;
  default_tts_model?: string;
}

export interface AIProviderItem {
  id: string;
  provider_name: string;
  base_url?: string;
  api_key_masked?: string;
  has_api_key: boolean;
  organization?: string;
  api_version?: string;
  status: string;
  is_global: boolean;
}

export interface SubscriptionPlanItem {
  id: string;
  name: string;
  daily_token_limit?: number;
  monthly_token_limit: number;
  daily_request_limit?: number;
  monthly_request_limit?: number;
  requests_per_minute?: number;
  max_tokens_per_request?: number;
  limit_mode: 'shared' | 'per_model';
  max_storage_gb: number;
  max_datasets: number;
  max_agents: number;
  allow_custom_providers: boolean;
  allow_custom_models: boolean;
  allow_custom_endpoints: boolean;
  allow_private_servers: boolean;
  allow_byok?: boolean;
  max_byok_models?: number;
  default_llm_id?: string;
  default_embd_id?: string;
  default_rerank_id?: string;
  status: string;
}

export interface AIModelItem {
  id: string;
  provider: string;
  model_name: string;
  model_type: 'CHAT' | 'EMBEDDING' | 'RERANK' | 'IMAGE2TEXT' | 'SPEECH2TEXT' | 'TTS' | 'OCR';
  base_url?: string;
  api_key?: string;
  api_key_masked?: string;
  input_token_price?: number;
  output_token_price?: number;
  max_tokens?: number;
  enabled: boolean;
  is_global: boolean;
  is_custom: boolean;
  owner_user_id?: string;
  status?: string;
  allowed_plans?: string[];
}

export interface SubscriptionAIPolicyItem {
  id: string;
  plan_id: string;
  model_id: string;
  model_token_limit: number;
  is_default_llm: boolean;
  is_default_embd: boolean;
  is_default_rerank?: boolean;
  enabled: boolean;
}

export interface UserTokenLimitItem {
  user_id: string;
  monthly_token_limit: number;
  enabled: boolean;
}

export interface ModelUsageBreakdown {
  model_id: string;
  model_type: string;
  tokens_used: number;
  cost?: number;
}

export interface UserAIUsageSummary {
  plan: SubscriptionPlanItem;
  period: string;
  date?: string;
  monthly_used: number;
  monthly_limit: number;
  total_used?: number;
  daily_used?: number;
  daily_limit?: number;
  percentage: number;
  breakdown: ModelUsageBreakdown[];
  allowed_models: SubscriptionAIPolicyItem[];
  global_instance_id: string;
}

export interface AdminAnalyticsSummary {
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_cost: number;
  active_users: number;
}

export interface AdminAnalyticsData {
  period: string;
  global_instance_id: string;
  summary: AdminAnalyticsSummary;
  by_subscription: Array<{ subscription_id: string; requests: number; tokens: number; cost: number }>;
  by_model: Array<{ model_id: string; model_type: string; requests: number; input_tokens: number; output_tokens: number; total_tokens: number; cost: number }>;
  by_provider: Array<{ provider_id: string; requests: number; tokens: number; cost: number }>;
  top_users: Array<{ user_id: string; email?: string; nickname?: string; subscription_id: string; requests: number; tokens: number; cost: number }>;
  byok_stats: { total_byok_models: number; active_byok_models: number };
}

export interface AIAuditLogItem {
  id: string;
  user_id: string;
  user_email?: string;
  user_nickname?: string;
  action: string;
  target_type: string;
  target_id?: string;
  details_parsed?: any;
  create_time: number;
}

// Global Instance & System Default Models
export const getAdminInstance = () =>
  request.get<ResponseData<GlobalInstanceStats>>('/v1/admin/ai/instance');

export const updateAdminInstance = (data: Partial<GlobalInstanceStats>) =>
  request.put<ResponseData<GlobalInstanceStats>>('/v1/admin/ai/instance', { data });

export const getAdminDefaultModels = () =>
  request.get<ResponseData<SystemDefaultModels>>('/v1/admin/ai/defaults');

export const updateAdminDefaultModels = (data: SystemDefaultModels) =>
  request.put<ResponseData<GlobalInstanceStats>>('/v1/admin/ai/defaults', { data });

// Providers
export const getAdminProviders = () =>
  request.get<ResponseData<AIProviderItem[]>>('/v1/admin/ai/providers');

export const getAdminAvailableProviders = () =>
  request.get<ResponseData<{ name: string; model_types: string[]; url: Record<string, string> }[]>>(
    '/v1/admin/ai/providers/available'
  );

export const verifyAdminProvider = (data: { provider_name: string; api_key: string; base_url?: string; extra?: any }) =>
  request.post<ResponseData<{ success: boolean; message: string; available_models: any[]; count: number }>>(
    '/v1/admin/ai/providers/verify',
    { data }
  );

export const saveAdminProvider = (data: Partial<AIProviderItem> & { api_key?: string }) =>
  request.post<ResponseData<AIProviderItem>>('/v1/admin/ai/providers', { data });

export const deleteAdminProvider = (providerId: string) =>
  request.delete<ResponseData<boolean>>(`/v1/admin/ai/providers/${encodeURIComponent(providerId)}`);

// Models & Pricing
export const getAdminModels = () =>
  request.get<ResponseData<AIModelItem[]>>('/v1/admin/ai/models');

export const saveAdminModel = (data: Partial<AIModelItem> & { allowed_plans?: string[] }) =>
  request.post<ResponseData<AIModelItem>>('/v1/admin/ai/models', { data });

export const deleteAdminModel = (modelId: string) =>
  request.delete<ResponseData<boolean>>(`/v1/admin/ai/models/${encodeURIComponent(modelId)}`);

// Plans & Policies
export const getAdminPlans = () =>
  request.get<ResponseData<SubscriptionPlanItem[]>>('/v1/admin/ai/plans');

export const updateAdminPlan = (planId: string, data: Partial<SubscriptionPlanItem>) =>
  request.put<ResponseData<boolean>>(`/v1/admin/ai/plans/${planId}`, { data });

export const getAdminPolicies = (planId?: string) =>
  request.get<ResponseData<SubscriptionAIPolicyItem[]>>('/v1/admin/ai/policies', {
    params: { plan_id: planId },
  });

export const updateAdminPolicies = (planId: string, policies: Partial<SubscriptionAIPolicyItem>[]) =>
  request.put<ResponseData<boolean>>('/v1/admin/ai/policies', {
    data: {
      plan_id: planId,
      policies,
    },
  });

// Analytics & Logs
export const getAdminAnalytics = (period?: string) =>
  request.get<ResponseData<AdminAnalyticsData>>('/v1/admin/ai/metrics', {
    params: { period },
  });

export const getAdminAuditLogs = (params?: { limit?: number; offset?: number; action?: string; target_type?: string }) =>
  request.get<ResponseData<{ items: AIAuditLogItem[]; total: number }>>('/v1/admin/ai/audit-logs', { params });

export const getAdminByokStats = () =>
  request.get<ResponseData<{ total_byok_models: number; active_byok_models: number; locked_byok_models: number; byok_users_count: number }>>('/v1/admin/ai/byok-stats');

// User Limits
export const getAdminUserLimit = (userId: string) =>
  request.get<ResponseData<UserTokenLimitItem>>(`/v1/admin/ai/user-limits/${userId}`);

export const setAdminUserLimit = (userId: string, limit: number, enabled: boolean = true) =>
  request.put<ResponseData<boolean>>('/v1/admin/ai/user-limits', {
    data: {
      user_id: userId,
      monthly_token_limit: limit,
      enabled,
    },
  });

// User Endpoints
export const getUserAiUsage = () =>
  request.get<ResponseData<UserAIUsageSummary>>('/v1/user/ai/usage');

export const getUserAllowedModels = () =>
  request.get<ResponseData<{
    plan: SubscriptionPlanItem;
    models: SubscriptionAIPolicyItem[];
    byok_models?: AIModelItem[];
    is_superuser?: boolean;
    can_add_custom?: boolean;
    global_instance_id?: string;
  }>>('/v1/user/ai/allowed-models');

export const getUserByok = () =>
  request.get<ResponseData<AIModelItem[]>>('/v1/user/ai/byok');

export const saveUserByok = (data: Partial<AIModelItem> & { api_key?: string }) =>
  request.post<ResponseData<AIModelItem>>('/v1/user/ai/byok', { data });

export const deleteUserByok = (modelId: string) =>
  request.delete<ResponseData<boolean>>(`/v1/user/ai/byok/${encodeURIComponent(modelId)}`);
