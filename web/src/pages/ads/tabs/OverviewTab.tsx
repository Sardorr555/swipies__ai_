import React from 'react';
import {
  Sparkles,
  Plus,
  Code2,
  Wallet,
  Megaphone,
  Activity,
  MousePointer,
  DollarSign,
  BarChart3,
  ArrowRight,
  Layers,
  Zap,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from 'recharts';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import {
  AdvertiserDashboardData,
  ProductFeedItem,
} from '@/services/ad-service';
import { toFixedSafe, toLocaleSafe } from '../format-utils';
import { AdLanguage, translateAdText } from '../translations';

export interface OverviewTimelinePoint {
  date: string;
  impressions: number;
  clicks: number;
  spend?: number;
}

export interface OverviewTabProps {
  dashboard: AdvertiserDashboardData | null;
  overviewTimeline?: OverviewTimelinePoint[];
  productFeeds?: ProductFeedItem[];
  onOpenCreateCampaign: () => void;
  onOpenPixelModal: () => void;
  onOpenTopUpModal: () => void;
  onNavigateTab: (tab: string) => void;
  currentLang?: AdLanguage;
  t?: (keyOrText: string, fallback?: string) => string;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  dashboard,
  overviewTimeline: rawTimeline,
  productFeeds = [],
  onOpenCreateCampaign,
  onOpenPixelModal,
  onOpenTopUpModal,
  onNavigateTab,
  currentLang = 'ru',
  t: customT,
}) => {
  const t = (keyOrText: string, fallback?: string): string => {
    if (customT) return customT(keyOrText, fallback);
    return translateAdText(keyOrText, currentLang, fallback);
  };

  const overviewTimeline =
    rawTimeline && Array.isArray(rawTimeline) && rawTimeline.length > 0
      ? rawTimeline
      : Array.from({ length: 14 }).map((_, i) => {
          const d = new Date();
          d.setDate(d.getDate() - (13 - i));
          const dateStr = d.toISOString().slice(5, 10);
          return { date: dateStr, impressions: 0, clicks: 0, spend: 0 };
        });

  return (
    <div className="space-y-6">
      {/* Hero Welcome Banner */}
      <div className="relative overflow-hidden rounded-xl border bg-gradient-to-r from-blue-600/10 via-indigo-600/10 to-purple-600/10 p-5 sm:p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="space-y-1.5 max-w-2xl">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/15 text-blue-600 dark:text-blue-400">
              <Sparkles className="h-3.5 w-3.5" /> Next-Gen AI Ad Platform
            </div>
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
              {t('overviewWelcome')}
            </h2>
            <p className="text-xs sm:text-sm text-muted-foreground">
              {t('overviewDesc')}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <Button
              onClick={onOpenCreateCampaign}
              className="bg-blue-600 hover:bg-blue-700 text-white text-xs sm:text-sm h-9 shadow-sm"
            >
              <Plus className="mr-1.5 h-4 w-4" /> {t('newCampaignBtn')}
            </Button>
            <Button
              variant="outline"
              onClick={onOpenPixelModal}
              className="text-xs sm:text-sm h-9 border-purple-500/30 text-purple-600 dark:text-purple-400 hover:bg-purple-500/10"
            >
              <Code2 className="mr-1.5 h-4 w-4" /> {t('pixelBtn')}
            </Button>
            <Button
              variant="outline"
              onClick={onOpenTopUpModal}
              className="text-xs sm:text-sm h-9 border-emerald-500/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/10"
            >
              <Wallet className="mr-1.5 h-4 w-4" /> {t('topUpBtn')}
            </Button>
          </div>
        </div>
      </div>

      {/* 4 Core KPI Metrics */}
      <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 w-full">
        <Card className="hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs sm:text-sm font-medium">{t('activeCampaigns')}</CardTitle>
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

        <Card className="hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs sm:text-sm font-medium">{t('totalImpressions')}</CardTitle>
            <Activity className="h-4 w-4 text-indigo-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{toLocaleSafe(dashboard?.total_impressions)}</div>
            <p className="text-xs text-muted-foreground mt-1">{t('timesShown')}</p>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs sm:text-sm font-medium">{t('clicksEngagement')}</CardTitle>
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

        <Card className="hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs sm:text-sm font-medium">{t('totalSpend')}</CardTitle>
            <DollarSign className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${toFixedSafe(dashboard?.total_spent, 2)}</div>
            <p className="text-xs text-muted-foreground mt-1">{t('allTimeInvest')}</p>
          </CardContent>
        </Card>
      </div>

      {/* Interactive 14-Day Performance Dynamics Chart */}
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-4">
          <div>
            <CardTitle className="text-base font-semibold">{t('performanceTrendsTitle')}</CardTitle>
            <CardDescription className="text-xs text-muted-foreground">
              {t('performanceTrendsDesc')}
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onNavigateTab('analytics')}
            className="text-xs h-8 flex items-center gap-1 w-max"
          >
            <BarChart3 className="h-3.5 w-3.5 text-blue-500" /> {t('tabAnalytics')}
            <ArrowRight className="h-3.5 w-3.5 ml-1" />
          </Button>
        </CardHeader>
        <CardContent>
          <div className="h-[260px] sm:h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={overviewTimeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="overviewImpGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="overviewClkGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ backgroundColor: '#09090b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px' }} />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Area
                  type="monotone"
                  dataKey="impressions"
                  name={t('totalImpressions')}
                  stroke="#3b82f6"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#overviewImpGradient)"
                />
                <Area
                  type="monotone"
                  dataKey="clicks"
                  name={t('clicksEngagement')}
                  stroke="#10b981"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#overviewClkGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Quick Navigation Cards Grid (4 Essential Cards) */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="hover:border-blue-500/40 hover:shadow-md transition-all cursor-pointer" onClick={() => onNavigateTab('campaigns')}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
                <Layers className="h-5 w-5" />
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </div>
            <CardTitle className="text-sm font-semibold mt-2">{t('tabCampaigns')}</CardTitle>
            <CardDescription className="text-xs">
              {t('campaignsCardDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-0">
            <Button variant="ghost" size="sm" className="h-7 text-xs text-blue-600 dark:text-blue-400 p-0 font-medium">
              {t('viewAllCampaigns')} ({dashboard?.campaigns?.length || 0}) →
            </Button>
          </CardContent>
        </Card>

        <Card className="hover:border-purple-500/40 hover:shadow-md transition-all cursor-pointer" onClick={() => onNavigateTab('studio')}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400">
                <Sparkles className="h-5 w-5" />
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </div>
            <CardTitle className="text-sm font-semibold mt-2">{t('cardStudioTitle')}</CardTitle>
            <CardDescription className="text-xs">
              DPA каталоги товаров, AI креативы и генерация раскадровок
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-0">
            <Button variant="ghost" size="sm" className="h-7 text-xs text-purple-600 dark:text-purple-400 p-0 font-medium">
              {t('tabStudio')} ({(Array.isArray(productFeeds) ? productFeeds.length : 0)}) →
            </Button>
          </CardContent>
        </Card>

        <Card className="hover:border-amber-500/40 hover:shadow-md transition-all cursor-pointer" onClick={onOpenPixelModal}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
                <Zap className="h-5 w-5" />
              </div>
              <Code2 className="h-4 w-4 text-muted-foreground" />
            </div>
            <CardTitle className="text-sm font-semibold mt-2">{t('cardPixelTitle')}</CardTitle>
            <CardDescription className="text-xs">
              Отслеживание конверсий и обучение алгоритма Smart CPA
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-0">
            <Button variant="ghost" size="sm" className="h-7 text-xs text-amber-600 dark:text-amber-400 p-0 font-medium">
              {t('pixelBtn')} →
            </Button>
          </CardContent>
        </Card>

        <Card className="hover:border-emerald-500/40 hover:shadow-md transition-all cursor-pointer" onClick={() => onNavigateTab('billing')}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <Wallet className="h-5 w-5" />
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </div>
            <CardTitle className="text-sm font-semibold mt-2">{t('cardWalletTitle')}</CardTitle>
            <CardDescription className="text-xs">
              Баланс: ${toFixedSafe(dashboard?.balance, 2)} • Пополнение и чеки
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-0">
            <Button variant="ghost" size="sm" className="h-7 text-xs text-emerald-600 dark:text-emerald-400 p-0 font-medium">
              {t('tabBilling')} →
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Recent Campaigns Overview Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-sm font-semibold">{t('recentCampaignsTitle')}</CardTitle>
            <CardDescription className="text-xs text-muted-foreground">
              Последние рекламные кампании и их текущая активность
            </CardDescription>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onNavigateTab('campaigns')}
            className="text-xs h-8 text-blue-600 dark:text-blue-400"
          >
            {t('viewAllCampaigns')} ({dashboard?.campaigns?.length || 0}) →
          </Button>
        </CardHeader>
        <CardContent>
          {dashboard?.campaigns && Array.isArray(dashboard.campaigns) && dashboard.campaigns.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-muted-foreground border-b uppercase bg-muted/30 text-[10px]">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold">{t('thCampaignProduct')}</th>
                    <th className="py-2.5 px-3 font-semibold">{t('thStatus')}</th>
                    <th className="py-2.5 px-3 font-semibold">{t('thBudgetSpend')}</th>
                    <th className="py-2.5 px-3 font-semibold">{t('thImpressions')}</th>
                    <th className="py-2.5 px-3 font-semibold">{t('thClicksCtr')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {(dashboard?.campaigns || []).slice(0, 4).map((c) => (
                    <tr key={c.id || (c as any).campaign_id} className="hover:bg-muted/40 transition-colors">
                      <td className="py-2.5 px-3">
                        <div className="font-semibold text-foreground">{c.name}</div>
                        <div className="text-[11px] text-muted-foreground truncate max-w-[220px]">
                          {c.landing_url || 'URL не указан'}
                        </div>
                      </td>
                      <td className="py-2.5 px-3">
                        <Badge
                          variant={c.status === 'active' ? 'default' : 'secondary'}
                          className={`text-[10px] font-normal ${
                            c.status === 'active'
                              ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
                              : ''
                          }`}
                        >
                          {c.status === 'active' ? t('statusActive') : c.status === 'paused' ? t('statusPaused') : c.status}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="font-medium">${toFixedSafe(c.total_spent, 2)}</div>
                        <div className="text-[10px] text-muted-foreground">из ${toFixedSafe(c.total_budget, 2)}</div>
                      </td>
                      <td className="py-2.5 px-3 font-medium">
                        {toLocaleSafe(c.impressions)}
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="font-medium">{toLocaleSafe(c.clicks)}</div>
                        <div className="text-[10px] text-emerald-500">{c.ctr || 0}% CTR</div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center space-y-3">
              <div className="p-3 bg-muted rounded-full text-muted-foreground">
                <Layers className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-sm font-semibold">{t('noCampaignsYet')}</h3>
                <p className="text-xs text-muted-foreground max-w-sm mt-1">
                  {t('noCampaignsDesc')}
                </p>
              </div>
              <Button onClick={onOpenCreateCampaign} size="sm" className="h-8 text-xs bg-blue-600 hover:bg-blue-700 text-white">
                <Plus className="mr-1.5 h-3.5 w-3.5" /> {t('createFirstCampaignBtn')}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
