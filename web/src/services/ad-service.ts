import request from '@/utils/request';

export interface ResponseData<T = any> {
  code: number;
  message: string;
  data: T;
}

export interface AdCampaignItem {
  id: string;
  name: string;
  product_name: string;
  description: string;
  advertisement_text: string;
  landing_url: string;
  target_categories: string[];
  keywords: string[];
  daily_budget: number;
  total_budget: number;
  spent_today: number;
  total_spent: number;
  pricing_model: 'cpc' | 'cpm';
  bid_amount: number;
  priority?: number;
  status: 'active' | 'paused' | 'completed' | 'archived';
  moderation_status: 'pending' | 'approved' | 'rejected';
  moderation_note?: string;
  impressions: number;
  clicks: number;
  ctr: number;
  created_at?: number;
}

export interface AdvertiserDashboardData {
  advertiser_id: string;
  company_name: string;
  balance: number;
  currency: string;
  active_campaigns: number;
  total_campaigns: number;
  total_impressions: number;
  total_clicks: number;
  total_spent: number;
  ctr: number;
  campaigns: AdCampaignItem[];
}

export interface AdTransactionItem {
  id: string;
  amount: number;
  type: string;
  description: string;
  reference_id: string;
  created_at: number;
}

export interface AdminAdsOverview {
  total_advertisers: number;
  total_campaigns: number;
  active_campaigns: number;
  pending_moderation: number;
  total_impressions: number;
  total_clicks: number;
  total_revenue: number;
  network_ctr: number;
}

export interface AdminAdsSettings {
  ads_enabled: boolean;
  ads_for_free_users: boolean;
  platform_branding_enabled: boolean;
  llm_prompt_enabled: boolean;
  targeting_enabled: boolean;
  billing_enabled: boolean;
  app_url: string;
  brand_name: string;
  max_impressions_per_user_day: number;
}

const adService = {
  // Advertiser Portal
  getDashboard: () => request.get<ResponseData<AdvertiserDashboardData>>('/ads/dashboard'),
  listCampaigns: () => request.get<ResponseData<AdCampaignItem[]>>('/ads/campaigns'),
  createCampaign: (data: Partial<AdCampaignItem>) =>
    request.post<ResponseData<{ id: string; name: string; status: string }>>('/ads/campaigns', { data }),
  updateCampaign: (id: string, data: Partial<AdCampaignItem>) =>
    request.put<ResponseData<{ id: string; name: string; status: string }>>(`/ads/campaigns/${id}`, { data }),
  toggleCampaignStatus: (id: string) =>
    request.post<ResponseData<{ id: string; status: string }>>(`/ads/campaigns/${id}/toggle_status`),
  deleteCampaign: (id: string) =>
    request.delete<ResponseData<boolean>>(`/ads/campaigns/${id}`),
  getCampaignAnalytics: (id: string) =>
    request.get<ResponseData<any>>(`/ads/campaigns/${id}/analytics`),

  // Billing
  depositFunds: (amount: number, description: string = 'Top-Up') =>
    request.post<ResponseData<{ balance: number; currency: string }>>('/ads/billing/deposit', {
      data: { amount, description },
    }),
  listTransactions: () =>
    request.get<ResponseData<AdTransactionItem[]>>('/ads/billing/transactions'),

  // Admin Controls
  getAdminOverview: () => request.get<ResponseData<AdminAdsOverview>>('/ads/admin/overview'),
  getAdminModerationQueue: () => request.get<ResponseData<any[]>>('/ads/admin/moderation'),
  approveCampaign: (id: string) => request.post<ResponseData<any>>(`/ads/admin/moderation/${id}/approve`),
  rejectCampaign: (id: string, note?: string) =>
    request.post<ResponseData<any>>(`/ads/admin/moderation/${id}/reject`, { data: { note } }),
  getAdminSettings: () => request.get<ResponseData<AdminAdsSettings>>('/ads/admin/settings'),
  updateAdminSettings: (data: Partial<AdminAdsSettings>) =>
    request.post<ResponseData<boolean>>('/ads/admin/settings', { data }),

  // Attribution & Watermark Analytics
  getAttributionStats: () => request.get<ResponseData<AttributionStatsData>>('/ads/attribution/stats'),
};

export interface AttributionStatsData {
  total_visits: number;
  unique_visitors: number;
  total_signups: number;
  conversion_rate: number;
  utm_link: string;
  recent_visits: Array<{
    id: string;
    utm_source: string;
    utm_medium: string;
    utm_campaign: string;
    utm_content?: string;
    created_at: number;
  }>;
}

export default adService;
