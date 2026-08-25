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
  bidding_strategy?: 'manual_cpc' | 'enhanced_cpc' | 'target_cpa' | 'maximize_conversions';
  target_cpa?: number;
  schedule_timezone?: string;
  schedule_config?: ScheduleConfig;
  dco_enabled?: boolean;
  dco_config?: DcoConfig;
  conversions_count?: number;
  conversion_rate?: number;
  total_conversion_value?: number;
  frequency_cap_impressions?: number;
  frequency_cap_hours?: number;
  target_audience_segment_ids?: string[];
  exclude_audience_segment_ids?: string[];
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

  // AI Campaign Optimizer & Copilot
  getAdvertiserInsights: () =>
    request.get<ResponseData<AdvertiserInsightsData>>('/ads/insights'),
  getCampaignInsights: (campaignId: string) =>
    request.get<ResponseData<CampaignInsightItem[]>>(`/ads/campaigns/${campaignId}/insights`),
  applyCampaignInsight: (campaignId: string, insightType: string, actionPayload: any) =>
    request.post<ResponseData<{ success: boolean; message: string }>>(`/ads/campaigns/${campaignId}/apply-insight`, {
      data: { insight_type: insightType, action_payload: actionPayload },
    }),

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
  // Team Collaboration & Granular Permissions
  getTeamMembers: () =>
    request.get<ResponseData<TeamMemberItem[]>>('/ads/team'),
  inviteTeamMember: (data: { email: string; role: string }) =>
    request.post<ResponseData<TeamMemberItem>>('/ads/team/invite', { data }),
  updateTeamMemberRole: (memberId: string, role: string) =>
    request.put<ResponseData<TeamMemberItem>>(`/ads/team/${memberId}/role`, { data: { role } }),
  deleteTeamMember: (memberId: string) =>
    request.delete<ResponseData<{ deleted: boolean }>>(`/ads/team/${memberId}`),

  // Notification Center & Multi-Channel Alerts
  getNotifications: (params?: { limit?: number; unread_only?: boolean }) =>
    request.get<ResponseData<NotificationData>>('/ads/notifications', { params }),
  markNotificationsRead: (data?: { notification_id?: string; all?: boolean }) =>
    request.post<ResponseData<{ updated_count: number }>>('/ads/notifications/read', { data }),
  getNotificationSettings: () =>
    request.get<ResponseData<NotificationSettingsData>>('/ads/notifications/settings'),
  updateNotificationSettings: (data: Partial<NotificationSettingsData>) =>
    request.post<ResponseData<NotificationSettingsData>>('/ads/notifications/settings', { data }),
  sendTestNotification: (channel: string = 'all') =>
    request.post<ResponseData<NotificationItem>>('/ads/notifications/test', { data: { channel } }),

  // Audience Retargeting & Segments
  getAudienceSegments: () =>
    request.get<ResponseData<AudienceSegmentItem[]>>('/ads/audiences'),
  createAudienceSegment: (data: { name: string; description?: string; rule_type: string; rule_config?: any }) =>
    request.post<ResponseData<AudienceSegmentItem>>('/ads/audiences', { data }),
  deleteAudienceSegment: (segmentId: string) =>
    request.delete<ResponseData<{ deleted: boolean }>>(`/ads/audiences/${segmentId}`),
  addAudienceMember: (segmentId: string, data: { user_id?: string; anonymous_id?: string; source_event?: string }) =>
    request.post<ResponseData<any>>(`/ads/audiences/${segmentId}/members`, { data }),

  // Publisher Monetization & Partner SDK
  getPublisherProfile: () =>
    request.get<ResponseData<PublisherProfileData>>('/ads/publisher'),
  regeneratePublisherKey: () =>
    request.post<ResponseData<{ api_key: string }>>('/ads/publisher/key/regenerate'),
  getPublisherPlacements: () =>
    request.get<ResponseData<PlacementItem[]>>('/ads/publisher/placements'),
  createPublisherPlacement: (data: { name: string; placement_type: string; domain_or_bot?: string; rev_share_rate?: number }) =>
    request.post<ResponseData<PlacementItem>>('/ads/publisher/placements', { data }),
  deletePublisherPlacement: (placementId: string) =>
    request.delete<ResponseData<{ deleted: boolean }>>(`/ads/publisher/placements/${placementId}`),
  getPublisherPayouts: () =>
    request.get<ResponseData<PublisherPayoutItem[]>>('/ads/publisher/payouts'),
  requestPublisherPayout: (data: { amount: number; destination_card: string; destination_holder?: string }) =>
    request.post<ResponseData<PublisherPayoutItem>>('/ads/publisher/payouts', { data }),
  // Anti-Fraud & IVT Protection
  getFraudOverview: () =>
    request.get<ResponseData<FraudOverviewData>>('/ads/fraud/overview'),
  getFraudBlacklist: () =>
    request.get<ResponseData<BlacklistEntryItem[]>>('/ads/fraud/blacklist'),
  addFraudBlacklist: (data: { ip_address: string; reason?: string; duration_hours?: number }) =>
    request.post<ResponseData<BlacklistEntryItem>>('/ads/fraud/blacklist', { data }),
  removeFraudBlacklist: (blacklistId: string) =>
    request.delete<ResponseData<{ deleted: boolean }>>(`/ads/fraud/blacklist/${blacklistId}`),

  // Smart Bidding & Dayparting
  getBiddingStrategies: () =>
    request.get<ResponseData<BiddingStrategyItem[]>>('/ads/bidding/strategies'),
  getCampaignBidding: (campaignId: string) =>
    request.get<ResponseData<CampaignBiddingInfo>>(`/ads/campaigns/${campaignId}/bidding`),
  updateCampaignBidding: (campaignId: string, data: Partial<CampaignBiddingInfo>) =>
    request.put<ResponseData<CampaignBiddingInfo>>(`/ads/campaigns/${campaignId}/bidding`, { data }),

  // Dynamic Creative Optimization (DCO) & Real-time Contextual Ad Insertion
  getCampaignDco: (campaignId: string) =>
    request.get<ResponseData<CampaignDcoInfo>>(`/ads/campaigns/${campaignId}/dco`),
  updateCampaignDco: (campaignId: string, data: { dco_enabled: boolean; dco_config: DcoConfig }) =>
    request.put<ResponseData<CampaignDcoInfo>>(`/ads/campaigns/${campaignId}/dco`, { data }),
  previewCampaignDco: (campaignId: string, data: DcoPreviewRequest) =>
    request.post<ResponseData<DcoPreviewResponse>>(`/ads/campaigns/${campaignId}/dco/preview`, { data }),
};

export interface DcoConfig {
  headline_template?: string;
  description_template?: string;
  url_template?: string;
  utm_auto_tagging?: boolean;
  default_keyword?: string;
  cta_text?: string;
  promo_code?: string;
  discount_percent?: number;
  tone_style?: 'auto' | 'professional' | 'friendly' | 'urgent' | 'technical';
}

export interface DcoLogItem {
  id: string;
  query: string;
  inserted_keyword?: string;
  applied_city?: string;
  applied_model?: string;
  applied_promo?: string;
  rendered_text: string;
  rendered_url: string;
  create_time: number;
}

export interface CampaignDcoInfo {
  campaign_id: string;
  campaign_name: string;
  product_name?: string;
  dco_enabled: boolean;
  dco_config: DcoConfig;
  recent_logs: DcoLogItem[];
}

export interface DcoPreviewRequest {
  query: string;
  model?: string;
  region?: string;
  lang?: string;
  custom_template?: string;
  custom_url_template?: string;
  custom_cta?: string;
  custom_promo?: string;
  custom_discount?: number;
  custom_tone?: string;
}

export interface DcoPreviewResponse {
  query: string;
  extracted_keyword: string;
  applied_city: string;
  applied_model: string;
  rendered_text: string;
  rendered_url: string;
  rendered_cta: string;
  promo_code: string;
  discount_percent: number;
  tone_style: string;
}

export interface ScheduleConfig {
  enabled_days?: number[];
  active_hours_start?: number;
  active_hours_end?: number;
  peak_hours?: number[];
  peak_hours_multiplier?: number;
  hourly_multipliers?: Record<string, number>;
}

export interface BiddingStrategyItem {
  id: 'manual_cpc' | 'enhanced_cpc' | 'target_cpa' | 'maximize_conversions';
  name: string;
  description: string;
  badge: string;
  requires_cpa: boolean;
}

export interface BiddingDecisionLogItem {
  id: string;
  strategy: string;
  base_bid: number;
  adjusted_bid: number;
  schedule_multiplier: number;
  cvr_multiplier: number;
  estimated_cvr: number;
  reason: string;
  query?: string;
  create_time: number;
}

export interface CampaignBiddingInfo {
  campaign_id: string;
  campaign_name: string;
  bidding_strategy: 'manual_cpc' | 'enhanced_cpc' | 'target_cpa' | 'maximize_conversions';
  base_bid: number;
  target_cpa: number;
  schedule_timezone: string;
  schedule_config: ScheduleConfig;
  current_status: {
    is_active_now: boolean;
    current_multiplier: number;
    local_time: string;
    local_day: string;
    local_hour: number;
  };
  recent_bids: BiddingDecisionLogItem[];
}

export interface FraudOverviewData {
  total_blocked_clicks: number;
  total_cost_saved: number;
  bot_detections: number;
  rate_limit_blocks: number;
  blacklist_blocks: number;
  active_blacklist_count: number;
  recent_logs: FraudIncidentLogItem[];
}

export interface FraudIncidentLogItem {
  id: string;
  campaign_id: string;
  campaign_name: string;
  event_type: string;
  reason: string;
  ip_hash: string;
  user_agent: string;
  cost_saved: number;
  create_time: number;
}

export interface BlacklistEntryItem {
  id: string;
  ip_address: string;
  advertiser_id?: string;
  is_system: boolean;
  reason: string;
  auto_expires_at?: number;
  status: string;
  create_time: number;
}

export interface PublisherProfileData {
  id: string;
  name: string;
  api_key: string;
  balance: number;
  total_earned: number;
  total_withdrawn: number;
  default_rev_share: number;
  payout_card: string;
  payout_holder: string;
  status: string;
}

export interface PlacementItem {
  id: string;
  publisher_id: string;
  name: string;
  placement_type: 'telegram_bot' | 'web_widget' | 'mobile_app' | 'api_agent';
  domain_or_bot: string;
  rev_share_rate: number;
  impressions: number;
  clicks: number;
  earnings: number;
  status: string;
  create_time: number;
}

export interface PublisherPayoutItem {
  id: string;
  publisher_id: string;
  amount: number;
  currency: string;
  destination_card: string;
  destination_holder: string;
  status: 'pending' | 'approved' | 'paid' | 'rejected';
  note: string;
  create_time: number;
}

export interface AudienceSegmentItem {
  id: string;
  advertiser_id: string;
  name: string;
  description: string;
  rule_type: 'pixel_event' | 'intent_keyword' | 'custom_list';
  rule_config: any;
  member_count: number;
  status: string;
  create_time: number;
}

export interface NotificationItem {
  id: string;
  advertiser_id: string;
  type: string;
  severity: 'info' | 'warning' | 'critical' | 'success';
  title: string;
  message: string;
  is_read: boolean;
  data?: any;
  create_time: number;
}

export interface NotificationData {
  unread_count: number;
  notifications: NotificationItem[];
}

export interface NotificationSettingsData {
  id?: string;
  advertiser_id?: string;
  email_alerts_enabled: boolean;
  email_target: string;
  telegram_alerts_enabled: boolean;
  telegram_chat_id: string;
  webhook_url: string;
  webhook_secret: string;
  notify_low_balance: boolean;
  low_balance_threshold: number;
  notify_daily_budget_reached: boolean;
  notify_moderation_status: boolean;
  notify_conversion_milestone: boolean;
}

export interface TeamMemberItem {
  id: string;
  advertiser_id: string;
  user_id?: string;
  email: string;
  role: 'admin' | 'manager' | 'analyst' | 'billing';
  status: 'active' | 'pending' | 'revoked';
  invited_by?: string;
  create_time: number;
}

export interface PixelSnippetData {
  pixel_id: string;
  snippet: string;
  example_usage: string;
}

export interface CampaignInsightItem {
  id: string;
  campaign_id: string;
  campaign_name: string;
  type: 'ad_copy_refresh' | 'keyword_expansion' | 'negative_keywords' | 'ab_test_recommendation' | 'switch_to_cpa' | 'bid_optimization';
  category: 'quality' | 'reach' | 'cost' | 'growth' | 'bidding';
  severity: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  estimated_impact: string;
  suggested_action: string;
  action_payload: any;
}

export interface AdvertiserInsightsData {
  score: number;
  total_insights: number;
  insights: CampaignInsightItem[];
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
