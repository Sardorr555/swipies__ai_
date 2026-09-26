import React from 'react';
import { Sparkles, RefreshCw, CheckCircle2, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { AdvertiserInsightsData, CampaignInsightItem } from '@/services/ad-service';

export interface InsightsTabProps {
  insightsData?: AdvertiserInsightsData | null;
  loadingInsights: boolean;
  applyingInsightId?: string | null;
  onRefresh: () => void;
  onApplyInsight: (insight: CampaignInsightItem) => void;
}

export const InsightsTab: React.FC<InsightsTabProps> = ({
  insightsData,
  loadingInsights,
  applyingInsightId,
  onRefresh,
  onApplyInsight,
}) => {
  return (
    <div className="space-y-6">
      {/* Optimization Header / Score Card */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-6 rounded-xl border bg-gradient-to-r from-amber-500/10 via-purple-500/10 to-blue-500/10 dark:from-amber-950/30 dark:via-purple-950/30 dark:to-blue-950/30">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-amber-500/20 text-amber-600 dark:text-amber-400 font-extrabold text-2xl border border-amber-500/30">
            {insightsData?.score ?? 100}%
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xl font-bold">AI Рекламный Аудит & Оптимизатор</h3>
              <Badge variant="outline" className="border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400">
                <Sparkles className="mr-1 h-3 w-3" /> Smart Copilot
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-1 max-w-xl">
              AI в реальном времени анализирует воронку конверсий, качество ключевых слов, CTR офферов и защищает бюджет от нецелевых кликов.
            </p>
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          disabled={loadingInsights}
          aria-label="Пересканировать кампании"
          className="bg-background hover:bg-muted text-xs flex items-center gap-1.5 shrink-0"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loadingInsights ? 'animate-spin' : ''}`} />
          Пересканировать кампании
        </Button>
      </div>

      {/* Recommendations List */}
      {loadingInsights ? (
        <div className="flex flex-col items-center justify-center py-16">
          <RefreshCw className="h-8 w-8 animate-spin text-amber-500 mb-2" />
          <p className="text-sm text-muted-foreground">Идет аудит рекламных кампаний...</p>
        </div>
      ) : !insightsData || !Array.isArray(insightsData.insights) || insightsData.insights.length === 0 ? (
        <Card className="p-8 text-center border-dashed">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500 mx-auto mb-3">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <h4 className="text-base font-bold text-foreground">Кампании максимально оптимизированы!</h4>
          <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
            Все ваши кампании имеют отличные показатели релевантности, настроенные минус-слова, A/B варианты и корректные ставки.
          </p>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {(insightsData.insights || []).map((insight: CampaignInsightItem) => (
            <Card key={insight.id} className="relative flex flex-col justify-between border shadow-sm hover:border-amber-500/40 transition-colors">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <Badge
                    variant="outline"
                    className={
                      insight.category === 'cost'
                        ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[10px]'
                        : insight.category === 'quality'
                        ? 'border-rose-500/30 bg-rose-500/10 text-rose-600 dark:text-rose-400 text-[10px]'
                        : insight.category === 'reach'
                        ? 'border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400 text-[10px]'
                        : 'border-purple-500/30 bg-purple-500/10 text-purple-600 dark:text-purple-400 text-[10px]'
                    }
                  >
                    {insight.category === 'cost' && '🛡️ Защита бюджета'}
                    {insight.category === 'quality' && '🎨 Оффер & CTR'}
                    {insight.category === 'reach' && '🔍 Охват запросов'}
                    {insight.category === 'growth' && '🧪 A/B Эксперимент'}
                    {insight.category === 'bidding' && '⚡ Smart CPA'}
                  </Badge>

                  <div className="flex items-center gap-1">
                    <span className="text-[11px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/20">
                      {insight.estimated_impact}
                    </span>
                  </div>
                </div>

                <CardTitle className="text-base font-semibold leading-snug">{insight.title}</CardTitle>
                <div className="text-xs text-muted-foreground font-medium flex items-center gap-1 mt-0.5">
                  <span className="text-blue-500 font-semibold">{insight.campaign_name}</span>
                </div>
              </CardHeader>

              <CardContent className="space-y-3 pb-4 text-xs">
                <p className="text-muted-foreground leading-relaxed">{insight.description}</p>

                <div className="p-2.5 rounded-lg bg-muted/40 border text-[11px] font-medium text-foreground">
                  <span className="text-muted-foreground block text-[10px] uppercase font-semibold">Действие:</span>
                  {insight.suggested_action}
                </div>

                <Button
                  size="sm"
                  className="w-full bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold flex items-center justify-center gap-1.5"
                  onClick={() => onApplyInsight(insight)}
                  disabled={applyingInsightId === insight.id}
                  aria-label={`Применить рекомендацию: ${insight.title}`}
                >
                  {applyingInsightId === insight.id ? (
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Zap className="h-3.5 w-3.5" />
                  )}
                  {applyingInsightId === insight.id ? 'Применение...' : 'Применить рекомендацию в 1 клик'}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default InsightsTab;
