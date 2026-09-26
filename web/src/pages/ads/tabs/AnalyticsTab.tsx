import React from 'react';
import {
  BarChart3,
  RefreshCw,
  Download,
  Printer,
  Globe,
  Cpu,
  Laptop,
  MapPin,
} from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { TimelineAnalyticsData } from '@/services/ad-service';
import { toFixedSafe, toLocaleSafe } from '../format-utils';

export interface AnalyticsTabProps {
  timelineData: TimelineAnalyticsData | null;
  timelineDays: number;
  loadingTimeline: boolean;
  onTimelineDaysChange: (days: number) => void;
  onRefresh: () => void;
  onExportCsv: (days: number) => void;
  onExportReport: (days: number) => void;
}

export const AnalyticsTab: React.FC<AnalyticsTabProps> = ({
  timelineData,
  timelineDays,
  loadingTimeline,
  onTimelineDaysChange,
  onRefresh,
  onExportCsv,
  onExportReport,
}) => {
  // Stale detection: parent index.tsx fetch functions currently lack AbortController/request-id sequencing (known limitation: ARCH-Race-Conditions)
  const isTimelineStale = Boolean(
    loadingTimeline || (timelineData?.days && timelineData.days !== timelineDays)
  );

  return (
    <div className="space-y-6">
      {/* Header with Date Range filter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-muted/30 p-4 rounded-xl border">
        <div>
          <h3 className="text-base font-bold flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-blue-500" />
            Интерактивная статистика эффективности
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Динамика показов, переходов, расходов и сегментация аудитории в реальном времени
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
          <div
            className="flex items-center gap-1.5 bg-background p-1 rounded-lg border"
            role="toolbar"
            aria-label="Период аналитики"
          >
            {[7, 14, 30].map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => onTimelineDaysChange(d)}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                  timelineDays === d
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
                aria-pressed={timelineDays === d}
              >
                {d === 7 ? '7 дней' : d === 14 ? '14 дней' : '30 дней'}
              </button>
            ))}
            <Button
              size="sm"
              variant="ghost"
              className="h-7 px-2 text-xs"
              onClick={onRefresh}
              title="Обновить данные"
              aria-label="Обновить данные"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loadingTimeline ? 'animate-spin' : ''}`} />
            </Button>
          </div>

          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs flex items-center gap-1.5"
            onClick={() => onExportCsv(timelineDays)}
            title="Экспорт динамики в CSV"
            aria-label="Экспорт динамики в CSV"
          >
            <Download className="h-3.5 w-3.5" /> CSV
          </Button>

          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs flex items-center gap-1.5 border-blue-500/30 text-blue-600 dark:text-blue-400 hover:bg-blue-500/10"
            onClick={() => onExportReport(timelineDays)}
            title="Открыть PDF / Печатную версию отчета"
            aria-label="Открыть PDF / Печатную версию отчета"
          >
            <Printer className="h-3.5 w-3.5" /> PDF Отчет
          </Button>
        </div>
      </div>

      {/* Quick Metrics in Analytics Tab */}
      <div
        className={`grid gap-4 md:grid-cols-4 transition-opacity duration-200 ${
          isTimelineStale ? 'opacity-70' : 'opacity-100'
        }`}
      >
        <Card className="bg-gradient-to-br from-blue-50/50 to-transparent dark:from-blue-950/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Показы за период</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-blue-600 dark:text-blue-400">
              {toLocaleSafe(timelineData?.total_impressions)}
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">Охват рекомендаций в чате</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-emerald-50/50 to-transparent dark:from-emerald-950/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Клики за период</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
              {toLocaleSafe(timelineData?.total_clicks)}
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">Переходы на ваш сайт</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-purple-50/50 to-transparent dark:from-purple-950/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Средний CTR</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-purple-600 dark:text-purple-400">
              {timelineData?.ctr ?? 0}%
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">Конверсия показов в клики</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-amber-50/50 to-transparent dark:from-amber-950/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Расходы за период</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black text-amber-600 dark:text-amber-400">
              ${toFixedSafe(timelineData?.total_spend, 2)}
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">CPC / CPM инвестиции</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Chart Area */}
      <Card
        className={`transition-opacity duration-200 ${
          isTimelineStale ? 'opacity-70' : 'opacity-100'
        }`}
      >
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <div>
            <CardTitle className="text-sm font-semibold">График показов и переходов по дням</CardTitle>
            <CardDescription className="text-xs">
              Динамика вовлеченности аудитории за последние {timelineDays} дней
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-[280px] w-full">
            {timelineData?.timeline &&
            Array.isArray(timelineData.timeline) &&
            timelineData.timeline.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={Array.isArray(timelineData.timeline) ? timelineData.timeline : []}
                  margin={{ top: 10, right: 20, left: -10, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="impGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="clkGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(val) => {
                      if (!val || typeof val !== 'string') return '';
                      const parts = val.split('-');
                      return parts.length === 3 ? `${parts[1]}.${parts[2]}` : val;
                    }}
                  />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(17, 24, 39, 0.95)',
                      borderRadius: '8px',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#fff',
                      fontSize: '12px',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                  <Area
                    type="monotone"
                    dataKey="impressions"
                    name="Показы (Impressions)"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#impGradient)"
                  />
                  <Area
                    type="monotone"
                    dataKey="clicks"
                    name="Клики (Clicks)"
                    stroke="#10b981"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#clkGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-muted-foreground">
                За выбранный период данных нет
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Breakdown Cards: Languages, Models, Devices, Regions */}
      <div
        className={`grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4 transition-opacity duration-200 ${
          isTimelineStale ? 'opacity-70' : 'opacity-100'
        }`}
      >
        {/* Language Breakdown */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-xs font-semibold flex items-center gap-2">
              <Globe className="h-4 w-4 text-blue-500" />
              Языки запросов пользователей
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {(() => {
              const langs =
                timelineData && typeof timelineData.languages === 'object' && timelineData.languages
                  ? timelineData.languages
                  : {};
              const total =
                Object.values(langs).reduce((a, b) => a + (Number(b) || 0), 0) || 1;
              const items = [
                { code: 'ru', label: '🇷🇺 Русский', count: langs['ru'] || 0, color: 'bg-blue-500' },
                { code: 'uz', label: '🇺🇿 Oʻzbekcha', count: langs['uz'] || 0, color: 'bg-emerald-500' },
                { code: 'en', label: '🇬🇧 English', count: langs['en'] || 0, color: 'bg-purple-500' },
                { code: 'other', label: '🌐 Другие', count: langs['other'] || 0, color: 'bg-zinc-400' },
              ];
              return items.map((item) => {
                const pct = Math.round(((item.count || 0) / total) * 100);
                return (
                  <div key={item.code} className="space-y-1">
                    <div className="flex justify-between text-xs font-medium">
                      <span>{item.label}</span>
                      <span className="text-muted-foreground">
                        {item.count} ({pct}%)
                      </span>
                    </div>
                    <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full ${item.color} rounded-full transition-all`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              });
            })()}
          </CardContent>
        </Card>

        {/* AI Models Breakdown */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-xs font-semibold flex items-center gap-2">
              <Cpu className="h-4 w-4 text-purple-500" />
              Используемые модели LLM
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {(() => {
              const models =
                timelineData && typeof timelineData.models === 'object' && timelineData.models
                  ? timelineData.models
                  : {};
              const total =
                Object.values(models).reduce((a, b) => a + (Number(b) || 0), 0) || 1;
              const items = [
                { code: 'gpt-4o', label: '🤖 GPT-4o / Mini', count: models['gpt-4o'] || 0, color: 'bg-emerald-500' },
                { code: 'deepseek', label: '⚡ DeepSeek R1 / V3', count: models['deepseek'] || 0, color: 'bg-blue-500' },
                { code: 'claude', label: '🧠 Claude 3.5 Sonnet', count: models['claude'] || 0, color: 'bg-purple-500' },
                { code: 'other', label: '🌐 Другие модели', count: models['other'] || 0, color: 'bg-zinc-400' },
              ];
              return items.map((item) => {
                const pct = Math.round(((item.count || 0) / total) * 100);
                return (
                  <div key={item.code} className="space-y-1">
                    <div className="flex justify-between text-xs font-medium">
                      <span>{item.label}</span>
                      <span className="text-muted-foreground">
                        {item.count} ({pct}%)
                      </span>
                    </div>
                    <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full ${item.color} rounded-full transition-all`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              });
            })()}
          </CardContent>
        </Card>

        {/* Devices Breakdown */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-xs font-semibold flex items-center gap-2">
              <Laptop className="h-4 w-4 text-emerald-500" />
              Устройства и платформы
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {(() => {
              const devs =
                timelineData && typeof timelineData.devices === 'object' && timelineData.devices
                  ? timelineData.devices
                  : {};
              const total =
                Object.values(devs).reduce((a, b) => a + (Number(b) || 0), 0) || 1;
              const items = [
                { code: 'desktop', label: '🖥️ Desktop (ПК)', count: devs['desktop'] || 0, color: 'bg-blue-500' },
                { code: 'mobile', label: '📱 Mobile (Смартфоны)', count: devs['mobile'] || 0, color: 'bg-emerald-500' },
                { code: 'tablet', label: '📟 Планшеты', count: devs['tablet'] || 0, color: 'bg-amber-500' },
              ];
              return items.map((item) => {
                const pct = Math.round(((item.count || 0) / total) * 100);
                return (
                  <div key={item.code} className="space-y-1">
                    <div className="flex justify-between text-xs font-medium">
                      <span>{item.label}</span>
                      <span className="text-muted-foreground">
                        {item.count} ({pct}%)
                      </span>
                    </div>
                    <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full ${item.color} rounded-full transition-all`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              });
            })()}
          </CardContent>
        </Card>

        {/* Regional Breakdown */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-xs font-semibold flex items-center gap-2">
              <MapPin className="h-4 w-4 text-rose-500" />
              Регионы Узбекистана
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {(() => {
              const regions =
                timelineData && typeof timelineData.regions === 'object' && timelineData.regions
                  ? timelineData.regions
                  : {};
              const total =
                Object.values(regions).reduce((a, b) => a + (Number(b) || 0), 0) || 1;
              const items = [
                { code: 'tashkent', label: '📍 Ташкент', count: regions['tashkent'] || 0, color: 'bg-rose-500' },
                { code: 'samarkand', label: '📍 Самарканд', count: regions['samarkand'] || 0, color: 'bg-blue-500' },
                { code: 'fergana', label: '📍 Фергана', count: regions['fergana'] || 0, color: 'bg-emerald-500' },
                { code: 'bukhara', label: '📍 Бухара', count: regions['bukhara'] || 0, color: 'bg-amber-500' },
                { code: 'andijan', label: '📍 Андижан', count: regions['andijan'] || 0, color: 'bg-indigo-500' },
                {
                  code: 'other',
                  label: '🌐 Другие регионы',
                  count: (regions['namangan'] || 0) + (regions['other'] || 0),
                  color: 'bg-zinc-400',
                },
              ];
              return items.map((item) => {
                const pct = Math.round(((item.count || 0) / total) * 100);
                return (
                  <div key={item.code} className="space-y-1">
                    <div className="flex justify-between text-xs font-medium">
                      <span>{item.label}</span>
                      <span className="text-muted-foreground">
                        {item.count} ({pct}%)
                      </span>
                    </div>
                    <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full ${item.color} rounded-full transition-all`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              });
            })()}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
