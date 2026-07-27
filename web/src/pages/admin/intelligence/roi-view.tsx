import { useState, useEffect } from 'react';
import request from '@/utils/request';
import { Button } from '@/components/ui/button';
import {
  LucideCoins,
  LucideClock,
  LucideFrown,
  LucideAlertTriangle,
  LucideFilePlus,
  LucideSparkles,
  LucideRefreshCw,
} from 'lucide-react';
import message from '@/components/ui/message';

interface SentimentData {
  frustration_index: number;
  positive_percentage: number;
  neutral_percentage: number;
  frustrated_percentage: number;
  top_friction_points: { issue: string; count: number }[];
  feature_requests: { request: string; count: number }[];
}

interface RoiData {
  total_hours_saved: number;
  estimated_cost_saved_usd: number;
  questions_resolved_automatically: number;
  knowledge_reuse_rate: string;
  spof_risks: { domain: string; expert_name: string; risk_level: string; recommendation: string }[];
}

export function IntelligenceRoiView() {
  const [loading, setLoading] = useState(false);
  const [sentiment, setSentiment] = useState<SentimentData | null>(null);
  const [roi, setRoi] = useState<RoiData | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [resSent, resRoi] = await Promise.all([
        request.get('/api/v1/intelligence/analytics/sentiment?global=true'),
        request.get('/api/v1/intelligence/analytics/roi?global=true'),
      ]);
      if (resSent?.data?.code === 0) setSentiment(resSent.data.data);
      if (resRoi?.data?.code === 0) setRoi(resRoi.data.data);
    } catch {
      setSentiment(null);
      setRoi(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleGenerateFaq = async (topic: string) => {
    try {
      const res = await request.post('/api/v1/intelligence/faq/generate?global=true', {
        topic,
      });
      if (res?.data?.code === 0) {
        message.success(`Статья FAQ "${res.data.data.title}" успешно сгенерирована!`);
      }
    } catch {
      message.error('Не удалось сгенерировать FAQ.');
    }
  };

  return (
    <div className="flex flex-col gap-6 w-full max-w-6xl mx-auto space-y-2">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="font-bold text-2xl">Аналитика ROI, Экономии Времени и Настроений</h3>
          <p className="text-xs text-muted-foreground mt-1">
            Оценка финансовой эффективности ИИ, уровня фрустрации пользователей и рисков утечки знаний
          </p>
        </div>
        <Button variant="outline" onClick={fetchData} disabled={loading} className="gap-2">
          <LucideRefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Обновить
        </Button>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-5">
        <div className="bg-background rounded-2xl p-5 border border-emerald-500/30 bg-emerald-500/5 space-y-1">
          <div className="flex items-center justify-between text-emerald-400 font-bold text-xs uppercase">
            <span>Сэкономлено Времени</span>
            <LucideClock className="w-5 h-5" />
          </div>
          <div className="text-3xl font-extrabold">{roi?.total_hours_saved || 0} ч</div>
          <div className="text-xs text-muted-foreground">Рабочих часов инженеров</div>
        </div>

        <div className="bg-background rounded-2xl p-5 border border-blue-500/30 bg-blue-500/5 space-y-1">
          <div className="flex items-center justify-between text-blue-400 font-bold text-xs uppercase">
            <span>Финансовый ROI</span>
            <LucideCoins className="w-5 h-5" />
          </div>
          <div className="text-3xl font-extrabold">${roi?.estimated_cost_saved_usd || 0}</div>
          <div className="text-xs text-muted-foreground">Прямой экономии бюджета</div>
        </div>

        <div className="bg-background rounded-2xl p-5 border border-purple-500/30 bg-purple-500/5 space-y-1">
          <div className="flex items-center justify-between text-purple-400 font-bold text-xs uppercase">
            <span>Повторное использование</span>
            <LucideSparkles className="w-5 h-5" />
          </div>
          <div className="text-3xl font-extrabold">{roi?.knowledge_reuse_rate || '0%'}</div>
          <div className="text-xs text-muted-foreground">База знаний RAGFlow</div>
        </div>

        <div className="bg-background rounded-2xl p-5 border border-amber-500/30 bg-amber-500/5 space-y-1">
          <div className="flex items-center justify-between text-amber-400 font-bold text-xs uppercase">
            <span>Индекс Фрустрации</span>
            <LucideFrown className="w-5 h-5" />
          </div>
          <div className="text-3xl font-extrabold">{sentiment ? `${Math.round((sentiment.frustration_index || 0) * 100)}%` : '0%'}</div>
          <div className="text-xs text-muted-foreground">Уровень затруднений пользования</div>
        </div>
      </div>

      {/* Main Grid Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SPOF Knowledge Bottleneck Risks */}
        <div className="bg-background rounded-2xl p-5 border border-border space-y-4">
          <h4 className="font-bold text-base flex items-center gap-2 text-amber-400">
            <LucideAlertTriangle className="w-5 h-5" />
            ⚠️ Детектор Утечки Знаний (Single Point of Failure Risks)
          </h4>
          <div className="space-y-3">
            {roi?.spof_risks && roi.spof_risks.length > 0 ? (
              roi.spof_risks.map((spof, i) => (
                <div key={i} className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/5 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm">{spof.domain}</span>
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 font-bold">
                      Риск: {spof.risk_level}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Ключевой эксперт: <strong className="text-foreground">{spof.expert_name}</strong>
                  </div>
                  <p className="text-xs text-amber-300 font-medium">💡 {spof.recommendation}</p>
                </div>
              ))
            ) : (
              <p className="text-xs text-muted-foreground">Узкие места в распределении знаний не выявлены.</p>
            )}
          </div>
        </div>

        {/* Feature Requests & Auto-FAQ */}
        <div className="bg-background rounded-2xl p-5 border border-border space-y-4">
          <h4 className="font-bold text-base flex items-center gap-2 text-primary">
            <LucideFilePlus className="w-5 h-5" />
            🚀 Запросы На Фичи и Авто-Генерация FAQ
          </h4>
          <div className="space-y-3">
            {sentiment?.feature_requests && sentiment.feature_requests.length > 0 ? (
              sentiment.feature_requests.map((fr, i) => (
                <div key={i} className="p-3.5 rounded-xl border border-border bg-background/50 flex items-center justify-between gap-3 text-xs">
                  <div>
                    <div className="font-bold text-sm text-foreground">{fr.request}</div>
                    <div className="text-muted-foreground mt-0.5">Запрошено {fr.count} пользователями</div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleGenerateFaq(fr.request)}
                    className="h-8 text-xs gap-1"
                  >
                    <LucideSparkles className="w-3.5 h-3.5 text-primary" />
                    Создать FAQ
                  </Button>
                </div>
              ))
            ) : (
              <p className="text-xs text-muted-foreground">Запросы анализируются из сообщений пользователей.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
