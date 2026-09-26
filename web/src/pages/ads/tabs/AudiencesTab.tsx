import React from 'react';
import {
  Fingerprint,
  GitBranch,
  Database,
  Plus,
  Users,
  TrendingUp,
  Calendar,
  AlertCircle,
  Target,
  RefreshCw,
  Trash2,
  Trophy,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import {
  AudienceSegmentItem,
  LookalikeAudienceItem,
  CustomerLtvOverviewResponse,
} from '@/services/ad-service';
import { toFixedSafe, toLocaleSafe } from '../format-utils';

export interface AudiencesTabProps {
  ltvOverview: CustomerLtvOverviewResponse | null;
  lookalikes: LookalikeAudienceItem[];
  audiences: AudienceSegmentItem[];
  loadingLookalikes: boolean;
  loadingAudiences: boolean;
  onOpenCreateLookalikeModal: () => void;
  onOpenLtvSyncModal: () => void;
  onOpenCreateAudienceModal: () => void;
  onRefreshLookalikes: () => void;
  onRefreshAudiences: () => void;
  onDeleteLookalike: (id: string) => void;
  onDeleteAudience: (id: string) => void;
}

export const AudiencesTab: React.FC<AudiencesTabProps> = ({
  ltvOverview,
  lookalikes,
  audiences,
  loadingLookalikes,
  loadingAudiences,
  onOpenCreateLookalikeModal,
  onOpenLtvSyncModal,
  onOpenCreateAudienceModal,
  onRefreshLookalikes,
  onRefreshAudiences,
  onDeleteLookalike,
  onDeleteAudience,
}) => {
  return (
    <div className="space-y-6">
      {/* Top Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-muted/30 p-4 rounded-xl border">
        <div>
          <h3 className="text-base font-bold flex items-center gap-2">
            <Fingerprint className="h-5 w-5 text-emerald-500" />
            Сегменты аудиторий, Lookalike AI и Прогнозный LTV
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Пиксель-ретаргетинг, расширение охвата через Lookalike-векторы и поведенческий скоринг ценности клиентов (RFM / Churn Risk)
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            onClick={onOpenCreateLookalikeModal}
            size="sm"
            variant="outline"
            className="border-indigo-500/30 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-500/10 text-xs flex items-center gap-1.5"
          >
            <GitBranch className="h-3.5 w-3.5" /> + Lookalike AI
          </Button>
          <Button
            onClick={onOpenLtvSyncModal}
            size="sm"
            variant="outline"
            className="border-amber-500/30 text-amber-600 dark:text-amber-400 hover:bg-amber-500/10 text-xs flex items-center gap-1.5"
          >
            <Database className="h-3.5 w-3.5" /> + Синхронизация клиента
          </Button>
          <Button
            onClick={onOpenCreateAudienceModal}
            size="sm"
            className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs flex items-center gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" /> + Создать аудиторию
          </Button>
        </div>
      </div>

      {/* Predictive LTV & RFM Metrics Scorecard */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-emerald-500/20 bg-gradient-to-br from-emerald-500/5 to-transparent">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Профилей в когортах</span>
              <Users className="h-4 w-4 text-emerald-500" />
            </div>
            <div className="text-2xl font-bold text-foreground mt-1">
              {ltvOverview?.total_customers || 0}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Историческая выручка: ${toFixedSafe(ltvOverview?.total_historical_revenue, 2)}
            </p>
          </CardContent>
        </Card>

        <Card className="border-indigo-500/20 bg-gradient-to-br from-indigo-500/5 to-transparent">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Ср. Прогнозный LTV (90d)</span>
              <TrendingUp className="h-4 w-4 text-indigo-500" />
            </div>
            <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 mt-1">
              ${toFixedSafe(ltvOverview?.avg_predicted_ltv_90d, 2)}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">Ожидаемый доход с покупателя</p>
          </CardContent>
        </Card>

        <Card className="border-cyan-500/20 bg-gradient-to-br from-cyan-500/5 to-transparent">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Ср. Прогнозный LTV (365d)</span>
              <Calendar className="h-4 w-4 text-cyan-500" />
            </div>
            <div className="text-2xl font-bold text-cyan-600 dark:text-cyan-400 mt-1">
              ${toFixedSafe(ltvOverview?.avg_predicted_ltv_365d, 2)}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">Годовая ценность клиента</p>
          </CardContent>
        </Card>

        <Card className="border-rose-500/20 bg-gradient-to-br from-rose-500/5 to-transparent">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Ср. Риск оттока (Churn)</span>
              <AlertCircle className="h-4 w-4 text-rose-500" />
            </div>
            <div className="text-2xl font-bold text-rose-600 dark:text-rose-400 mt-1">
              {ltvOverview?.avg_churn_risk_percent || 0}%
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">Вероятность потери активности</p>
          </CardContent>
        </Card>
      </div>

      {/* RFM Behavioral Cohorts Breakdown */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Target className="h-4 w-4 text-emerald-500" />
            RFM Сегментация базы (Recency, Frequency, Monetary)
          </CardTitle>
          <CardDescription className="text-xs">
            Автоматическая кластеризация покупателей для персонализированного таргетинга и Win-Back кампаний
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
            {[
              { key: 'champions', label: '🏆 Чемпионы', desc: 'Часто и много', color: 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30' },
              { key: 'loyal', label: '💎 Лояльные', desc: 'Стабильные заказы', color: 'bg-blue-500/10 text-blue-600 border-blue-500/30' },
              { key: 'potential_loyalist', label: '🚀 Потенциал', desc: 'Недавние с чеком', color: 'bg-indigo-500/10 text-indigo-600 border-indigo-500/30' },
              { key: 'recent_customers', label: '🌱 Новички', desc: 'Первый заказ', color: 'bg-cyan-500/10 text-cyan-600 border-cyan-500/30' },
              { key: 'at_risk', label: '⚠️ В зоне риска', desc: 'Давно не покупали', color: 'bg-amber-500/10 text-amber-600 border-amber-500/30' },
              { key: 'hibernating', label: '💤 Спящие', desc: 'Редкие клиенты', color: 'bg-purple-500/10 text-purple-600 border-purple-500/30' },
              { key: 'lost', label: '❌ Потерянные', desc: 'Минимальный чек', color: 'bg-rose-500/10 text-rose-600 border-rose-500/30' },
            ].map((item) => (
              <div key={item.key} className={`p-3 rounded-lg border flex flex-col justify-between ${item.color}`}>
                <div>
                  <span className="text-xs font-bold block">{item.label}</span>
                  <span className="text-[10px] opacity-80 block mt-0.5">{item.desc}</span>
                </div>
                <div className="text-lg font-extrabold mt-2">
                  {ltvOverview?.segment_counts?.[item.key] || 0}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* AI Lookalike Audiences Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <div>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-indigo-500" />
              Lookalike AI-аудитории (Похожая аудитория)
            </CardTitle>
            <CardDescription className="text-xs">
              Расширение целевой базы на основе векторов сходства поисковых интентов и интересов семенных сегментов
            </CardDescription>
          </div>
          <Button size="sm" variant="ghost" onClick={onRefreshLookalikes} disabled={loadingLookalikes}>
            <RefreshCw className={`h-3.5 w-3.5 ${loadingLookalikes ? 'animate-spin' : ''}`} />
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {!Array.isArray(lookalikes) || lookalikes.length === 0 ? (
            <div className="p-8 text-center text-xs text-muted-foreground">
              <GitBranch className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
              У вас пока нет созданных Lookalike аудиторий. Создайте расширенную аудиторию на основе VIP-покупателей!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b bg-muted/40 uppercase text-muted-foreground">
                  <tr>
                    <th className="py-2.5 px-4">Название Lookalike</th>
                    <th className="py-2.5 px-4">Исходный сегмент (Seed)</th>
                    <th className="py-2.5 px-4 text-center">Сходство (%)</th>
                    <th className="py-2.5 px-4">Регион</th>
                    <th className="py-2.5 px-4">Размер Seed</th>
                    <th className="py-2.5 px-4 font-bold text-indigo-600">Прогнозный охват (Reach)</th>
                    <th className="py-2.5 px-4">Статус</th>
                    <th className="py-2.5 px-4 text-right">Действия</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(lookalikes || []).map((lal) => (
                    <tr key={lal.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 px-4 font-semibold text-foreground">{lal.name}</td>
                      <td className="py-3 px-4 text-muted-foreground">{lal.source_segment_name || 'Seed Segment'}</td>
                      <td className="py-3 px-4 text-center">
                        <Badge variant="outline" className="bg-indigo-500/10 text-indigo-600 border-indigo-500/20 font-bold">
                          {lal.similarity_ratio}%
                        </Badge>
                      </td>
                      <td className="py-3 px-4 font-mono">{lal.country}</td>
                      <td className="py-3 px-4">{toLocaleSafe(lal.seed_audience_size)} чел.</td>
                      <td className="py-3 px-4 font-bold text-indigo-600 dark:text-indigo-400 font-mono">
                        ~{toLocaleSafe(lal.estimated_reach)} чел.
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 text-[10px]">
                          🟢 Готово к показу
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onDeleteLookalike(lal.id)}
                          className="text-red-500 hover:text-red-700 h-7 px-2 text-xs"
                        >
                          <Trash2 className="h-3.5 w-3.5 mr-1" /> Удалить
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

      {/* Seed Audiences & Retargeting Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <div>
            <CardTitle className="text-sm font-semibold">Сегменты пикселя и ретаргетинга</CardTitle>
            <CardDescription className="text-xs">
              Списки пользователей для прямого таргетинга, исключения или генерации Lookalike
            </CardDescription>
          </div>
          <Button size="sm" variant="ghost" onClick={onRefreshAudiences} disabled={loadingAudiences}>
            <RefreshCw className={`h-3.5 w-3.5 ${loadingAudiences ? 'animate-spin' : ''}`} />
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {!Array.isArray(audiences) || audiences.length === 0 ? (
            <div className="p-8 text-center text-xs text-muted-foreground">
              <Fingerprint className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
              У вас пока нет созданных сегментов аудиторий. Создайте первую аудиторию ретаргетинга!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b bg-muted/40 uppercase text-muted-foreground">
                  <tr>
                    <th className="py-2.5 px-4">Название аудитории</th>
                    <th className="py-2.5 px-4">Тип сбора</th>
                    <th className="py-2.5 px-4">Правило / Событие</th>
                    <th className="py-2.5 px-4">Участников (Users)</th>
                    <th className="py-2.5 px-4">Дата создания</th>
                    <th className="py-2.5 px-4 text-right">Действия</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(audiences || []).map((aud) => (
                    <tr key={aud.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 px-4 font-medium">
                        <div>{aud.name}</div>
                        {aud.description && (
                          <div className="text-[11px] text-muted-foreground">{aud.description}</div>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="outline" className="text-[10px]">
                          {aud.rule_type === 'pixel_event' ? '🌐 Событие Пикселя' : '📝 Пользовательский'}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px]">
                        {aud.rule_config?.event_type || 'all_events'}
                      </td>
                      <td className="py-3 px-4 font-bold text-emerald-600 dark:text-emerald-400">
                        {toLocaleSafe(aud.member_count)}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {new Date(aud.create_time).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onDeleteAudience(aud.id)}
                          className="text-red-500 hover:text-red-700 h-7 px-2 text-xs"
                        >
                          <Trash2 className="h-3.5 w-3.5 mr-1" /> Удалить
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

      {/* High-pLTV Top Customer Cohort Table */}
      {ltvOverview?.top_customers && Array.isArray(ltvOverview.top_customers) && ltvOverview.top_customers.length > 0 && (
        <Card>
          <CardHeader className="py-4">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Trophy className="h-4 w-4 text-amber-500" />
              Топ VIP-профили по Прогнозному LTV (pLTV Top-25)
            </CardTitle>
            <CardDescription className="text-xs">
              Клиенты с наибольшей прогнозируемой ценностью на ближайшие 90 и 365 дней
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b bg-muted/40 uppercase text-muted-foreground">
                  <tr>
                    <th className="py-2.5 px-4">Клиент / Visitor</th>
                    <th className="py-2.5 px-4">RFM Когорта</th>
                    <th className="py-2.5 px-4 text-center">Заказов</th>
                    <th className="py-2.5 px-4 text-right">Выручка ($)</th>
                    <th className="py-2.5 px-4 text-right">Ср. чек ($)</th>
                    <th className="py-2.5 px-4 text-right font-bold text-indigo-600">Прогнозный LTV (90d)</th>
                    <th className="py-2.5 px-4 text-right font-bold text-emerald-600">Годовой LTV (365d)</th>
                    <th className="py-2.5 px-4 text-center">Риск оттока</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(ltvOverview.top_customers || []).map((cust) => (
                    <tr key={cust.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium">
                        {cust.customer_identifier || cust.visitor_id?.substring(0, 16) || '—'}
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="outline" className="text-[10px] uppercase font-bold">
                          {cust.rfm_segment?.replace('_', ' ') ?? '—'}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-center font-bold">{cust.total_orders}</td>
                      <td className="py-3 px-4 text-right font-mono">${toFixedSafe(cust.rfm_monetary_val, 2)}</td>
                      <td className="py-3 px-4 text-right font-mono">${toFixedSafe(cust.avg_order_value, 2)}</td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-indigo-600 dark:text-indigo-400">
                        ${toFixedSafe(cust.predicted_ltv_90d, 2)}
                      </td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                        ${toFixedSafe(cust.predicted_ltv_365d, 2)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className={cust.churn_risk_score > 0.5 ? 'text-rose-500 font-bold' : 'text-emerald-500 font-medium'}>
                          {toFixedSafe((cust.churn_risk_score ?? 0) * 100, 0)}%
                        </span>
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
