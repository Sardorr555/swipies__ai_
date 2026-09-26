import React from 'react';
import {
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  Calendar,
  CreditCard,
  RefreshCw,
  Pause,
  Play,
  Plus,
  Zap,
  Download,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import {
  AdTransactionItem,
  SavedPaymentMethodItem,
  UserSubscriptionData,
} from '@/services/ad-service';
import { toFixedSafe } from '../format-utils';

export interface BillingTabProps {
  subscription?: UserSubscriptionData | null;
  loadingSubscriptionAction: boolean;
  savedCards: SavedPaymentMethodItem[];
  balance: number;
  currency: string;
  transactions: AdTransactionItem[];
  onToggleAutoRenew: () => void;
  onOpenCardsModal: () => void;
  onOpenTopUpModal: () => void;
  onExportTransactions: () => void;
}

export const BillingTab: React.FC<BillingTabProps> = ({
  subscription,
  loadingSubscriptionAction,
  savedCards,
  balance,
  currency,
  transactions,
  onToggleAutoRenew,
  onOpenCardsModal,
  onOpenTopUpModal,
  onExportTransactions,
}) => {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        {/* Subscription & Auto-Renewal Card */}
        <Card className="md:col-span-1 border-blue-500/30 bg-gradient-to-br from-blue-950/20 via-background to-background">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-blue-500" />
                Тариф и Автопродление
              </CardTitle>
              <Badge
                variant={
                  subscription?.plan_id === 'pro'
                    ? 'default'
                    : subscription?.plan_id === 'plus'
                    ? 'secondary'
                    : 'outline'
                }
                className="uppercase font-bold text-[10px]"
              >
                {subscription?.plan_id ? subscription.plan_id.toUpperCase() : 'FREE'}
              </Badge>
            </div>
            <CardDescription className="text-xs">
              Управление тарифным планом Swipies AI и привязанными картами
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="p-3 rounded-lg border bg-background/80 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Стоимость:</span>
                <span className="font-bold text-foreground">
                  ${toFixedSafe(subscription?.price_usd, 2)} / мес
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Статус подписки:</span>
                {subscription?.status === 'active' ? (
                  <span className="font-semibold text-emerald-500 flex items-center gap-1">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Активна
                  </span>
                ) : subscription?.status === 'past_due' ? (
                  <span className="font-semibold text-rose-500 flex items-center gap-1">
                    <AlertCircle className="h-3.5 w-3.5" /> Ошибка оплаты
                  </span>
                ) : (
                  <span className="font-semibold text-zinc-400">Базовый (Free)</span>
                )}
              </div>

              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Автопродление:</span>
                {subscription?.auto_renew ? (
                  <Badge className="bg-emerald-600/20 text-emerald-500 hover:bg-emerald-600/30 border-emerald-500/30 text-[10px]">
                    🟢 Включено (каждые 30 дн.)
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-zinc-400 text-[10px]">
                    ⏸️ Отключено
                  </Badge>
                )}
              </div>

              {subscription?.next_billing_time ? (
                <div className="flex justify-between items-center pt-1 border-t border-border/40">
                  <span className="text-muted-foreground flex items-center gap-1">
                    <Calendar className="h-3 w-3" /> Следующее списание:
                  </span>
                  <span className="font-medium text-foreground">
                    {new Date(subscription.next_billing_time).toLocaleDateString()}
                  </span>
                </div>
              ) : null}

              {subscription?.card ? (
                <div className="flex justify-between items-center pt-1 border-t border-border/40">
                  <span className="text-muted-foreground flex items-center gap-1">
                    <CreditCard className="h-3 w-3" /> Основная карта:
                  </span>
                  <span className="font-medium text-foreground">
                    {subscription.card.card_pan_masked}
                  </span>
                </div>
              ) : null}
            </div>

            <div className="flex flex-col gap-2 pt-1">
              {subscription?.plan_id && subscription.plan_id !== 'free' && (
                <Button
                  size="sm"
                  variant={subscription.auto_renew ? 'outline' : 'default'}
                  className="w-full text-xs"
                  onClick={onToggleAutoRenew}
                  disabled={loadingSubscriptionAction}
                  aria-label={subscription.auto_renew ? 'Отключить автопродление' : 'Возобновить автопродление'}
                >
                  {loadingSubscriptionAction ? (
                    <RefreshCw className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                  ) : subscription.auto_renew ? (
                    <>
                      <Pause className="mr-1.5 h-3.5 w-3.5 text-amber-500" /> Отключить автопродление
                    </>
                  ) : (
                    <>
                      <Play className="mr-1.5 h-3.5 w-3.5 text-emerald-500" /> Возобновить автопродление
                    </>
                  )}
                </Button>
              )}

              <Button
                size="sm"
                variant="outline"
                className="w-full text-xs flex items-center justify-center gap-1.5"
                onClick={onOpenCardsModal}
                aria-label="Управление сохранёнными картами"
              >
                <CreditCard className="h-3.5 w-3.5 text-blue-500" />
                Сохранённые карты ({Array.isArray(savedCards) ? savedCards.length : 0})
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Advertiser Wallet Card */}
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle>Advertiser Wallet</CardTitle>
            <CardDescription>Manage advertising funds and payment deposits</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg border bg-muted/40 p-4 text-center">
              <div className="text-xs text-muted-foreground uppercase tracking-wider">Available Balance</div>
              <div className="text-3xl font-extrabold text-emerald-600 dark:text-emerald-400 mt-1">
                ${toFixedSafe(balance, 2)} {currency}
              </div>
            </div>

            <Button
              onClick={onOpenTopUpModal}
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
              aria-label="Пополнить баланс кабинета"
            >
              <Plus className="mr-1.5 h-4 w-4" /> Top-Up Account Balance
            </Button>
          </CardContent>
        </Card>

        {/* Notifications and Security Card */}
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle className="text-sm font-semibold">Уведомления и Безопасность</CardTitle>
            <CardDescription className="text-xs">Защищённые транзакции и СМС-оповещения</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2.5 text-xs text-muted-foreground">
            <div className="p-2.5 rounded border bg-muted/20 space-y-1">
              <div className="font-semibold text-foreground flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-blue-500" /> Безопасная токенизация
              </div>
              <p>Все платежи обрабатываются через сертифицированный шлюз Atmos. Данные карт зашифрованы.</p>
            </div>
            <div className="p-2.5 rounded border bg-muted/20 space-y-1">
              <div className="font-semibold text-foreground flex items-center gap-1.5">
                <Zap className="h-3.5 w-3.5 text-amber-500" /> Мгновенный перерасчёт
              </div>
              <p>При автопродлении все преимущества тарифа (лимиты токенов, отсутствие рекламы) продлеваются без пауз.</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4">
        {/* Recent Transactions Ledger */}
        <Card className="md:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent Transactions</CardTitle>
              <CardDescription>Ledger of deposits and advertising spend deductions</CardDescription>
            </div>
            <Button
              size="sm"
              variant="outline"
              className="text-xs flex items-center gap-1.5"
              onClick={onExportTransactions}
              aria-label="Экспорт транзакций в CSV"
            >
              <Download className="h-3.5 w-3.5" /> Экспорт CSV
            </Button>
          </CardHeader>
          <CardContent>
            {!Array.isArray(transactions) || transactions.length === 0 ? (
              <div className="py-8 text-center text-sm text-muted-foreground">
                No transactions recorded yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b bg-muted/40 uppercase text-muted-foreground">
                    <tr>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Description</th>
                      <th className="py-2.5 px-3">Amount</th>
                      <th className="py-2.5 px-3">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {(transactions || []).map((t) => (
                      <tr key={t.id} className="hover:bg-muted/20">
                        <td className="py-2.5 px-3 font-semibold uppercase">{t.type}</td>
                        <td className="py-2.5 px-3">{t.description}</td>
                        <td className="py-2.5 px-3">
                          <span className={(t.amount ?? 0) >= 0 ? 'text-emerald-500 font-bold' : 'text-zinc-400'}>
                            {(t.amount ?? 0) >= 0 ? `+$${toFixedSafe(t.amount, 2)}` : `-$${toFixedSafe(Math.abs(t.amount ?? 0), 2)}`}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-muted-foreground">
                          {new Date(t.created_at).toLocaleDateString()}
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
    </div>
  );
};

export default BillingTab;
