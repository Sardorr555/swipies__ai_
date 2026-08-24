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
  negative_keywords?: string[];
  target_languages?: string[];
  target_models?: string[];
  target_countries?: string[];
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

export interface PromoCodeItem {
  id: string;
  code: string;
  discount_type: string;
  discount_value: number;
  applies_to: string;
  plan_id?: string;
  max_uses: number;
  used_count: number;
  is_active: boolean;
  expires_at?: number;
  created_at?: number;
}

export interface AdminAdsOverview {
  total_advertisers: number;
  active_advertisers: number;
  total_campaigns: number;
  active_campaigns: number;
  pending_moderation: number;
  network_impressions_today: number;
  network_clicks_today: number;
  network_ctr_today: number;
  network_revenue_today: number;
  total_network_revenue: number;
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

  // AI Ad Creator Assistant
  generateCopy: (data: { product_name: string; landing_url?: string; description?: string; lang?: string }) =>
    request.post<ResponseData<{
      ad_copy_variations: string[];
      recommended_keywords: string[];
      recommended_negative_keywords: string[];
      recommended_categories: string[];
      recommended_bid: number;
    }>>('/ads/campaigns/generate-copy', { data }),

  // Billing
  depositFunds: (amount: number, description: string = 'Top-Up') =>
    request.post<ResponseData<{ balance: number; currency: string }>>('/ads/billing/deposit', {
      data: { amount, description },
    }),
  listTransactions: () =>
    request.get<ResponseData<AdTransactionItem[]>>('/ads/billing/transactions'),

  // Promo Codes
  validatePromo: (data: { code: string; purpose: string; amount_usd: number; plan_id?: string }) =>
    request.post<ResponseData<{
      promo_code_id: string;
      code: string;
      discount_type: string;
      discount_value: number;
      discount_usd: number;
      bonus_usd: number;
      original_amount_usd: number;
      final_amount_usd: number;
    }>>('/ads/promo/validate', { data }),
  adminListPromoCodes: () => request.get<ResponseData<PromoCodeItem[]>>('/ads/admin/promo-codes'),
  adminCreatePromoCode: (data: Partial<PromoCodeItem> & { expires_days?: number }) =>
    request.post<ResponseData<{ id: string; code: string }>>('/ads/admin/promo-codes', { data }),
  adminTogglePromoCode: (id: string) => request.put<ResponseData<{ id: string; is_active: boolean }>>(`/ads/admin/promo-codes/${id}/toggle`),
  adminDeletePromoCode: (id: string) => request.delete<ResponseData<boolean>>(`/ads/admin/promo-codes/${id}`),

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
