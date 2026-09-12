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
  pacing_mode?: 'standard_smooth' | 'accelerated_asap' | 'peak_weighted';
  auto_rules_enabled?: boolean;
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

  // Advertiser General Settings & Defaults
  getAdvertiserSettings: () =>
    request.get<ResponseData<AdvertiserSettingsData>>('/ads/settings'),
  updateAdvertiserSettings: (data: Partial<AdvertiserSettingsData>) =>
    request.post<ResponseData<AdvertiserSettingsData>>('/ads/settings', { data }),

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

  // Automated Rules (Auto-Pilot) & Predictive Budget Pacing (Phase 24)
  getRuleTemplates: () =>
    request.get<ResponseData<RuleTemplateItem[]>>('/ads/rules/templates'),
  getAutomatedRules: (campaignId?: string) =>
    request.get<ResponseData<AutomatedRuleItem[]>>('/ads/rules', { params: { campaign_id: campaignId } }),
  createAutomatedRule: (data: Partial<AutomatedRuleItem>) =>
    request.post<ResponseData<AutomatedRuleItem>>('/ads/rules', { data }),
  updateAutomatedRule: (ruleId: string, data: Partial<AutomatedRuleItem>) =>
    request.put<ResponseData<AutomatedRuleItem>>(`/ads/rules/${ruleId}`, { data }),
  deleteAutomatedRule: (ruleId: string) =>
    request.delete<ResponseData<{ deleted: boolean }>>(`/ads/rules/${ruleId}`),
  toggleAutomatedRule: (ruleId: string) =>
    request.post<ResponseData<AutomatedRuleItem>>(`/ads/rules/${ruleId}/toggle`),
  evaluateAutomatedRules: (data?: { campaign_id?: string; rule_id?: string }) =>
    request.post<ResponseData<{ rules_evaluated: number; actions_triggered: number; actions: any[] }>>('/ads/rules/evaluate', { data }),
  getRuleExecutionLogs: (params?: { campaign_id?: string; limit?: number }) =>
    request.get<ResponseData<RuleExecutionLogItem[]>>('/ads/rules/logs', { params }),
  getCampaignPacing: (campaignId: string) =>
    request.get<ResponseData<CampaignPacingInfo>>(`/ads/campaigns/${campaignId}/pacing`),
  updateCampaignPacing: (campaignId: string, data: { pacing_mode: string }) =>
    request.put<ResponseData<CampaignPacingInfo>>(`/ads/campaigns/${campaignId}/pacing`, { data }),
  getAttributionSummary: (params?: { model?: string; days?: number }) =>
    request.get<ResponseData<AttributionSummaryResponse>>('/ads/attribution/summary', { params }),
  getAttributionPaths: (params?: { limit?: number }) =>
    request.get<ResponseData<ConversionJourneyPath[]>>('/ads/attribution/paths', { params }),
  getAttributionFunnel: (params?: { days?: number }) =>
    request.get<ResponseData<FunnelAnalyticsResponse>>('/ads/attribution/funnel', { params }),
  // Phase 26: Lookalikes & Predictive LTV Methods
  getLookalikes: () =>
    request.get<ResponseData<LookalikeAudienceItem[]>>('/ads/audiences/lookalikes'),
  createLookalike: (data: CreateLookalikeRequest) =>
    request.post<ResponseData<LookalikeAudienceItem>>('/ads/audiences/lookalikes', { data }),
  deleteLookalike: (lookalikeId: string) =>
    request.delete<ResponseData<{ deleted: boolean }>>(`/ads/audiences/lookalikes/${lookalikeId}`),
  getLtvOverview: () =>
    request.get<ResponseData<CustomerLtvOverviewResponse>>('/ads/audiences/ltv-overview'),
  syncCustomerLtv: (data: SyncCustomerLtvRequest) =>
    request.post<ResponseData<any>>('/ads/audiences/ltv-sync', { data }),
  // Phase 27: Multi-Format Creative Studio & Product Feeds (DPA) Methods
  generateCreativeMatrix: (data: GenerateCreativeMatrixRequest) =>
    request.post<ResponseData<CreativeMatrixResponse>>('/ads/creatives/generate-matrix', { data }),
  getCreativeHealthScore: (campaignId: string) =>
    request.get<ResponseData<CreativeHealthScoreResponse>>(`/ads/creatives/health-score/${campaignId}`),
  getProductFeeds: () =>
    request.get<ResponseData<ProductFeedItem[]>>('/ads/feeds'),
  createProductFeed: (data: CreateProductFeedRequest) =>
    request.post<ResponseData<ProductFeedItem>>('/ads/feeds', { data }),
  deleteProductFeed: (feedId: string) =>
    request.delete<ResponseData<{ deleted: boolean }>>(`/ads/feeds/${feedId}`),
  getFeedItems: (feedId: string, params?: { category?: string; search?: string; limit?: number }) =>
    request.get<ResponseData<ProductSkuItem[]>>(`/ads/feeds/${feedId}/items`, { params }),
  addFeedItem: (feedId: string, data: any) =>
    request.post<ResponseData<ProductSkuItem>>(`/ads/feeds/${feedId}/items`, { data }),
  // Phase 28: Enterprise Agency Hub, Sub-Accounts & White-Label Reporting Methods
  getAgencyWorkspace: () =>
    request.get<ResponseData<AgencyWorkspace>>('/ads/agency/workspace'),
  updateAgencyWorkspace: (data: UpdateAgencyWorkspaceRequest) =>
    request.put<ResponseData<AgencyWorkspace>>('/ads/agency/workspace', { data }),
  getAgencyClients: () =>
    request.get<ResponseData<AgencyClient[]>>('/ads/agency/clients'),
  createAgencyClient: (data: CreateAgencyClientRequest) =>
    request.post<ResponseData<AgencyClient>>('/ads/agency/clients', { data }),
  deleteAgencyClient: (clientId: string) =>
    request.delete<ResponseData<{ deleted: boolean }>>(`/ads/agency/clients/${clientId}`),
  getAgencyMembers: () =>
    request.get<ResponseData<AgencyMember[]>>('/ads/agency/members'),
  inviteAgencyMember: (data: InviteAgencyMemberRequest) =>
    request.post<ResponseData<AgencyMember>>('/ads/agency/members/invite', { data }),
  removeAgencyMember: (memberId: string) =>
    request.delete<ResponseData<{ removed: boolean }>>(`/ads/agency/members/${memberId}`),
  getExecutiveReport: (params?: { client_id?: string; days?: number; custom_title?: string }) =>
    request.get<ResponseData<ExecutiveReportData>>('/ads/agency/reports/executive', { params }),
  shareAgencyReport: (data: { client_id?: string; report_title?: string; days?: number }) =>
    request.post<ResponseData<ShareReportResponse>>('/ads/agency/reports/share', { data }),
  getPublicSharedReport: (shareToken: string) =>
    request.get<ResponseData<ExecutiveReportData>>(`/ads/agency/reports/shared/${shareToken}`),
  // Phase 36: Cross-Platform Omni-Channel Ads Bridge
  getOmniAccounts: () =>
    request.get<ResponseData<OmniAccountItem[]>>('/ads/omnichannel/accounts'),
  connectOmniAccount: (data: ConnectOmniAccountRequest) =>
    request.post<ResponseData<any>>('/ads/omnichannel/accounts', { data }),
  disconnectOmniAccount: (accountId: string) =>
    request.delete<ResponseData<{ success: boolean }>>(`/ads/omnichannel/accounts/${accountId}`),
  testOmniAccount: (accountId: string) =>
    request.post<ResponseData<any>>(`/ads/omnichannel/accounts/${accountId}/test`),
  exportOmniCampaign: (data: ExportOmniCampaignRequest) =>
    request.post<ResponseData<ExportOmniCampaignResponse>>('/ads/omnichannel/export-campaign', { data }),
  syncOmniAudience: (data: SyncOmniAudienceRequest) =>
    request.post<ResponseData<any>>('/ads/omnichannel/sync-audience', { data }),
  getCrossPlatformAnalytics: (params?: { days?: number }) =>
    request.get<ResponseData<CrossPlatformAnalyticsResponse>>('/ads/omnichannel/cross-platform-analytics', { params }),
  getOmniSyncJobs: (params?: { limit?: number }) =>
    request.get<ResponseData<OmniSyncJobItem[]>>('/ads/omnichannel/sync-jobs', { params }),
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

export interface AdvertiserSettingsData {
  advertiser_id: string;
  company_name: string;
  contact_email: string;
  website_url: string;
  currency: string;
  pixel_id: string;
  balance: number;
  status: string;
  language: 'ru' | 'en' | 'uz';
  default_regions: string[];
  default_models: string[];
  daily_spend_ceiling: number;
  default_frequency_cap: number;
  auto_pause_low_ctr: boolean;
  low_ctr_threshold: number;
  timezone: string;
  notifications?: NotificationSettingsData;
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

export interface AutomatedRuleItem {
  id: string;
  advertiser_id: string;
  campaign_id: string;
  campaign_name?: string;
  name: string;
  description?: string;
  metric: 'ctr' | 'cvr' | 'cpa' | 'impressions' | 'clicks' | 'spent' | 'conversions' | 'spent_ratio';
  operator: '<' | '<=' | '>' | '>=' | '==' | '=';
  threshold_value: number;
  min_impressions: number;
  time_window: 'today' | 'last_7_days' | 'last_30_days' | 'lifetime';
  action_type: 'pause_campaign' | 'resume_campaign' | 'increase_bid' | 'decrease_bid' | 'increase_budget' | 'decrease_budget' | 'send_alert';
  action_value: number;
  is_active: boolean;
  last_evaluated_time?: number;
  last_triggered_time?: number;
  trigger_count: number;
  create_time: number;
}

export interface RuleTemplateItem {
  template_id: string;
  name: string;
  description: string;
  metric: string;
  operator: string;
  threshold_value: number;
  min_impressions: number;
  time_window: string;
  action_type: string;
  action_value: number;
}

export interface RuleExecutionLogItem {
  id: string;
  rule_id: string;
  rule_name: string;
  campaign_id: string;
  campaign_name: string;
  advertiser_id: string;
  metric_name: string;
  metric_current_value: number;
  threshold_value: number;
  action_taken: string;
  action_details: string;
  create_time: number;
}

export interface CampaignPacingInfo {
  campaign_id: string;
  campaign_name: string;
  daily_budget: number;
  spent_today: number;
  pacing_mode: 'standard_smooth' | 'accelerated_asap' | 'peak_weighted';
  schedule_timezone: string;
  current_pacing_multiplier: number;
  burn_rate_status: 'optimal' | 'overpacing' | 'underpacing';
  hourly_forecast: Array<{
    hour: number;
    hour_label: string;
    expected_cumulative_spend: number;
    expected_ratio: number;
  }>;
}

export type AttributionModelType =
  | 'last_touch'
  | 'first_touch'
  | 'linear'
  | 'time_decay'
  | 'position_based';

export interface CampaignAttributionCredit {
  campaign_id: string;
  campaign_name: string;
  product_name?: string;
  total_spend: number;
  credited_conversions: number;
  credited_revenue: number;
  first_touch_count: number;
  last_touch_count: number;
  assisted_count: number;
  effective_cpa: number;
  roas: number;
}

export interface AttributionSummaryResponse {
  model_selected: AttributionModelType;
  days: number;
  total_conversions: number;
  total_revenue: number;
  avg_touchpoints_per_conversion: number;
  avg_journey_duration_hours: number;
  campaigns: CampaignAttributionCredit[];
}

export interface JourneyPathStep {
  seq: number;
  campaign_name: string;
  type: string;
  channel: string;
  device: string;
}

export interface ConversionJourneyPath {
  id: string;
  visitor_id: string;
  conversion_type: string;
  conversion_value: number;
  total_touchpoints: number;
  journey_duration_hours: number;
  first_touch: string;
  last_touch: string;
  path_steps: JourneyPathStep[];
  create_time: number;
}

export interface FunnelStageItem {
  stage_id: string;
  name: string;
  count: number;
  conversion_from_prev: number;
  dropoff_rate: number;
}

export interface FunnelAnalyticsResponse {
  days: number;
  overall_funnel_conversion_rate: number;
  stages: FunnelStageItem[];
}

// Phase 26: Lookalikes & Predictive LTV Types
export interface LookalikeAudienceItem {
  id: string;
  advertiser_id: string;
  source_segment_id: string;
  source_segment_name: string;
  name: string;
  similarity_ratio: number;
  country: string;
  seed_audience_size: number;
  estimated_reach: number;
  status: 'building' | 'ready' | 'failed';
  feature_weights: Record<string, number>;
  create_time: number;
}

export interface CreateLookalikeRequest {
  source_segment_id: string;
  name: string;
  similarity_ratio?: number;
  country?: string;
  custom_weights?: Record<string, number>;
}

export type RfmSegmentType =
  | 'champions'
  | 'loyal'
  | 'potential_loyalist'
  | 'recent_customers'
  | 'at_risk'
  | 'hibernating'
  | 'lost';

export interface CustomerLtvProfileItem {
  id: string;
  visitor_id: string;
  customer_identifier: string;
  rfm_segment: RfmSegmentType;
  predicted_ltv_90d: number;
  predicted_ltv_365d: number;
  churn_risk_score: number;
  total_orders: number;
  rfm_monetary_val: number;
  avg_order_value: number;
  rfm_recency_days: number;
  tags: string[];
  create_time: number;
}

export interface CustomerLtvOverviewResponse {
  total_customers: number;
  avg_predicted_ltv_90d: number;
  avg_predicted_ltv_365d: number;
  avg_churn_risk_percent: number;
  total_historical_revenue: number;
  segment_counts: Record<string, number>;
  top_customers: CustomerLtvProfileItem[];
}

export interface SyncCustomerLtvRequest {
  visitor_id?: string;
  customer_identifier?: string;
  order_value?: number;
  total_orders?: number;
  recency_days?: number;
  tags?: string[];
  customers?: Array<{
    visitor_id?: string;
    id?: string;
    email?: string;
    phone?: string;
    customer_identifier?: string;
    order_value?: number;
    spend?: number;
    total_orders?: number;
    orders?: number;
    recency_days?: number;
    recency?: number;
    tags?: string[];
  }>;
}

// Phase 27: Multi-Format Creative Studio & Product Feed Types
export interface ProductFeedItem {
  id: string;
  advertiser_id: string;
  name: string;
  feed_type: string;
  feed_url?: string;
  currency: string;
  items_count: number;
  sync_status: 'active' | 'syncing' | 'error' | 'paused';
  last_sync_time: number;
  sync_frequency: string;
  create_time: number;
}

export interface ProductSkuItem {
  id: string;
  feed_id: string;
  advertiser_id: string;
  sku: string;
  title: string;
  description?: string;
  price: number;
  original_price?: number;
  discount_percent: number;
  currency: string;
  image_url?: string;
  product_url: string;
  category: string;
  brand: string;
  availability: 'in_stock' | 'out_of_stock' | 'preorder';
  custom_labels?: Record<string, any>;
  is_active: boolean;
  create_time: number;
}

export interface CreateProductFeedRequest {
  name: string;
  feed_type?: string;
  feed_url?: string;
  currency?: string;
  sync_frequency?: string;
  items?: Array<{
    sku?: string;
    title: string;
    price: number;
    original_price?: number;
    product_url: string;
    image_url?: string;
    category?: string;
    brand?: string;
    availability?: string;
  }>;
}

export interface CreativeMatrixFormats {
  text_card: {
    headlines: string[];
    descriptions: string[];
    ctas: string[];
    badges: string[];
  };
  rich_interactive_card: {
    widget_title: string;
    headline: string;
    features: string[];
    primary_cta: string;
    secondary_cta: string;
    visual_style: string;
    rating: number;
    reviews_count: number;
  };
  story_banner: {
    aspect_ratio: string;
    resolution: string;
    title_overlay: string;
    subtitle: string;
    sticker_badge: string;
    swipe_up_text: string;
    background_gradient: string;
  };
  leaderboard_banner: {
    dimensions: string[];
    banner_header: string;
    banner_body: string;
    button_text: string;
    color_theme: string;
  };
  video_storyboard: {
    duration_sec: number;
    target_platform: string[];
    scenes: Array<{
      scene: number;
      timestamp: string;
      phase: string;
      visual: string;
      voiceover: string;
    }>;
  };
}

export interface CreativeMatrixResponse {
  product_name: string;
  category: string;
  target_audience: string;
  overall_health_score: number;
  formats: CreativeMatrixFormats;
  saved_assets: Array<{
    id: string;
    format_type: string;
    asset_payload: any;
    health_score: number;
  }>;
}

export interface GenerateCreativeMatrixRequest {
  product_name: string;
  description?: string;
  category?: string;
  target_audience?: string;
  campaign_id?: string;
  save_assets?: boolean;
}

export interface CreativeHealthCheckItem {
  name: string;
  status: 'passed' | 'warning' | 'failed' | 'info';
  desc: string;
}

export interface CreativeHealthScoreResponse {
  campaign_id: string;
  campaign_name: string;
  score: number;
  rating: 'excellent' | 'good' | 'needs_improvement';
  variants_count: number;
  has_dco: boolean;
  has_feeds: boolean;
  checklist: CreativeHealthCheckItem[];
  recommendations: string[];
}

export interface AgencyWorkspace {
  id: string;
  owner_advertiser_id: string;
  name: string;
  agency_slug: string;
  logo_url: string;
  brand_color: string;
  report_footer_text: string;
  billing_mode: 'consolidated' | 'separate';
  status: string;
  clients_count: number;
  members_count: number;
  total_managed_spend: number;
  create_time: number;
}

export interface UpdateAgencyWorkspaceRequest {
  workspace_id?: string;
  name?: string;
  logo_url?: string;
  brand_color?: string;
  report_footer_text?: string;
  billing_mode?: string;
}

export interface AgencyClient {
  id: string;
  workspace_id: string;
  client_advertiser_id: string;
  client_name: string;
  contact_email?: string;
  monthly_budget_cap: number;
  monthly_spend_current: number;
  currency: string;
  status: 'active' | 'paused' | 'archived';
  campaigns_count: number;
  active_campaigns_count: number;
  total_spend: number;
  total_clicks: number;
  avg_ctr: number;
  total_conversions: number;
  avg_cpa: number;
  create_time: number;
}

export interface CreateAgencyClientRequest {
  client_name: string;
  contact_email?: string;
  monthly_budget_cap?: number;
  currency?: string;
}

export interface AgencyMember {
  id: string;
  workspace_id: string;
  user_id: string;
  email: string;
  role: 'agency_admin' | 'media_buyer' | 'creative_designer' | 'financial_auditor' | 'client_viewer';
  assigned_client_ids: string[];
  status: 'active' | 'invited' | 'suspended';
  invite_token?: string;
  create_time: number;
}

export interface InviteAgencyMemberRequest {
  email: string;
  role?: string;
  assigned_client_ids?: string[];
}

export interface ExecutiveReportData {
  report_id: string;
  workspace_id: string;
  report_title: string;
  period_days: number;
  generated_at: string;
  white_label: {
    agency_name: string;
    agency_slug: string;
    logo_url: string;
    brand_color: string;
    footer_text: string;
  };
  client_info: {
    client_id?: string;
    client_name: string;
    currency: string;
  };
  kpi_summary: {
    total_spend: number;
    total_impressions: number;
    total_clicks: number;
    avg_ctr: number;
    avg_cpc: number;
    total_conversions: number;
    avg_cpa: number;
    estimated_revenue: number;
    roas: number;
    active_campaigns: number;
  };
  timeline_trends: Array<{
    date: string;
    spend: number;
    clicks: number;
    conversions: number;
  }>;
  channel_attribution: Array<{
    channel: string;
    share_percent: number;
    conversions: number;
    cpa: number;
  }>;
  top_creative_assets: Array<{
    title: string;
    format: string;
    ctr: number;
    conversions: number;
    health_score: number;
  }>;
  executive_takeaways: string[];
}

export interface ShareReportResponse {
  template_id: string;
  share_token: string;
  share_url: string;
  expires_in: string;
}

// Phase 36: Cross-Platform Omni-Channel Ads Bridge Interfaces
export type OmniPlatformType = 'telegram_ads' | 'meta_ads' | 'google_ads' | 'tiktok_ads' | 'yandex_direct';

export interface OmniAccountItem {
  id: string;
  advertiser_id: string;
  platform: OmniPlatformType;
  platform_display_name: string;
  account_name: string;
  account_id_external: string | null;
  auth_status: 'connected' | 'expired' | 'error' | 'disconnected';
  default_currency: string;
  auto_sync_enabled: boolean;
  total_campaigns_exported: number;
  total_external_spend: number;
  last_sync_time: number | null;
  create_time: number;
}

export interface ConnectOmniAccountRequest {
  platform: OmniPlatformType;
  account_name: string;
  account_id_external?: string;
  access_token?: string;
  refresh_token?: string;
  default_currency?: string;
  auto_sync_enabled?: boolean;
}

export interface ExportOmniCampaignRequest {
  account_id: string;
  campaign_id: string;
  export_params?: {
    target_channels?: string[];
    target_languages?: string[];
    interests?: string[];
    keywords?: string[];
  };
}

export interface ExportOmniCampaignResponse {
  job_id: string;
  account_id: string;
  platform: string;
  campaign_id: string;
  external_campaign_id: string;
  status: string;
  payload: any;
  target_info: any;
  message: string;
}

export interface SyncOmniAudienceRequest {
  account_id: string;
  segment_id: string;
}

export interface CrossPlatformNetworkStat {
  platform: string;
  name: string;
  account_name?: string;
  spend: number;
  impressions: number;
  clicks: number;
  ctr: number;
  conversions: number;
  cpa: number;
  share_percent: number;
}

export interface CrossPlatformAnalyticsResponse {
  period_days: number;
  connected_accounts_count: number;
  total_blended_spend: number;
  total_blended_impressions: number;
  total_blended_clicks: number;
  total_blended_conversions: number;
  blended_ctr: number;
  blended_cpa: number;
  blended_roas: number;
  networks: CrossPlatformNetworkStat[];
}

export interface OmniSyncJobItem {
  id: string;
  advertiser_id: string;
  account_id: string;
  campaign_id: string | null;
  platform: string;
  job_type: string;
  status: string;
  external_campaign_id: string | null;
  payload_data: any;
  response_data: any;
  items_synced_count: number;
  error_message: string | null;
  create_time: number;
  finish_time: number | null;
}

export default adService;



