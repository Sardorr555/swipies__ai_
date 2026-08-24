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
  target_regions?: string[];
  target_cities?: string[];
  daily_budget: number;
  total_budget: number;
  spent_today: number;
  total_spent: number;
  pricing_model: 'cpc' | 'cpm' | 'cpa';
  bid_amount: number;
  target_cpa?: number;
  conversions_count?: number;
  conversion_rate?: number;
  total_conversion_value?: number;
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

  // A/B Testing & Variants
  getCampaignVariants: (campaignId: string) =>
    request.get<ResponseData<AdVariantItem[]>>(`/ads/campaigns/${campaignId}/variants`),
  createCampaignVariant: (campaignId: string, data: { name: string; advertisement_text: string; landing_url?: string; weight?: number; is_active?: boolean }) =>
    request.post<ResponseData<AdVariantItem>>(`/ads/campaigns/${campaignId}/variants`, { data }),
  updateCampaignVariant: (campaignId: string, variantId: string, data: Partial<AdVariantItem>) =>
    request.put<ResponseData<AdVariantItem>>(`/ads/campaigns/${campaignId}/variants/${variantId}`, { data }),
  toggleCampaignVariant: (campaignId: string, variantId: string) =>
    request.put<ResponseData<{ id: string; is_active: boolean }>>(`/ads/campaigns/${campaignId}/variants/${variantId}/toggle`),
  deleteCampaignVariant: (campaignId: string, variantId: string) =>
    request.delete<ResponseData<{ deleted: boolean }>>(`/ads/campaigns/${campaignId}/variants/${variantId}`),

  // Analytics & Charts
  getAdvertiserTimeline: (days: number = 14) =>
    request.get<ResponseData<TimelineAnalyticsData>>(`/ads/analytics/timeline?days=${days}`),
  getCampaignAnalyticsDetailed: (campaignId: string, days: number = 14) =>
    request.get<ResponseData<CampaignDetailedAnalyticsData>>(`/ads/campaigns/${campaignId}/analytics/detailed?days=${days}`),
  getAdminOverviewTimeline: (days: number = 14) =>
    request.get<ResponseData<AdminTimelineData>>(`/ads/admin/analytics/overview-timeline?days=${days}`),

  // Admin Controls
  getAdminOverview: () => request.get<ResponseData<AdminAdsOverview>>('/ads/admin/overview'),
  getAdminModerationQueue: () => request.get<ResponseData<any[]>>('/ads/admin/moderation'),
  approveCampaign: (id: string) => request.post<ResponseData<any>>(`/ads/admin/moderation/${id}/approve`),
  rejectCampaign: (id: string, note?: string) =>
    request.post<ResponseData<any>>(`/ads/admin/moderation/${id}/reject`, { data: { note } }),
  getAdminSettings: () => request.get<ResponseData<AdminAdsSettings>>('/ads/admin/settings'),
  updateAdminSettings: (data: Partial<AdminAdsSettings>) =>
    request.post<ResponseData<boolean>>('/ads/admin/settings', { data }),

  // Conversion Pixel & Smart Bidding
  getPixelSnippet: () => request.get<ResponseData<PixelSnippetData>>('/ads/pixel/snippet'),
  testPixelTrack: (data: { pixel_id: string; event: string; value?: number; order_id?: string }) =>
    request.post<ResponseData<any>>('/ads/pixel/track', { data }),

  // Attribution & Watermark Analytics
  getAttributionStats: () => request.get<ResponseData<AttributionStatsData>>('/ads/attribution/stats'),

  // Geo Targeting
  getGeoRegions: () => request.get<ResponseData<GeoRegionItem[]>>('/ads/geo/regions'),

  // Recurring Subscriptions & Saved Cards
  getUserSubscription: () =>
    request.get<ResponseData<UserSubscriptionData>>('/ads/billing/subscription'),
  cancelSubscription: (immediate: boolean = false) =>
    request.post<ResponseData<{ success: boolean; status: string; cancel_at_period_end?: boolean; valid_until?: number }>>('/ads/billing/subscription/cancel', { data: { immediate } }),
  resumeSubscription: () =>
    request.post<ResponseData<{ success: boolean; status: string; auto_renew: boolean; next_billing_time: number }>>('/ads/billing/subscription/resume'),
  getSavedPaymentMethods: () =>
    request.get<ResponseData<SavedPaymentMethodItem[]>>('/ads/billing/payment-methods'),
  deleteSavedPaymentMethod: (cardId: string) =>
    request.delete<ResponseData<{ deleted: boolean }>>(`/ads/billing/payment-methods/${cardId}`),
  adminProcessRenewals: () =>
    request.post<ResponseData<{ processed: number; renewed: number; failed: number }>>('/ads/admin/subscriptions/process-renewals'),
};

export interface PixelSnippetData {
  pixel_id: string;
  snippet: string;
  example_usage: string;
}

export interface GeoRegionItem {
  id: string;
  name_ru: string;
  name_uz: string;
  name_en: string;
}

export interface SavedPaymentMethodItem {
  id: string;
  card_pan_masked: string;
  card_expiry: string;
  card_holder?: string;
  card_type: string;
  is_default: boolean;
  create_time: number;
}

export interface UserSubscriptionData {
  id: string;
  user_id?: string;
  tenant_id?: string;
  plan_id: string;
  status: string;
  auto_renew: boolean;
  price_usd: number;
  current_period_start: number;
  current_period_end: number;
  next_billing_time: number;
  cancel_at_period_end: boolean;
  retry_count?: number;
  card?: {
    id: string;
    card_pan_masked: string;
    card_type: string;
    card_expiry: string;
  };
}

export interface AdVariantItem {
  id: string;
  campaign_id: string;
  name: string;
  advertisement_text: string;
  landing_url?: string;
  impressions: number;
  clicks: number;
  ctr: number;
  weight: number;
  is_active: boolean;
  create_time?: number;
}

export interface DailyTimelinePoint {
  date: string;
  impressions: number;
  clicks: number;
  spend?: number;
  revenue?: number;
  ctr: number;
}

export interface TimelineAnalyticsData {
  days: number;
  total_impressions: number;
  total_clicks: number;
  total_spend: number;
  ctr: number;
  timeline: DailyTimelinePoint[];
  languages: Record<string, number>;
  models: Record<string, number>;
  devices: Record<string, number>;
  regions?: Record<string, number>;
}

export interface CampaignDetailedAnalyticsData extends TimelineAnalyticsData {
  campaign_id: string;
  campaign_name: string;
  product_name: string;
  status: string;
}

export interface AdminTimelineData {
  days: number;
  timeline: DailyTimelinePoint[];
  total_network_impressions: number;
  total_network_clicks: number;
  total_network_revenue: number;
  regions?: Record<string, number>;
}

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
