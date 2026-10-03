import React from 'react';
import {
  Megaphone,
  Activity,
  MousePointer,
  DollarSign,
  Download,
  Plus,
  ExternalLink,
  Pause,
  Play,
  Wand2,
  Timer,
  Zap,
  FlaskConical,
  Sparkles,
  BarChart3,
  Edit3,
  Trash2,
  Clock,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import {
  AdvertiserDashboardData,
  AdCampaignItem,
} from '@/services/ad-service';
import { toFixedSafe, toLocaleSafe } from '../format-utils';
import { AdLanguage, translateAdText } from '../translations';

export interface CampaignsTabProps {
  dashboard: AdvertiserDashboardData | null;
  onOpenCreateCampaign: () => void;
  onToggleStatus: (campaign: AdCampaignItem) => void;
  onOpenDcoModal: (campaign: AdCampaignItem) => void;
  onOpenPacingModal: (campaign: AdCampaignItem) => void;
  onOpenBiddingConfig: (campaign: AdCampaignItem) => void;
  onOpenVariants: (campaign: AdCampaignItem) => void;
  onViewCampaignHealth: (campaignId: string) => void;
  onOpenAnalytics: (campaign: AdCampaignItem) => void;
  onOpenEditCampaign: (campaign: AdCampaignItem) => void;
  onDeleteCampaign: (campaign: AdCampaignItem) => void;
  onExportCsv?: () => void;
  currentLang?: AdLanguage;
  t?: (keyOrText: string, fallback?: string) => string;
}

export const CampaignsTab: React.FC<CampaignsTabProps> = ({
  dashboard,
  onOpenCreateCampaign,
  onToggleStatus,
  onOpenDcoModal,
  onOpenPacingModal,
  onOpenBiddingConfig,
  onOpenVariants,
  onViewCampaignHealth,
  onOpenAnalytics,
  onOpenEditCampaign,
  onDeleteCampaign,
  onExportCsv = () => window.open('/v1/ads/export/campaigns', '_blank'),
  currentLang = 'ru',
  t = (key: string, fallback?: string) => translateAdText(key, currentLang, fallback),
}) => {
  return (
    <div className="space-y-4">
      {/* KPI Cards on Campaigns Tab */}
      <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 w-full">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('activeCampaigns')}</CardTitle>
            <Megaphone className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboard?.active_campaigns || 0}{' '}
              <span className="text-xs font-normal text-muted-foreground">/ {dashboard?.total_campaigns || 0} {t('totalSuffix')}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">{t('liveInAuction')}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('totalImpressions')}</CardTitle>
            <Activity className="h-4 w-4 text-indigo-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{toLocaleSafe(dashboard?.total_impressions)}</div>
            <p className="text-xs text-muted-foreground mt-1">{t('timesShown')}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('clicksEngagement')}</CardTitle>
            <MousePointer className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {toLocaleSafe(dashboard?.total_clicks)}{' '}
              <span className="text-sm font-normal text-emerald-500">({dashboard?.ctr || 0}% CTR)</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">{t('verifiedVisits')}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('totalSpend')}</CardTitle>
            <DollarSign className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${toFixedSafe(dashboard?.total_spent, 2)}</div>
            <p className="text-xs text-muted-foreground mt-1">{t('allTimeInvest')}</p>
          </CardContent>
        </Card>
      </div>

      {/* Campaigns Table Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>{t('campaignsCardTitle')}</CardTitle>
            <CardDescription>
              {t('campaignsCardDesc')}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              className="text-xs flex items-center gap-1.5"
              onClick={onExportCsv}
            >
              <Download className="h-3.5 w-3.5" /> {t('exportCsvBtn')}
            </Button>
            <Button onClick={onOpenCreateCampaign} size="sm" className="bg-blue-600 hover:bg-blue-700 text-white text-xs">
              <Plus className="mr-1 h-3.5 w-3.5" /> {t('newCampaignBtn')}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {!Array.isArray(dashboard?.campaigns) || dashboard.campaigns.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-500/10 text-blue-500 mb-3">
                <Megaphone className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-semibold">{t('noCampaignsYet')}</h3>
              <p className="text-sm text-muted-foreground max-w-sm mt-1">
                {t('noCampaignsDesc')}
              </p>
              <Button onClick={onOpenCreateCampaign} className="mt-4 bg-blue-600 hover:bg-blue-700 text-white">
                <Plus className="mr-1.5 h-4 w-4" /> {t('createFirstCampaignBtn')}
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b bg-muted/40 text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="py-3 px-4">{t('thCampaignProduct')}</th>
                    <th className="py-3 px-4">{t('thStatus')}</th>
                    <th className="py-3 px-4">{t('thModelBid')}</th>
                    <th className="py-3 px-4">{t('thBudgetSpend')}</th>
                    <th className="py-3 px-4">{t('thImpressions')}</th>
                    <th className="py-3 px-4">{t('thClicksCtr')}</th>
                    <th className="py-3 px-4 text-right">{t('thActions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(dashboard?.campaigns || []).map((cmp) => (
                    <tr key={cmp.id || (cmp as any).campaign_id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-foreground flex items-center gap-1.5">
                          {cmp.name}
                          {cmp.dco_enabled && (
                            <Badge variant="outline" className="border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 text-[10px] px-1.5 py-0 font-bold">
                              ✨ DCO
                            </Badge>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
                          <span className="font-medium text-blue-500">{cmp.product_name}</span>
                          <span>•</span>
                          <a
                            href={cmp.landing_url}
                            target="_blank"
                            rel="noreferrer"
                            className="hover:underline flex items-center gap-0.5 text-xs text-muted-foreground truncate max-w-[200px]"
                          >
                            {cmp.landing_url} <ExternalLink className="h-2.5 w-2.5 inline" />
                          </a>
                        </div>
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {(!Array.isArray(cmp.target_languages) || cmp.target_languages.length === 0 || cmp.target_languages.includes('all')) ? (
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300 font-medium">{t('badgeAllLanguages')}</span>
                          ) : (
                            (cmp.target_languages || []).map((l) => (
                              <span key={l} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-sky-50 text-sky-700 dark:bg-sky-950/50 dark:text-sky-300 font-bold uppercase">
                                {l === 'uz' ? '🇺🇿 UZ' : l === 'ru' ? '🇷🇺 RU' : l === 'en' ? '🇬🇧 EN' : l}
                              </span>
                            ))
                          )}
                          {Array.isArray(cmp.target_models) && cmp.target_models.length > 0 && !cmp.target_models.includes('all') && (
                            cmp.target_models.map((m: string) => (
                              <span key={m} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-purple-50 text-purple-700 dark:bg-purple-950/50 dark:text-purple-300 font-medium">
                                🤖 {m}
                              </span>
                            ))
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-col gap-1">
                          <Badge
                            variant="outline"
                            className={
                              cmp.status === 'active'
                                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-500'
                                : 'border-zinc-500/30 bg-zinc-500/10 text-zinc-400'
                            }
                          >
                            {cmp.status === 'active' ? t('statusActive') : t('statusPaused')}
                          </Badge>
                          {cmp.moderation_status === 'pending' && (
                            <Badge variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-500 text-[10px]">
                              {t('statusPending')}
                            </Badge>
                          )}
                          {cmp.moderation_status === 'rejected' && (
                            <Badge variant="outline" className="border-red-500/30 bg-red-500/10 text-red-500 text-[10px]">
                              {t('statusRejected')}
                            </Badge>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-medium uppercase text-xs flex items-center gap-1">
                          {cmp.pricing_model}
                          {cmp.bidding_strategy === 'enhanced_cpc' && (
                            <Badge variant="outline" className="border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400 text-[9px] px-1 py-0 font-bold">
                              ⚡ E-CPC
                            </Badge>
                          )}
                          {cmp.bidding_strategy === 'target_cpa' && (
                            <Badge variant="outline" className="border-purple-500/30 bg-purple-500/10 text-purple-600 dark:text-purple-400 text-[9px] px-1 py-0 font-bold">
                              🎯 tCPA
                            </Badge>
                          )}
                          {cmp.bidding_strategy === 'maximize_conversions' && (
                            <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[9px] px-1 py-0 font-bold">
                              🚀 MAX
                            </Badge>
                          )}
                          {cmp.pacing_mode === 'accelerated_asap' && (
                            <Badge variant="outline" className="border-rose-500/30 bg-rose-500/10 text-rose-600 dark:text-rose-400 text-[9px] px-1 py-0 font-bold">
                              ⚡ ASAP
                            </Badge>
                          )}
                          {cmp.pacing_mode === 'peak_weighted' && (
                            <Badge variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400 text-[9px] px-1 py-0 font-bold">
                              📈 {t('peakBadge', 'Пик')}
                            </Badge>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground font-semibold">
                          {cmp.pricing_model === 'cpa' || cmp.bidding_strategy === 'target_cpa'
                            ? `$${toFixedSafe(cmp.target_cpa ?? 5.0, 2)} ${t('targetCpaLabel')}`
                            : `$${toFixedSafe(cmp.bid_amount, 2)} / ${cmp.pricing_model === 'cpc' ? t('perClick') : t('per1kImp')}`}
                        </div>
                        {cmp.schedule_config?.enabled_days && cmp.schedule_config.enabled_days.length < 7 && (
                          <div className="text-[10px] text-amber-600 dark:text-amber-400 font-medium flex items-center gap-1 mt-0.5">
                            <Clock className="h-2.5 w-2.5" /> {t('scheduleLabel')} ({cmp.schedule_config.active_hours_start || 0}:00-{cmp.schedule_config.active_hours_end || 23}:00)
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-xs">
                          <span className="font-bold">${toFixedSafe(cmp.spent_today, 2)}</span> / ${toFixedSafe(cmp.daily_budget, 2)} {t('dayUnit')}
                        </div>
                        <div className="text-[11px] text-muted-foreground">
                          {t('totalBudgetLabel')} ${toFixedSafe(cmp.total_spent, 2)} / ${toFixedSafe(cmp.total_budget, 2)}
                        </div>
                      </td>
                      <td className="py-3 px-4 font-medium">{toLocaleSafe(cmp.impressions)}</td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-emerald-600 dark:text-emerald-400">{toLocaleSafe(cmp.clicks)}</div>
                        <div className="text-xs text-muted-foreground">{cmp.ctr || 0}% CTR</div>
                        {((cmp.conversions_count && cmp.conversions_count > 0) || cmp.pricing_model === 'cpa') && (
                          <div className="text-[11px] font-medium text-purple-600 dark:text-purple-400 mt-0.5">
                            🎯 {cmp.conversions_count || 0} {t('conversionsBadge', 'conv')} ({cmp.conversion_rate || 0}% CVR)
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => onToggleStatus(cmp)}
                            title={cmp.status === 'active' ? t('pauseCampaignTooltip') : t('activateCampaignTooltip')}
                          >
                            {cmp.status === 'active' ? (
                              <Pause className="h-4 w-4 text-amber-500" />
                            ) : (
                              <Play className="h-4 w-4 text-emerald-500" />
                            )}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => onOpenDcoModal(cmp)}
                            title={t('dcoTooltip')}
                            className="text-cyan-600 hover:text-cyan-700 dark:text-cyan-400"
                          >
                            <Wand2 className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => onOpenPacingModal(cmp)}
                            title={t('pacingTooltip')}
                            className="text-purple-600 hover:text-purple-700 dark:text-purple-400"
                          >
                            <Timer className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => onOpenBiddingConfig(cmp)}
                            title={t('biddingTooltip')}
                            className="text-amber-600 hover:text-amber-700 dark:text-amber-400"
                          >
                            <Zap className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => onOpenVariants(cmp)}
                            title={t('variantsTooltip')}
                            className="text-purple-600 hover:text-purple-700 dark:text-purple-400"
                          >
                            <FlaskConical className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => onViewCampaignHealth(cmp.id)}
                            title={t('healthTooltip')}
                            className="text-pink-600 hover:text-pink-700 dark:text-pink-400"
                          >
                            <Sparkles className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => onOpenAnalytics(cmp)}
                            title={t('analyticsTooltip')}
                          >
                            <BarChart3 className="h-4 w-4 text-blue-500" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => onOpenEditCampaign(cmp)}
                            title={t('editCampaignTooltip')}
                          >
                            <Edit3 className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => onDeleteCampaign(cmp)}
                            title={t('deleteCampaignTooltip')}
                          >
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
