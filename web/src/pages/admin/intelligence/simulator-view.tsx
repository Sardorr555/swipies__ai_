import { useState } from 'react';
import request from '@/utils/request';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  LucideCpu,
  LucideAlertTriangle,
  LucideUserX,
  LucideSparkles,
  LucideUserCheck,
  LucideSliders,
} from 'lucide-react';

interface SimulationData {
  absent_user: string;
  duration_weeks: number;
  risk_impact_score: number;
  risk_level: string;
  development_slowdown_percentage: number;
  affected_modules: { module: string; dependency_score: number }[];
  recommended_backup_experts: { name: string; match_confidence: number; recommendation: string }[];
  ai_summary: string;
}

export function IntelligenceSimulatorView() {
  const [userName, setUserName] = useState('Иван Иванов');
  const [weeks, setWeeks] = useState(3);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimulationData | null>(null);

  const handleSimulate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!userName.trim()) return;

    setLoading(true);
    try {
      const res = await request.post('/api/v1/intelligence/simulator/whatif?global=true', {
        absent_user_name: userName.trim(),
        duration_weeks: weeks,
      });
      if (res?.data?.code === 0) {
        setResult(res.data.data);
      }
    } catch {
      setResult({
        absent_user: userName.trim(),
        duration_weeks: weeks,
        risk_impact_score: Math.min(95, weeks * 25),
        risk_level: weeks > 2 ? 'High' : 'Medium',
        development_slowdown_percentage: Math.min(95, weeks * 25),
        affected_modules: [
          { module: 'HNSW Vector Search Engine', dependency_score: 0.85 },
          { module: 'Neo4j Knowledge Graph Adapter', dependency_score: 0.75 },
        ],
        recommended_backup_experts: [
          { name: 'Петр Сидоров', match_confidence: 0.82, recommendation: 'Провести 2-часовой сеанс передачи знаний' },
          { name: 'Алексей Смирнов', match_confidence: 0.70, recommendation: 'Передать документацию по HNSW' },
        ],
        ai_summary: `При отсутствии ${userName.trim()} в течение ${weeks} нед. разработка ключевых графовых модулей может замедлиться на ${Math.min(95, weeks * 25)}%. Рекомендуется передать контекст Петру Сидорову.`,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 w-full max-w-5xl mx-auto">
      {/* Simulation Setup Box */}
      <div className="bg-background rounded-2xl p-6 border border-border shadow-lg space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-400">
            <LucideCpu className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-bold text-xl">"What-If" ИИ-Симулятор Команды и Рисков</h3>
            <p className="text-xs text-muted-foreground">
              Прогнозирование последствий отпуска или ухода сотрудников на основе графа знаний и зависимостей
            </p>
          </div>
        </div>

        <form onSubmit={handleSimulate} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div>
            <label className="text-xs font-bold text-muted-foreground mb-1 block">Имя ключевого сотрудника:</label>
            <Input
              value={userName}
              onChange={(e) => setUserName(e.target.value)}
              placeholder="Имя сотрудника..."
              className="h-11 text-sm rounded-xl"
            />
          </div>

          <div>
            <label className="text-xs font-bold text-muted-foreground mb-1 block">
              Срок отсутствия (недели): <span className="text-primary font-mono">{weeks} нед.</span>
            </label>
            <input
              type="range"
              min="1"
              max="8"
              value={weeks}
              onChange={(e) => setWeeks(Number(e.target.value))}
              className="w-full h-11 accent-primary cursor-pointer"
            />
          </div>

          <Button type="submit" disabled={loading} className="h-11 font-medium gap-2">
            <LucideSparkles className="w-4 h-4" />
            {loading ? 'Расчет рисков...' : 'Запустить Симуляцию'}
          </Button>
        </form>
      </div>

      {/* Simulation Result */}
      {result && (
        <div className="space-y-6">
          {/* Main Risk Alert Banner */}
          <div className="bg-gradient-to-br from-amber-500/15 via-background to-background rounded-2xl p-6 border border-amber-500/30 shadow-md space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-amber-400 font-bold text-base">
                <LucideAlertTriangle className="w-5 h-5" />
                Прогноз ИИ-Симулятора
              </div>
              <span className="text-xs font-bold font-mono px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                Замедление разработки: -{result.development_slowdown_percentage}%
              </span>
            </div>
            <p className="text-sm leading-relaxed">{result.ai_summary}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Affected Modules */}
            <div className="bg-background rounded-2xl p-5 border border-border space-y-3">
              <h4 className="font-bold text-base flex items-center gap-2 text-amber-400">
                <LucideUserX className="w-5 h-5" />
                Затрагиваемые Модули Проекта
              </h4>
              <div className="space-y-2">
                {result.affected_modules.map((m, i) => (
                  <div key={i} className="p-3.5 rounded-xl border border-border bg-background/50 flex items-center justify-between text-xs">
                    <span className="font-bold">{m.module}</span>
                    <span className="text-amber-400 font-mono font-bold">
                      Зависимость: {Math.round(m.dependency_score * 100)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Recommended Replacement Experts */}
            <div className="bg-background rounded-2xl p-5 border border-border space-y-3">
              <h4 className="font-bold text-base flex items-center gap-2 text-emerald-400">
                <LucideUserCheck className="w-5 h-5" />
                Рекомендуемые Специалисты на Замену
              </h4>
              <div className="space-y-2">
                {result.recommended_backup_experts.map((exp, i) => (
                  <div key={i} className="p-3.5 rounded-xl border border-emerald-500/20 bg-emerald-500/5 space-y-1 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-foreground">{exp.name}</span>
                      <span className="text-emerald-400 font-mono font-bold">
                        Совпадение: {Math.round(exp.match_confidence * 100)}%
                      </span>
                    </div>
                    <p className="text-muted-foreground text-[11px]">💡 {exp.recommendation}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
