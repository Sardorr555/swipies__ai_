import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BlacklistEntryItem, FraudOverviewData } from '@/services/ad-service';
import { toFixedSafe } from '../format-utils';
import {
  Ban,
  Bot,
  DollarSign,
  Plus,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  Trash2,
} from 'lucide-react';

export interface FraudTabProps {
  fraudOverview: FraudOverviewData | null;
  fraudBlacklist: BlacklistEntryItem[];
  loadingFraud?: boolean;
  onRefresh: () => void;
  onOpenBlacklistModal: () => void;
  onRemoveBlacklist: (id: string) => Promise<void> | void;
}

const formatDate = (val?: string | number | null, includeSeconds = true) => {
  if (!val) return '—';
  try {
    const d = new Date(val);
    if (isNaN(d.getTime())) return '—';
    const timeStr = includeSeconds
      ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return `${d.toLocaleDateString()} ${timeStr}`;
  } catch {
    return '—';
  }
};

export const FraudTab: React.FC<FraudTabProps> = ({
  fraudOverview,
  fraudBlacklist,
  loadingFraud,
  onRefresh,
  onOpenBlacklistModal,
  onRemoveBlacklist,
}) => {
  return (
    <div className="space-y-4">
      {/* Header Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-rose-500/5 border border-rose-500/20 rounded-xl">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-rose-500/10 text-rose-500 rounded-lg">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">Anti-Fraud Shield & Защита от скликивания</h3>
            <p className="text-xs text-muted-foreground">
              Многоуровневая система фильтрации ботов, повторных кликов и датацентровых прокси в реальном времени
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={onOpenBlacklistModal}
            className="bg-rose-600 hover:bg-rose-700 text-white text-xs h-8"
          >
            <Ban className="h-3.5 w-3.5 mr-1.5" /> Заблокировать IP
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={onRefresh}
            disabled={loadingFraud}
            aria-label="Обновить данные антифрода"
            className="h-8"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loadingFraud ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Заблокировано фрод-событий</CardTitle>
            <ShieldX className="h-4 w-4 text-rose-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-rose-600 dark:text-rose-400">
              {fraudOverview?.total_blocked_clicks || 0}
            </div>
            <p className="text-[10px] text-muted-foreground mt-0.5">Недействительных кликов нейтрализовано</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Сэкономлено бюджета</CardTitle>
            <DollarSign className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
              ${toFixedSafe(fraudOverview?.total_cost_saved, 2)}
            </div>
            <p className="text-[10px] text-muted-foreground mt-0.5">Сохраненные средства рекламодателя</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Отфильтровано ботов</CardTitle>
            <Bot className="h-4 w-4 text-indigo-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {fraudOverview?.bot_detections || 0}
            </div>
            <p className="text-[10px] text-muted-foreground mt-0.5">Scrapy, headless chrome & curl</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">IP в черном списке</CardTitle>
            <Ban className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {fraudOverview?.active_blacklist_count || 0}
            </div>
            <p className="text-[10px] text-muted-foreground mt-0.5">Активные персональные и системные правила</p>
          </CardContent>
        </Card>
      </div>

      {/* Incidents Log Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <div>
            <CardTitle className="text-sm font-semibold">Журнал перехваченных инцидентов (Live Anti-Fraud Log)</CardTitle>
            <CardDescription className="text-xs">
              Последние заблокированные попытки скликивания, бот-активности и фрод-переходов
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {!fraudOverview?.recent_logs || !Array.isArray(fraudOverview.recent_logs) || fraudOverview.recent_logs.length === 0 ? (
            <div className="p-8 text-center text-xs text-muted-foreground">
              <ShieldCheck className="h-8 w-8 mx-auto mb-2 text-emerald-500/60" />
              Подозрительной активности не зафиксировано. Все клики соответствуют стандартам чистоты трафика.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b bg-muted/40 uppercase text-muted-foreground">
                  <tr>
                    <th className="py-2.5 px-4">Время</th>
                    <th className="py-2.5 px-4">Кампания</th>
                    <th className="py-2.5 px-4">Причина блокировки</th>
                    <th className="py-2.5 px-4">IP Hash / Хэш устройства</th>
                    <th className="py-2.5 px-4">User-Agent / Сигнатура</th>
                    <th className="py-2.5 px-4">Сэкономлено</th>
                    <th className="py-2.5 px-4">Статус</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(fraudOverview.recent_logs || []).map((log) => (
                    <tr key={log.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 px-4 text-muted-foreground whitespace-nowrap">
                        {formatDate(log.create_time)}
                      </td>
                      <td className="py-3 px-4 font-medium text-foreground">
                        {log.campaign_name}
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant="outline"
                          className={
                            log.reason === 'bot_user_agent'
                              ? 'bg-indigo-500/10 text-indigo-500 border-indigo-500/30 text-[10px]'
                              : log.reason === 'blacklist_ip'
                              ? 'bg-rose-500/10 text-rose-500 border-rose-500/30 text-[10px]'
                              : 'bg-amber-500/10 text-amber-500 border-amber-500/30 text-[10px]'
                          }
                        >
                          {log.reason === 'bot_user_agent' && '🤖 Бот / Web Scraper'}
                          {log.reason === 'blacklist_ip' && '🚫 Заблокированный IP'}
                          {log.reason === 'rapid_repeat_clicks' && '⚡ Скликивание (>2 в мин)'}
                          {log.reason === 'rate_limit_exceeded' && '⏱️ Превышен лимит запросов'}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-muted-foreground">
                        {log.ip_hash ? log.ip_hash.slice(0, 16) + '...' : '—'}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground max-w-[200px] truncate text-[11px]" title={log.user_agent}>
                        {log.user_agent}
                      </td>
                      <td className="py-3 px-4 font-semibold text-emerald-600 dark:text-emerald-400">
                        +${toFixedSafe(log.cost_saved, 2)}
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="secondary" className="text-[10px] bg-emerald-500/10 text-emerald-600 border-emerald-500/20">
                          🛡️ Заблокировано (0$ списано)
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* IP Blacklist Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <div>
            <CardTitle className="text-sm font-semibold">Черный список IP и подсетей (IP Blacklist)</CardTitle>
            <CardDescription className="text-xs">
              Заблокированные адреса не могут скликивать ваши рекламные кампании
            </CardDescription>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={onOpenBlacklistModal}
            className="text-xs h-7"
          >
            <Plus className="h-3.5 w-3.5 mr-1" /> Добавить IP
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {!Array.isArray(fraudBlacklist) || fraudBlacklist.length === 0 ? (
            <div className="p-6 text-center text-xs text-muted-foreground">
              Черный список пуст. При обнаружении подозрительной активности система заблокирует IP автоматически, либо вы можете добавить его вручную.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b bg-muted/40 uppercase text-muted-foreground">
                  <tr>
                    <th className="py-2.5 px-4">IP-адрес / Подсеть</th>
                    <th className="py-2.5 px-4">Тип правила</th>
                    <th className="py-2.5 px-4">Причина блокировки</th>
                    <th className="py-2.5 px-4">Срок действия</th>
                    <th className="py-2.5 px-4 text-right">Действия</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(fraudBlacklist || []).map((entry) => (
                    <tr key={entry.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 px-4 font-mono font-bold text-foreground">
                        {entry.ip_address}
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={entry.is_system ? 'secondary' : 'default'} className="text-[10px]">
                          {entry.is_system ? '🌐 Системный глобальный' : '👤 Персональный'}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {entry.reason}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground text-[11px]">
                        {entry.auto_expires_at ? (
                          <span>Истекает {formatDate(entry.auto_expires_at, false)}</span>
                        ) : (
                          <span className="text-amber-500 font-medium">Бессрочно</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {!entry.is_system && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => onRemoveBlacklist(entry.id)}
                            aria-label="Разблокировать IP"
                            className="text-red-500 hover:text-red-700 h-7 px-2 text-xs"
                          >
                            <Trash2 className="h-3.5 w-3.5 mr-1" /> Разблокировать
                          </Button>
                        )}
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
