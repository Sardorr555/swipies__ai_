import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import message from '@/components/ui/message';
import {
  PlacementItem,
  PublisherPayoutItem,
  PublisherProfileData,
} from '@/services/ad-service';
import { toFixedSafe, toLocaleSafe } from '../format-utils';
import {
  ArrowUpRight,
  Bot,
  CheckCircle2,
  Code,
  Coins,
  Copy,
  Key,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
} from 'lucide-react';

export interface PublisherTabProps {
  publisher: PublisherProfileData | null;
  placements: PlacementItem[];
  payouts: PublisherPayoutItem[];
  loadingPublisher?: boolean;
  onRefresh: () => void;
  onRegenerateKey: () => Promise<void>;
  onDeletePlacement: (id: string) => Promise<void>;
  onOpenPlacementModal: () => void;
  onOpenPayoutModal: () => void;
  onOpenSdkSnippetModal: (placement: PlacementItem) => void;
}

export const PublisherTab: React.FC<PublisherTabProps> = ({
  publisher,
  placements,
  payouts,
  loadingPublisher,
  onRefresh,
  onRegenerateKey,
  onDeletePlacement,
  onOpenPlacementModal,
  onOpenPayoutModal,
  onOpenSdkSnippetModal,
}) => {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-muted/30 p-4 rounded-xl border">
        <div>
          <h3 className="text-base font-bold flex items-center gap-2">
            <Bot className="h-5 w-5 text-cyan-500" />
            Монетизация & Партнёрская сеть (Publisher SDK)
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Подключайте свои Telegram-боты, сайты и AI-агенты, показывайте релевантные рекомендации и получайте 70% Revenue Share
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={onOpenPayoutModal}
            size="sm"
            variant="outline"
            className="text-xs flex items-center gap-1.5 border-emerald-500/40 text-emerald-600 hover:bg-emerald-500/10"
          >
            <Coins className="h-3.5 w-3.5" /> Вывести доход (${toFixedSafe(publisher?.balance, 2)})
          </Button>
          <Button
            onClick={onOpenPlacementModal}
            size="sm"
            className="bg-cyan-600 hover:bg-cyan-700 text-white text-xs flex items-center gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" /> + Создать размещение
          </Button>
        </div>
      </div>

      {/* Publisher KPI Cards */}
      <div className="grid gap-3 sm:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Доступно к выводу</CardTitle>
            <Coins className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
              ${toFixedSafe(publisher?.balance, 2)}
            </div>
            <p className="text-[10px] text-muted-foreground mt-0.5">Мгновенный вывод на карты Uzcard / Humo / Visa</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Всего заработано</CardTitle>
            <ArrowUpRight className="h-4 w-4 text-cyan-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${toFixedSafe(publisher?.total_earned, 2)}
            </div>
            <p className="text-[10px] text-muted-foreground mt-0.5">За всё время монетизации</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Выплачено</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${toFixedSafe(publisher?.total_withdrawn, 2)}
            </div>
            <p className="text-[10px] text-muted-foreground mt-0.5">{(Array.isArray(payouts) ? payouts.length : 0)} заявок на выплату</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Доля дохода (RevShare)</CardTitle>
            <Sparkles className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">
              {toFixedSafe((publisher?.default_rev_share ?? 0.70) * 100, 0)}%
            </div>
            <p className="text-[10px] text-muted-foreground mt-0.5">От каждого платного клика и показа</p>
          </CardContent>
        </Card>
      </div>

      {/* API Key Banner */}
      <div className="p-4 bg-muted/40 border rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5">
          <Key className="h-4 w-4 text-cyan-500 shrink-0" />
          <div>
            <span className="font-semibold text-foreground">Ваш уникальный API-ключ паблишера:</span>
            <div className="font-mono bg-background border px-2.5 py-1 rounded mt-1 text-[11px] select-all">
              {publisher?.api_key || 'Загрузка...'}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              if (publisher?.api_key) {
                navigator.clipboard.writeText(publisher.api_key);
                message.success('API-ключ скопирован в буфер обмена');
              }
            }}
            className="h-8 text-xs"
          >
            <Copy className="h-3.5 w-3.5 mr-1" /> Скопировать
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={onRegenerateKey}
            className="h-8 text-xs text-muted-foreground hover:text-foreground"
          >
            <RefreshCw className="h-3.5 w-3.5 mr-1" /> Перевыпустить
          </Button>
        </div>
      </div>

      {/* Placements Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <div>
            <CardTitle className="text-sm font-semibold">Рекламные места (Placements)</CardTitle>
            <CardDescription className="text-xs">
              Подключенные боты, сайты и приложения для показа объявлений
            </CardDescription>
          </div>
          <Button size="sm" variant="ghost" onClick={onRefresh} disabled={loadingPublisher}>
            <RefreshCw className={`h-3.5 w-3.5 ${loadingPublisher ? 'animate-spin' : ''}`} />
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {!Array.isArray(placements) || placements.length === 0 ? (
            <div className="p-8 text-center text-xs text-muted-foreground">
              <Bot className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
              У вас пока нет созданных рекламных мест. Создайте первое размещение для своего Telegram-бота или сайта!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b bg-muted/40 uppercase text-muted-foreground">
                  <tr>
                    <th className="py-2.5 px-4">Название & Канал</th>
                    <th className="py-2.5 px-4">Тип интеграции</th>
                    <th className="py-2.5 px-4">Доля (RevShare)</th>
                    <th className="py-2.5 px-4">Показов</th>
                    <th className="py-2.5 px-4">Кликов</th>
                    <th className="py-2.5 px-4">Заработано ($)</th>
                    <th className="py-2.5 px-4 text-right">Действия</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(placements || []).map((plc) => (
                    <tr key={plc.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 px-4 font-medium">
                        <div>{plc.name}</div>
                        {plc.domain_or_bot && (
                          <div className="text-[11px] text-muted-foreground font-mono">{plc.domain_or_bot}</div>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="outline" className="text-[10px] gap-1">
                          {plc.placement_type === 'telegram_bot' && '🤖 Telegram Bot'}
                          {plc.placement_type === 'web_widget' && '🌐 Web Widget'}
                          {plc.placement_type === 'mobile_app' && '📱 Mobile App'}
                          {plc.placement_type === 'api_agent' && '⚡ AI Agent API'}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 font-semibold text-amber-600">
                        {toFixedSafe((plc.rev_share_rate ?? 0) * 100, 0)}%
                      </td>
                      <td className="py-3 px-4 font-mono">{toLocaleSafe(plc.impressions)}</td>
                      <td className="py-3 px-4 font-mono">{toLocaleSafe(plc.clicks)}</td>
                      <td className="py-3 px-4 font-bold text-emerald-600 dark:text-emerald-400">
                        ${toFixedSafe(plc.earnings, 4)}
                      </td>
                      <td className="py-3 px-4 text-right flex items-center justify-end gap-1.5">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => onOpenSdkSnippetModal(plc)}
                          className="h-7 px-2 text-xs"
                        >
                          <Code className="h-3.5 w-3.5 mr-1" /> Код SDK
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onDeletePlacement(plc.id)}
                          aria-label="Удалить размещение"
                          className="text-red-500 hover:text-red-700 h-7 px-2 text-xs"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Payouts History Card */}
      <Card>
        <CardHeader className="py-4">
          <CardTitle className="text-sm font-semibold">История выплат</CardTitle>
          <CardDescription className="text-xs">
            Все запросы на перевод заработанных средств на банковские карты
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {!Array.isArray(payouts) || payouts.length === 0 ? (
            <div className="p-6 text-center text-xs text-muted-foreground">
              Заявок на выплату пока не было. Накопите минимальный баланс и нажмите «Вывести доход».
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b bg-muted/40 uppercase text-muted-foreground">
                  <tr>
                    <th className="py-2.5 px-4">Дата запроса</th>
                    <th className="py-2.5 px-4">Сумма</th>
                    <th className="py-2.5 px-4">Карта получателя</th>
                    <th className="py-2.5 px-4">Статус</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(payouts || []).map((pay) => (
                    <tr key={pay.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 px-4 text-muted-foreground">
                        {new Date(pay.create_time).toLocaleDateString()} {new Date(pay.create_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="py-3 px-4 font-bold text-foreground">
                        ${toFixedSafe(pay.amount, 2)} {pay.currency}
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px]">
                        {pay.destination_card} {pay.destination_holder && `(${pay.destination_holder})`}
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant={
                            pay.status === 'paid' ? 'default' : pay.status === 'pending' ? 'secondary' : 'destructive'
                          }
                          className="text-[10px]"
                        >
                          {pay.status === 'paid' && '✅ Выплачено'}
                          {pay.status === 'pending' && '⏳ В обработке'}
                          {pay.status === 'approved' && '👍 Одобрено'}
                          {pay.status === 'rejected' && '❌ Отклонено'}
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
    </div>
  );
};

export default PublisherTab;
