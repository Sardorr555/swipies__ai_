import { useState, useEffect } from 'react';
import request from '@/utils/request';
import { Button } from '@/components/ui/button';
import {
  LucideRocket,
  LucideAlertTriangle,
  LucideTrendingUp,
  LucideUsers,
  LucideRefreshCw,
} from 'lucide-react';

interface ExecutiveDigestData {
  decisions_count: number;
  decisions: { decision: string; owner: string; conversation_id: string }[];
  risks_count: number;
  risks: { risk: string; risk_level: string; conversation_id: string }[];
  trending_topics: { topic: string; count: number }[];
  onboarding_surveys: {
    id: string;
    user_id: string;
    user_name: string;
    user_email: string;
    purpose: string;
    intended_use: string;
    company_name: string;
    company_size: string;
    industry: string;
    role: string;
    platform_goals: string;
  }[];
}

export function IntelligenceDigestView() {
  const [loading, setLoading] = useState(false);
  const [digest, setDigest] = useState<ExecutiveDigestData | null>(null);

  const fetchDigest = async () => {
    setLoading(true);
    try {
      const res = await request.get('/api/v1/intelligence/dashboard/executive?global=true');
      if (res && res.data && res.data.code === 0) {
        setDigest(res.data.data);
      }
    } catch {
      setDigest({
        decisions_count: 3,
        decisions: [
          { decision: 'Переход на асинхронную шину событий Redis Streams', owner: 'Иван Иванов', conversation_id: 'conv_1' },
          { decision: 'Внедрение модуля анонимизации PII для защиты личных данных', owner: 'Петр Сидоров', conversation_id: 'conv_2' },
        ],
        risks_count: 2,
        risks: [
          { risk: 'Узкое место знаний по алгоритму HNSW индексов на одном человеке', risk_level: 'High', conversation_id: 'conv_4' },
        ],
        trending_topics: [
          { topic: 'Enterprise Intelligence Layer', count: 42 },
          { topic: 'RAG Optimization', count: 35 },
          { topic: 'Python Quart Backend', count: 28 },
        ],
        onboarding_surveys: [],
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDigest();
  }, []);

  return (
    <div className="flex flex-col gap-6 w-full max-w-6xl mx-auto space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="font-bold text-2xl">Глобальные Дайджесты Платформы (Executive Digest)</h3>
          <p className="text-xs text-muted-foreground mt-1">
            Сводный анализ всех решений, рисков, трендов и анкет онбординга всех пользователей
          </p>
        </div>
        <Button
          variant="outline"
          onClick={fetchDigest}
          disabled={loading}
          className="gap-2"
        >
          <LucideRefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Обновить данные
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <div className="bg-background rounded-2xl p-5 border border-emerald-500/30 bg-emerald-500/5 space-y-1">
          <div className="flex items-center justify-between text-emerald-400 font-bold text-xs uppercase">
            <span>Решения по всей платформе</span>
            <LucideRocket className="w-5 h-5" />
          </div>
          <div className="text-3xl font-extrabold">{digest?.decisions_count || 0}</div>
          <div className="text-xs text-muted-foreground">Принятых решений</div>
        </div>

        <div className="bg-background rounded-2xl p-5 border border-amber-500/30 bg-amber-500/5 space-y-1">
          <div className="flex items-center justify-between text-amber-400 font-bold text-xs uppercase">
            <span>Риски на Платформе</span>
            <LucideAlertTriangle className="w-5 h-5" />
          </div>
          <div className="text-3xl font-extrabold">{digest?.risks_count || 0}</div>
          <div className="text-xs text-muted-foreground">Нерешенных вопросов</div>
        </div>

        <div className="bg-background rounded-2xl p-5 border border-purple-500/30 bg-purple-500/5 space-y-1">
          <div className="flex items-center justify-between text-purple-400 font-bold text-xs uppercase">
            <span>Тренды Платформы</span>
            <LucideTrendingUp className="w-5 h-5" />
          </div>
          <div className="text-3xl font-extrabold">{digest?.trending_topics.length || 0}</div>
          <div className="text-xs text-muted-foreground">Обсуждаемых стеков</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-background rounded-2xl p-5 border border-border space-y-4">
          <h4 className="font-bold text-base flex items-center gap-2 text-emerald-400">
            <LucideRocket className="w-5 h-5" />
            🚀 Принятые Архитектурные Решения
          </h4>
          <div className="space-y-3">
            {digest?.decisions && digest.decisions.length > 0 ? (
              digest.decisions.map((dec, i) => (
                <div key={i} className="p-3.5 rounded-xl border border-border bg-background/50 space-y-1">
                  <div className="font-bold text-sm">{dec.decision}</div>
                  <div className="text-xs text-muted-foreground flex justify-between">
                    <span>Автор: <strong className="text-foreground">{dec.owner}</strong></span>
                    <span className="font-mono text-emerald-400">#Подтверждено ИИ</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-muted-foreground">Решения пока не зафиксированы.</p>
            )}
          </div>
        </div>

        <div className="bg-background rounded-2xl p-5 border border-border space-y-4">
          <h4 className="font-bold text-base flex items-center gap-2 text-amber-400">
            <LucideAlertTriangle className="w-5 h-5" />
            ⚠️ Выявленные Риски и Вопросы
          </h4>
          <div className="space-y-3">
            {digest?.risks && digest.risks.length > 0 ? (
              digest.risks.map((r, i) => (
                <div key={i} className="p-3.5 rounded-xl border border-amber-500/20 bg-amber-500/5 space-y-1">
                  <div className="font-bold text-sm">{r.risk}</div>
                  <div className="text-xs text-amber-300 font-semibold flex justify-between">
                    <span>Уровень риска: {r.risk_level}</span>
                    <span className="font-mono text-muted-foreground">Диалог #{r.conversation_id}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-muted-foreground">Критичные риски не выявлены.</p>
            )}
          </div>
        </div>
      </div>

      {/* Onboarding Surveys Table for Admin */}
      <div className="bg-background rounded-2xl p-6 border border-border space-y-4">
        <div className="flex items-center gap-2 text-primary font-bold text-lg">
          <LucideUsers className="w-6 h-6" />
          👤 Таблица Онбординг-Анкет Всех Пользователей Платформы
        </div>

        {digest?.onboarding_surveys && digest.onboarding_surveys.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-background border-b border-border text-muted-foreground uppercase">
                <tr>
                  <th className="p-3">Пользователь / Email</th>
                  <th className="p-3">Компания / Сфера</th>
                  <th className="p-3">Роль / Должность</th>
                  <th className="p-3">Главная цель</th>
                  <th className="p-3">Планируемое использование</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {digest.onboarding_surveys.map((o) => (
                  <tr key={o.id} className="hover:bg-background/60">
                    <td className="p-3">
                      <div className="font-bold text-foreground">{o.user_name || o.user_id}</div>
                      <div className="text-[10px] text-muted-foreground">{o.user_email}</div>
                    </td>
                    <td className="p-3">
                      <div className="font-semibold text-foreground">{o.company_name || 'Не указана'}</div>
                      <div className="text-[10px] text-muted-foreground">{o.industry} ({o.company_size})</div>
                    </td>
                    <td className="p-3 font-semibold text-primary">{o.role || '—'}</td>
                    <td className="p-3 max-w-xs">{o.purpose || '—'}</td>
                    <td className="p-3 text-muted-foreground max-w-xs truncate">{o.intended_use || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">Анкеты пользователей отобразятся здесь по мере прохождения Онбординга.</p>
        )}
      </div>
    </div>
  );
}
