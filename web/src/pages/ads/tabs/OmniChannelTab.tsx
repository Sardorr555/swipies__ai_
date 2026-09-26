import React from 'react';
import {
  Share2,
  Plus,
  Send,
  DollarSign,
  TrendingUp,
  Activity,
  Target,
  BarChart3,
  Layers,
  Trash2,
  Clock,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Bar,
} from 'recharts';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import {
  CrossPlatformAnalyticsResponse,
  OmniAccountItem,
  OmniPlatformType,
  OmniSyncJobItem,
} from '@/services/ad-service';
import { toFixedSafe, toLocaleSafe } from '../format-utils';

export interface OmniChannelTabProps {
  crossPlatformAnalytics: CrossPlatformAnalyticsResponse | null;
  omniAccounts: OmniAccountItem[];
  omniSyncJobs: OmniSyncJobItem[];
  testingOmniAccountId: string | null;
  onOpenConnectAccount: (platform?: OmniPlatformType) => void;
  onOpenExportModal: () => void;
  onTestConnection: (accountId: string) => void;
  onDisconnectAccount: (accountId: string) => void;
}

export const OmniChannelTab: React.FC<OmniChannelTabProps> = ({
  crossPlatformAnalytics,
  omniAccounts,
  omniSyncJobs,
  testingOmniAccountId,
  onOpenConnectAccount,
  onOpenExportModal,
  onTestConnection,
  onDisconnectAccount,
}) => {
  return (
    <div className="space-y-6">
      {/* Top Hero Banner */}
      <div className="rounded-2xl border bg-gradient-to-r from-blue-500/10 via-indigo-500/10 to-sky-500/10 dark:from-blue-950/30 dark:via-indigo-950/30 dark:to-sky-950/30 p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600 text-white font-bold shadow-lg shadow-blue-500/20 shrink-0">
              <Share2 className="h-7 w-7" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xl font-black tracking-tight text-foreground">
                  Кросс-платформенный Мост (Omni-Channel Ads Bridge)
                </h3>
                <Badge variant="secondary" className="text-xs bg-blue-500/10 text-blue-600 dark:text-blue-400 font-bold border border-blue-500/20">
                  🌐 Telegram • Meta • Google • TikTok
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                1-Click экспорт ваших AI кампаний и сегментов аудиторий в Telegram Ads, Meta Marketing API, Google Ads и TikTok с объединенной сквозной аналитикой и Blended ROAS.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onOpenConnectAccount('telegram_ads')}
              className="text-xs border-blue-500/30 text-blue-600 dark:text-blue-400 hover:bg-blue-500/10"
            >
              <Plus className="h-3.5 w-3.5 mr-1" /> Подключить кабинет
            </Button>
            <Button
              size="sm"
              onClick={onOpenExportModal}
              className="text-xs bg-blue-600 hover:bg-blue-700 text-white shadow-sm"
            >
              <Send className="h-3.5 w-3.5 mr-1" /> 🚀 1-Click Экспорт Кампании
            </Button>
          </div>
        </div>
      </div>

      {/* 4 Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-blue-500/20 bg-blue-50/20 dark:bg-blue-950/10">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Общий расход (Blended Spend)</span>
              <DollarSign className="h-4 w-4 text-blue-500" />
            </div>
            <div className="text-2xl font-bold text-foreground mt-1">
              ${toFixedSafe(crossPlatformAnalytics?.total_blended_spend, 2)}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Подключено сетей:{' '}
              <b>{crossPlatformAnalytics?.connected_accounts_count || 0} платформ</b>
            </p>
          </CardContent>
        </Card>

        <Card className="border-emerald-500/20 bg-emerald-50/20 dark:bg-emerald-950/10">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Blended ROAS & Эффективность</span>
              <TrendingUp className="h-4 w-4 text-emerald-500" />
            </div>
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
              {crossPlatformAnalytics?.blended_roas || '0.00'}x
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Сквозная окупаемость инвестиций в трафик
            </p>
          </CardContent>
        </Card>

        <Card className="border-indigo-500/20 bg-indigo-50/20 dark:bg-indigo-950/10">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Кросс-показы & Blended CTR</span>
              <Activity className="h-4 w-4 text-indigo-500" />
            </div>
            <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 mt-1">
              {toLocaleSafe(crossPlatformAnalytics?.total_blended_impressions)}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Кликов: <b>{toLocaleSafe(crossPlatformAnalytics?.total_blended_clicks)}</b> ({crossPlatformAnalytics?.blended_ctr || 0}% CTR)
            </p>
          </CardContent>
        </Card>

        <Card className="border-purple-500/20 bg-purple-50/20 dark:bg-purple-950/10">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Конверсии & Blended CPA</span>
              <Target className="h-4 w-4 text-purple-500" />
            </div>
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400 mt-1">
              {crossPlatformAnalytics?.total_blended_conversions || 0}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Ср. стоимость действия (CPA):{' '}
              <b>${toFixedSafe(crossPlatformAnalytics?.blended_cpa, 2)}</b>
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Cross-Platform Breakdown Chart */}
      {crossPlatformAnalytics && crossPlatformAnalytics.networks && Array.isArray(crossPlatformAnalytics.networks) && (
        <Card>
          <CardHeader className="py-4">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-blue-500" /> Сравнение Результативности по Рекламным Сетям
            </CardTitle>
            <CardDescription className="text-xs">
              Распределение бюджетов, кликов и стоимости конверсии между каналами (Swipies AI Native vs Внешние сети)
            </CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={crossPlatformAnalytics.networks}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(val: any, name: string) => [name === 'spend' ? `$${val}` : val, name === 'spend' ? 'Расход ($)' : name === 'conversions' ? 'Конверсии' : 'Клики']} />
                  <Bar dataKey="spend" fill="#3b82f6" radius={[4, 4, 0, 0]} name="spend" />
                  <Bar dataKey="conversions" fill="#10b981" radius={[4, 4, 0, 0]} name="conversions" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Connected Ad Accounts List */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <div>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Layers className="h-4 w-4 text-blue-500" /> Подключенные Рекламные Кабинеты
            </CardTitle>
            <CardDescription className="text-xs">
              Управление API интеграциями с Telegram Ads, Meta, Google Ads и TikTok
            </CardDescription>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              onClick={() => onOpenConnectAccount()}
              className="text-xs bg-blue-600 hover:bg-blue-700 text-white"
            >
              <Plus className="h-3.5 w-3.5 mr-1" /> Добавить кабинет
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {!Array.isArray(omniAccounts) || omniAccounts.length === 0 ? (
            <div className="py-12 text-center text-xs text-muted-foreground">
              <Share2 className="h-8 w-8 mx-auto text-muted-foreground/40 mb-2" />
              Нет подключенных рекламных кабинетов. Нажмите «Добавить кабинет», чтобы настроить синхронизацию с Telegram Ads, Meta или Google.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b bg-muted/40 uppercase text-muted-foreground">
                  <tr>
                    <th className="py-2.5 px-4">Платформа / Аккаунт</th>
                    <th className="py-2.5 px-4">External Account ID</th>
                    <th className="py-2.5 px-4">Экспортировано кампаний</th>
                    <th className="py-2.5 px-4">Валюта</th>
                    <th className="py-2.5 px-4">Статус API</th>
                    <th className="py-2.5 px-4 text-right">Действия</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(omniAccounts || []).map((acc) => (
                    <tr key={acc.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 px-4 font-bold text-foreground">
                        <div className="flex items-center gap-2">
                          <span className="text-base">
                            {acc.platform === 'telegram_ads'
                              ? '✈️'
                              : acc.platform === 'meta_ads'
                              ? '♾️'
                              : acc.platform === 'google_ads'
                              ? '🔍'
                              : acc.platform === 'tiktok_ads'
                              ? '🎵'
                              : '🌐'}
                          </span>
                          <div>
                            <div>{acc.account_name}</div>
                            <div className="text-[10px] text-muted-foreground">
                              {acc.platform_display_name}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4 font-mono text-muted-foreground">
                        {acc.account_id_external || '—'}
                      </td>
                      <td className="py-3 px-4 font-mono font-bold text-foreground">
                        {acc.total_campaigns_exported}
                      </td>
                      <td className="py-3 px-4 font-bold">
                        <Badge variant="outline" className="text-[10px]">
                          {acc.default_currency}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant="secondary"
                          className={`text-[10px] uppercase font-bold ${
                            acc.auth_status === 'connected'
                              ? 'bg-emerald-500/10 text-emerald-600'
                              : 'bg-rose-500/10 text-rose-600'
                          }`}
                        >
                          {acc.auth_status === 'connected' ? '🟢 Подключен' : '🔴 Ошибка'}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => onTestConnection(acc.id)}
                            disabled={testingOmniAccountId === acc.id}
                            className="h-7 text-xs border-blue-500/30 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/20"
                          >
                            {testingOmniAccountId === acc.id ? 'Пинг...' : '📡 Тест API'}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={onOpenExportModal}
                            className="h-7 text-xs border-emerald-500/30 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/20"
                          >
                            🚀 Экспорт
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => onDisconnectAccount(acc.id)}
                            className="h-7 text-xs text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/20"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
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

      {/* Sync Jobs History */}
      {Array.isArray(omniSyncJobs) && omniSyncJobs.length > 0 && (
        <Card>
          <CardHeader className="py-4">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" /> Журнал Экспорта и Синхронизации (Sync Jobs)
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b bg-muted/40 uppercase text-muted-foreground">
                  <tr>
                    <th className="py-2.5 px-4">Job ID / Дата</th>
                    <th className="py-2.5 px-4">Тип операции</th>
                    <th className="py-2.5 px-4">Платформа</th>
                    <th className="py-2.5 px-4">Remote Campaign / Audience ID</th>
                    <th className="py-2.5 px-4 text-right">Статус</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(omniSyncJobs || []).slice(0, 10).map((job) => (
                    <tr key={job.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-2.5 px-4">
                        <div className="font-mono font-bold text-foreground">{job.id}</div>
                        <div className="text-[10px] text-muted-foreground">
                          {new Date(job.create_time * 1000).toLocaleString()}
                        </div>
                      </td>
                      <td className="py-2.5 px-4">
                        <Badge variant="secondary" className="text-[10px]">
                          {job.job_type === 'export_campaign' ? '🚀 Экспорт кампании' : '👥 Синхронизация аудитории'}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-4 uppercase font-bold text-foreground">
                        {job.platform?.replace('_', ' ') ?? '—'}
                      </td>
                      <td className="py-2.5 px-4 font-mono text-muted-foreground">
                        {job.external_campaign_id || '—'}
                      </td>
                      <td className="py-2.5 px-4 text-right">
                        <Badge className="text-[10px] bg-emerald-500/10 text-emerald-600 font-bold">
                          ✅ {job.status}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
