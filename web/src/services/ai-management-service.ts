import request from '@/utils/request';

export interface ResponseData<T = any> {
  code: number;
  message: string;
  data: T;
}

export interface SubscriptionPlanItem {
  id: string;
  name: string;
  monthly_token_limit: number;
  limit_mode: 'shared' | 'per_model';
  max_storage_gb: number;
  max_datasets: number;
  max_agents: number;
  allow_custom_providers: boolean;
  allow_custom_models: boolean;
  allow_custom_endpoints: boolean;
  allow_private_servers: boolean;
  default_llm_id?: string;
  default_embd_id?: string;
  status: string;
}

export interface AIModelItem {
  id: string;
  provider: string;
  model_name: string;
  model_type: 'CHAT' | 'EMBEDDING' | 'RERANK' | 'IMAGE2TEXT' | 'SPEECH2TEXT' | 'TTS' | 'OCR';
  base_url?: string;
  api_key?: string;
  enabled: boolean;
  is_global: boolean;
  is_custom: boolean;
}

export interface SubscriptionAIPolicyItem {
  id: string;
  plan_id: string;
  model_id: string;
  model_token_limit: number;
  is_default_llm: boolean;
  is_default_embd: boolean;
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
}

export interface UserAIUsageSummary {
  plan: SubscriptionPlanItem;
  period: string;
  total_used: number;
  monthly_limit: number;
  percentage: number;
  breakdown: ModelUsageBreakdown[];
  allowed_models: SubscriptionAIPolicyItem[];
}

export const getAdminPlans = () =>
  request.get<ResponseData<SubscriptionPlanItem[]>>('/v1/admin/ai/plans');

export const updateAdminPlan = (planId: string, data: Partial<SubscriptionPlanItem>) =>
  request.put<ResponseData<boolean>>(`/v1/admin/ai/plans/${planId}`, { data });

export const getAdminModels = () =>
  request.get<ResponseData<AIModelItem[]>>('/v1/admin/ai/models');

export const saveAdminModel = (data: Partial<AIModelItem>) =>
  request.post<ResponseData<AIModelItem>>('/v1/admin/ai/models', { data });

export const deleteAdminModel = (modelId: string) =>
  request.delete<ResponseData<boolean>>(`/v1/admin/ai/models/${encodeURIComponent(modelId)}`);

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

export const getUserAiUsage = () =>
  request.get<ResponseData<UserAIUsageSummary>>('/v1/user/ai/usage');

export const getUserAllowedModels = () =>
  request.get<ResponseData<{ plan: SubscriptionPlanItem; models: SubscriptionAIPolicyItem[]; is_superuser?: boolean; can_add_custom?: boolean }>>('/v1/user/ai/allowed-models');
