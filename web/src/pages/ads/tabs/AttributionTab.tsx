import React from 'react';
import {
  Route,
  Compass,
  Target,
  TrendingUp,
  Footprints,
  Clock,
  Filter,
  Share2,
  GitBranch,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  AttributionModelType,
  AttributionSummaryResponse,
  ConversionJourneyPath,
  FunnelAnalyticsResponse,
  CampaignAttributionCredit,
  FunnelStageItem,
} from '@/services/ad-service';
import { toFixedSafe, toLocaleSafe } from '../format-utils';

export interface AttributionTabProps {
  mtaModel: AttributionModelType;
  mtaDays: number;
  mtaSummary: AttributionSummaryResponse | null;
  mtaPaths: ConversionJourneyPath[];
  funnelData: FunnelAnalyticsResponse | null;
  loadingMta: boolean;
  loadingFunnel: boolean;
  onMtaModelChange: (model: AttributionModelType) => void;
  onMtaDaysChange: (days: number) => void;
  onRefresh: () => void;
}

export const AttributionTab: React.FC<AttributionTabProps> = ({
  mtaModel,
  mtaDays,
  mtaSummary,
  mtaPaths,
  funnelData,
  loadingMta,
  loadingFunnel,
  onMtaModelChange,
  onMtaDaysChange,
  onRefresh,
}) => {
  // Consistency checks: detect if cached/current data is stale relative to user's selected model or window
  const isMtaStale = Boolean(
    loadingMta ||
      (mtaSummary?.model_selected && mtaSummary.model_selected !== mtaModel) ||
      (mtaSummary?.days && mtaSummary.days !== mtaDays),
  );

  const isFunnelStale = Boolean(
    loadingFunnel || (funnelData?.days && funnelData.days !== mtaDays),
  );

  // The model the current summary data actually represents (avoids attributing stale numbers to a newly clicked model)
  const displayModelForData = mtaSummary?.model_selected || mtaModel;

  return (
    <div className="space-y-6">
      {/* Header toolbar & Model Selector */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-muted/30 p-4 rounded-xl border">
        <div>
          <h3 className="text-base font-bold flex items-center gap-2">
            <Route className="h-5 w-5 text-indigo-500" />
            Мультитач Аттрибуция & Карта Пути Клиента (MTA)
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Оценка ценности каждого касания в цепочке конверсий: от первого открытия в AI-чате до финальной оплаты
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Model Selector Buttons */}
          <div className="flex items-center gap-1 bg-background p-1 rounded-lg border text-xs" role="toolbar" aria-label="Модели атрибуции">
            {[
              { id: 'position_based', label: 'U-Shaped (40/20/40)' },
              { id: 'time_decay', label: 'Time-Decay (7d)' },
              { id: 'linear', label: 'Линейная (1/N)' },
              { id: 'first_touch', label: 'First Touch' },
              { id: 'last_touch', label: 'Last Touch' },
            ].map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => onMtaModelChange(m.id as AttributionModelType)}
                className={`px-2.5 py-1 rounded-md font-semibold transition-all ${
                  mtaModel === m.id
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
                aria-pressed={mtaModel === m.id}
              >
                {m.label}
              </button>
            ))}
          </div>

          {/* Time window selector */}
          <div className="flex items-center gap-1 bg-background p-1 rounded-lg border text-xs" role="toolbar" aria-label="Период анализа">
            {[7, 14, 30, 90].map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => onMtaDaysChange(d)}
                className={`px-2.5 py-1 rounded-md font-semibold transition-all ${
                  mtaDays === d
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
                aria-pressed={mtaDays === d}
              >
                {d} дней
              </button>
            ))}
            <Button
              size="sm"
              variant="ghost"
              className="h-7 px-2 text-xs"
              onClick={onRefresh}
              title="Обновить аналитику"
              aria-label="Обновить аналитику"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loadingMta || loadingFunnel ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </div>

      {/* Model Explanation Callout */}
      <div className="p-3.5 rounded-lg border border-indigo-500/20 bg-indigo-500/5 text-xs flex items-start gap-2.5">
        <Compass className="h-4 w-4 text-indigo-500 mt-0.5 shrink-0" />
        <div className="space-y-0.5">
          <span className="font-semibold text-foreground">
            {mtaModel === 'position_based' && 'U-Shaped / Position-Based модель:'}
            {mtaModel === 'time_decay' && 'Time-Decay (Временной распад) модель:'}
            {mtaModel === 'linear' && 'Линейная (Linear) модель:'}
            {mtaModel === 'first_touch' && 'First Touch (Первое касание) модель:'}
            {mtaModel === 'last_touch' && 'Last Touch (Последнее касание) модель:'}
          </span>
          <span className="text-muted-foreground ml-1">
            {mtaModel === 'position_based' &&
              '40% ценности получает кампания первого знакомства с продуктом, 40% — кампания закрытия сделки, а 20% поровну распределяются между поддерживающими касаниями (nurturing).'}
            {mtaModel === 'time_decay' &&
              'Касания, произошедшие ближе к моменту покупки, получают экспоненциально больший вес (период полураспада 7 дней).'}
            {mtaModel === 'linear' &&
              'Каждое взаимодействие в цепочке пользователя получает строго равную долю ценности (1/N) конверсии.'}
            {mtaModel === 'first_touch' &&
              '100% выручки и конверсии приписывается первому каналу привлечения (Top-of-Funnel discovery).'}
            {mtaModel === 'last_touch' &&
              '100% ценности приписывается последнему клику перед совершением целевого действия.'}
          </span>
        </div>
      </div>

      {/* KPI Cards Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-indigo-500/20 bg-gradient-to-br from-indigo-500/5 to-transparent">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Всего конверсий (MTA)</span>
              <Target className="h-4 w-4 text-indigo-500" />
            </div>
            <div className="text-2xl font-bold text-foreground mt-1">
              {mtaSummary?.total_conversions || 0}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">Верифицированных заказов</p>
          </CardContent>
        </Card>

        <Card
          className={`border-emerald-500/20 bg-gradient-to-br from-emerald-500/5 to-transparent transition-opacity duration-200 ${
            isMtaStale ? 'opacity-70' : 'opacity-100'
          }`}
        >
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Аттрибутированная выручка</span>
              {isMtaStale ? (
                <RefreshCw className="h-4 w-4 text-emerald-500 animate-spin" />
              ) : (
                <TrendingUp className="h-4 w-4 text-emerald-500" />
              )}
            </div>
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
              ${toFixedSafe(mtaSummary?.total_revenue, 2)}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              По модели {displayModelForData.replace('_', ' ')}
              {isMtaStale && ' (обновление...)'}
            </p>
          </CardContent>
        </Card>

        <Card className="border-cyan-500/20 bg-gradient-to-br from-cyan-500/5 to-transparent">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Касаний до покупки</span>
              <Footprints className="h-4 w-4 text-cyan-500" />
            </div>
            <div className="text-2xl font-bold text-cyan-600 dark:text-cyan-400 mt-1">
              {mtaSummary?.avg_touchpoints_per_conversion || 1.0}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">Средняя длина пути клиента</p>
          </CardContent>
        </Card>

        <Card className="border-amber-500/20 bg-gradient-to-br from-amber-500/5 to-transparent">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Цикл сделки (Time-to-Convert)</span>
              <Clock className="h-4 w-4 text-amber-500" />
            </div>
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">
              {mtaSummary?.avg_journey_duration_hours || 0.0} ч
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">От первого клика до оплаты</p>
          </CardContent>
        </Card>
      </div>

      {/* Full Funnel Dropoff Analytics */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Filter className="h-4 w-4 text-indigo-500" />
                Сквозная конверсионная воронка (Full-Funnel Dropoff)
              </CardTitle>
              <CardDescription className="text-xs">
                Конверсия каждого этапа: от AI-рекомендации в диалоге до целевой транзакции
              </CardDescription>
            </div>
            <Badge variant="outline" className="text-xs font-bold text-indigo-600 dark:text-indigo-400">
              Общая конверсия воронки: {funnelData?.overall_funnel_conversion_rate || 0}%
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {loadingFunnel || isFunnelStale ? (
            <div className="py-8 flex items-center justify-center text-xs text-muted-foreground">
              <RefreshCw className="h-4 w-4 animate-spin mr-2" /> Загрузка воронки ({mtaDays} дней)...
            </div>
          ) : !funnelData?.stages || !Array.isArray(funnelData.stages) || funnelData.stages.length === 0 ? (
            <div className="py-8 text-center text-xs text-muted-foreground">
              Недостаточно данных для построения воронки
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
              {(funnelData.stages || []).map((stage: FunnelStageItem, idx: number) => {
                const colors = [
                  'from-blue-500 to-blue-600',
                  'from-cyan-500 to-cyan-600',
                  'from-teal-500 to-teal-600',
                  'from-purple-500 to-purple-600',
                  'from-emerald-500 to-emerald-600',
                ];
                const grad = colors[idx % colors.length];
                return (
                  <div
                    key={stage.stage_id}
                    className="p-3.5 rounded-xl border bg-card/60 flex flex-col justify-between space-y-2 relative overflow-hidden"
                  >
                    <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${grad}`} />
                    <div>
                      <span className="text-[11px] font-semibold text-muted-foreground block line-clamp-1">
                        {stage.name}
                      </span>
                      <div className="text-xl font-black text-foreground mt-1">
                        {toLocaleSafe(stage.count)}
                      </div>
                    </div>

                    <div className="space-y-1 pt-2 border-t text-[11px]">
                      <div className="flex justify-between text-muted-foreground">
                        <span>Конверсия шага:</span>
                        <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                          {stage.conversion_from_prev}%
                        </span>
                      </div>
                      {idx > 0 && stage.dropoff_rate > 0 && (
                        <div className="flex justify-between text-muted-foreground">
                          <span>Отток (Dropoff):</span>
                          <span className="font-semibold text-rose-500">
                            -{stage.dropoff_rate}%
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Campaign Multi-Touch Attribution Breakdown Table */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Share2 className="h-4 w-4 text-emerald-500" />
                Вклад кампаний по модели: {displayModelForData.toUpperCase().replace('_', ' ')}
                {isMtaStale && (
                  <Badge variant="outline" className="text-[10px] ml-2 animate-pulse text-indigo-500 border-indigo-500/20">
                    Обновление...
                  </Badge>
                )}
              </CardTitle>
              <CardDescription className="text-xs">
                Дробное распределение конверсий, ROAS и эффективная цена привлечения (CPA)
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loadingMta || isMtaStale ? (
            <div className="py-8 flex items-center justify-center text-xs text-muted-foreground">
              <RefreshCw className="h-4 w-4 animate-spin mr-2" /> Расчет мультитач весов ({mtaModel.replace('_', ' ')})...
            </div>
          ) : !mtaSummary?.campaigns || !Array.isArray(mtaSummary.campaigns) || mtaSummary.campaigns.length === 0 ? (
            <div className="py-8 text-center text-xs text-muted-foreground">
              Кампании пока не зафиксировали конверсионных путей
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b text-muted-foreground text-left">
                    <th className="py-2.5 px-3">Кампания</th>
                    <th className="py-2.5 px-3">Расход ($)</th>
                    <th className="py-2.5 px-3 text-center">First Touch</th>
                    <th className="py-2.5 px-3 text-center">Assists (Помощь)</th>
                    <th className="py-2.5 px-3 text-center">Last Touch</th>
                    <th className="py-2.5 px-3 text-right font-bold text-indigo-600">Кредит Конверсий</th>
                    <th className="py-2.5 px-3 text-right font-bold text-emerald-600">Кредит Выручки</th>
                    <th className="py-2.5 px-3 text-right">Эфф. CPA ($)</th>
                    <th className="py-2.5 px-3 text-right">ROAS</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(mtaSummary.campaigns || []).map((c: CampaignAttributionCredit) => (
                    <tr key={c.campaign_id} className="hover:bg-muted/40 transition-colors">
                      <td className="py-2.5 px-3 font-semibold text-foreground">
                        <div>{c.campaign_name}</div>
                        {c.product_name && (
                          <div className="text-[10px] text-muted-foreground font-normal">{c.product_name}</div>
                        )}
                      </td>
                      <td className="py-2.5 px-3 font-mono">${toFixedSafe(c.total_spend, 2)}</td>
                      <td className="py-2.5 px-3 text-center">
                        <Badge variant="outline" className="text-[10px] bg-blue-500/10 text-blue-500 border-blue-500/20">
                          {c.first_touch_count}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <Badge variant="outline" className="text-[10px] bg-purple-500/10 text-purple-500 border-purple-500/20">
                          {c.assisted_count}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
                          {c.last_touch_count}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-indigo-600 dark:text-indigo-400 font-mono">
                        {c.credited_conversions}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                        ${toFixedSafe(c.credited_revenue, 2)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono">
                        ${toFixedSafe(c.effective_cpa, 2)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold font-mono">
                        <span className={c.roas >= 1.0 ? 'text-emerald-600' : 'text-muted-foreground'}>
                          {toFixedSafe(c.roas, 2)}x
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* User Conversion Journey Paths Stream */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-cyan-500" />
            Карта путей клиентов (Conversion Journey Paths)
          </CardTitle>
          <CardDescription className="text-xs">
            Последовательность точек касания пользователей перед совершением конверсии
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!Array.isArray(mtaPaths) || mtaPaths.length === 0 ? (
            <div className="py-8 text-center text-xs text-muted-foreground">
              Нет зафиксированных мультикасательных путей
            </div>
          ) : (
            <div className="space-y-3">
              {(mtaPaths || []).map((path: ConversionJourneyPath) => (
                <div
                  key={path.id}
                  className="p-3.5 rounded-xl border bg-muted/20 hover:bg-muted/40 transition-colors space-y-2 text-xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] text-muted-foreground">
                        Visitor: {path.visitor_id.substring(0, 16)}
                      </span>
                      <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-600 border-emerald-500/20 font-bold">
                        🏆 {path.conversion_type.toUpperCase()} (${toFixedSafe(path.conversion_value, 2)})
                      </Badge>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
                      <span>Длина пути: <strong>{path.total_touchpoints} касаний</strong></span>
                      <span>Время: <strong>{path.journey_duration_hours} ч</strong></span>
                      <span>{new Date(path.create_time).toLocaleDateString()}</span>
                    </div>
                  </div>

                  {/* Path step sequence */}
                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    {(path.path_steps || []).map((step, sIdx) => (
                      <div key={sIdx} className="flex items-center gap-1.5">
                        <div className="px-2.5 py-1 rounded-md bg-background border text-[11px] flex items-center gap-1.5 shadow-sm">
                          <span className="h-4 w-4 rounded-full bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-bold flex items-center justify-center text-[9px]">
                            {step.seq}
                          </span>
                          <span className="font-semibold text-foreground">{step.campaign_name}</span>
                          <span className="text-[10px] text-muted-foreground">({step.channel})</span>
                        </div>
                        {sIdx < ((path.path_steps && path.path_steps.length) || 0) - 1 && (
                          <ArrowRight className="h-3 w-3 text-muted-foreground" />
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
