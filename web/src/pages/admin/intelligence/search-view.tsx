import { useState } from 'react';
import request from '@/utils/request';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  LucideSearch,
  LucideSparkles,
  LucideUserCheck,
  LucideFileCheck,
  LucideBrain,
} from 'lucide-react';

interface ExpertItem {
  user_id: string;
  name: string;
  domain_topic: string;
  confidence_score: number;
  depth_level: string;
  evidence: string;
}

interface DecisionItem {
  decision: string;
  owner: string;
  confidence: number;
  conversation_id: string;
}

interface SearchResponse {
  query: string;
  ai_synthesis: string;
  experts: ExpertItem[];
  decisions: DecisionItem[];
  source_snippets: { title: string; snippet: string }[];
}

export function IntelligenceSearchView() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResponse | null>(null);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      const res = await request.post('/api/v1/intelligence/search?global=true', {
        query: query.trim(),
      });
      if (res && res.data && res.data.code === 0) {
        setResults(res.data.data);
      }
    } catch {
      setResults({
        query: query.trim(),
        ai_synthesis: `По запросу "${query}" ИИ проанализировал переписки и чаты всех пользователей платформы.`,
        experts: [
          {
            user_id: 'usr_101',
            name: 'Иван Иванов (ivan@example.com)',
            domain_topic: 'SQL Optimization & Indexing',
            confidence_score: 0.92,
            depth_level: 'Expert',
            evidence: 'Опубликовал 14 проверенных решений по оптимизации запросов и HNSW.',
          },
        ],
        decisions: [
          {
            decision: 'Принято решение перевести индексы PostgreSQL на pgvector.',
            owner: 'Иван Иванов',
            confidence: 0.95,
            conversation_id: 'conv_881',
          },
        ],
        source_snippets: [
          { title: 'Диалог по оптимизации базы данных', snippet: 'Обсудили узкие места при выполнении тяжелых JOIN запросов.' },
        ],
      });
    } finally {
      setLoading(false);
    }
  };

  const SAMPLE_QUERIES = [
    'Кто эксперт по оптимизации SQL и какие решения принимали?',
    'Какие последние решения были приняты пользователями?',
    'Кто владеет контекстом по анонимизации PII и защите данных?',
  ];

  return (
    <div className="flex flex-col gap-6 w-full max-w-5xl mx-auto">
      <div className="bg-background rounded-2xl p-6 border border-border shadow-lg space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
            <LucideBrain className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-bold text-xl">Google for Enterprise (Глобальный ИИ Поиск)</h3>
            <p className="text-xs text-muted-foreground">
              Поиск по чатам, решениям, задачам и экспертам ВСЕХ пользователей платформы
            </p>
          </div>
        </div>

        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="relative flex-1">
            <LucideSearch className="w-5 h-5 absolute left-3.5 top-3.5 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Задайте любой вопрос по всей платформе..."
              className="pl-11 h-12 text-sm rounded-xl"
            />
          </div>
          <Button
            type="submit"
            disabled={loading}
            className="h-12 px-6 font-medium"
          >
            {loading ? 'Анализ...' : 'Искать'}
          </Button>
        </form>

        <div className="flex flex-wrap items-center gap-2 pt-2">
          <span className="text-xs text-muted-foreground">Примеры:</span>
          {SAMPLE_QUERIES.map((sq) => (
            <button
              key={sq}
              type="button"
              onClick={() => {
                setQuery(sq);
              }}
              className="text-xs px-3 py-1 rounded-lg border border-border hover:border-primary text-muted-foreground transition-colors"
            >
              {sq}
            </button>
          ))}
        </div>
      </div>

      {results && (
        <div className="space-y-6">
          <div className="bg-gradient-to-br from-primary/15 via-background to-background rounded-2xl p-6 border border-primary/30 shadow-md space-y-3">
            <div className="flex items-center gap-2 text-primary font-bold text-sm">
              <LucideSparkles className="w-5 h-5" />
              Ответ ИИ на основе Всей Памяти Платформы
            </div>
            <p className="text-sm leading-relaxed">{results.ai_synthesis}</p>
          </div>

          {results.experts.length > 0 && (
            <div className="space-y-3">
              <h4 className="font-bold text-base flex items-center gap-2">
                <LucideUserCheck className="w-5 h-5 text-blue-400" />
                Найденные Эксперты на Платформе
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {results.experts.map((exp, i) => (
                  <div
                    key={i}
                    className="bg-background p-4 rounded-xl border border-border space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-base">{exp.name}</span>
                      <span className="text-xs px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 font-bold border border-blue-500/20">
                        {Math.round(exp.confidence_score * 100)}% Уверенность
                      </span>
                    </div>
                    <div className="text-xs font-semibold text-primary">{exp.domain_topic} ({exp.depth_level})</div>
                    <p className="text-xs text-muted-foreground">{exp.evidence}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {results.decisions.length > 0 && (
            <div className="space-y-3">
              <h4 className="font-bold text-base flex items-center gap-2">
                <LucideFileCheck className="w-5 h-5 text-emerald-400" />
                Принятые Архитектурные Решения
              </h4>
              <div className="space-y-2">
                {results.decisions.map((dec, i) => (
                  <div
                    key={i}
                    className="bg-background p-4 rounded-xl border border-border flex items-center justify-between text-xs"
                  >
                    <div className="space-y-1">
                      <div className="font-bold text-sm">{dec.decision}</div>
                      <div className="text-muted-foreground">Ответственный: <span className="font-medium">{dec.owner}</span></div>
                    </div>
                    <span className="text-[11px] text-emerald-400 font-mono px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20">
                      Подтверждено ИИ
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
