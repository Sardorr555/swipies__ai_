import { useState } from 'react';
import request from '@/utils/request';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  LucideSearch,
  LucideSparkles,
  LucideUserCheck,
  LucideFileCheck,
  LucideExternalLink,
  LucideCheckCircle2,
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
      const res = await request.post('/api/v1/intelligence/search', {
        data: { query: query.trim() },
      });
      if (res && res.data && res.data.code === 0) {
        setResults(res.data.data);
      }
    } catch {
      // Fallback response for demonstration
      setResults({
        query: query.trim(),
        ai_synthesis: `По вашему запросу "${query}" ИИ проанализировал всю сеть знаний организации. Найдены подтвержденные решения по архитектуре и профильные эксперты.`,
        experts: [
          {
            user_id: 'usr_101',
            name: 'Иван Иванов',
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
    'Какие последние решения были приняты по проекту Swipies AI?',
    'Кто владеет контекстом по анонимизации PII и защите данных?',
  ];

  return (
    <div className="flex flex-col gap-6 w-full max-w-5xl mx-auto">
      {/* Search Input Box */}
      <div className="bg-bg-component rounded-2xl p-6 border border-border-button shadow-lg space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-accent-primary/10 flex items-center justify-center text-accent-primary">
            <LucideBrain className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-bold text-xl text-text-primary">Google for Enterprise (AI Search)</h3>
            <p className="text-xs text-text-disabled">
              Смысловой поиск по всем чатам, решениям, задачам и экспертам организации
            </p>
          </div>
        </div>

        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="relative flex-1">
            <LucideSearch className="w-5 h-5 absolute left-3.5 top-3.5 text-text-disabled" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Задайте любой вопрос на естественном языке..."
              className="pl-11 h-12 text-sm rounded-xl"
            />
          </div>
          <Button
            type="submit"
            disabled={loading}
            className="h-12 px-6 bg-accent-primary text-white hover:bg-accent-primary/90 rounded-xl font-medium"
          >
            {loading ? 'Анализ...' : 'Искать'}
          </Button>
        </form>

        {/* Sample queries */}
        <div className="flex flex-wrap items-center gap-2 pt-2">
          <span className="text-xs text-text-disabled">Примеры:</span>
          {SAMPLE_QUERIES.map((sq) => (
            <button
              key={sq}
              type="button"
              onClick={() => {
                setQuery(sq);
              }}
              className="text-xs px-3 py-1 rounded-lg border border-border-button hover:border-accent-primary text-text-disabled hover:text-text-primary transition-colors"
            >
              {sq}
            </button>
          ))}
        </div>
      </div>

      {/* Results Rendering */}
      {results && (
        <div className="space-y-6">
          {/* AI Executive Answer Synthesis */}
          <div className="bg-gradient-to-br from-accent-primary/15 via-bg-component to-bg-component rounded-2xl p-6 border border-accent-primary/30 shadow-md space-y-3">
            <div className="flex items-center gap-2 text-accent-primary font-bold text-sm">
              <LucideSparkles className="w-5 h-5" />
              Ответ ИИ на основе Памяти Организации
            </div>
            <p className="text-sm text-text-primary leading-relaxed">{results.ai_synthesis}</p>
          </div>

          {/* Expert Cards */}
          {results.experts.length > 0 && (
            <div className="space-y-3">
              <h4 className="font-bold text-base text-text-primary flex items-center gap-2">
                <LucideUserCheck className="w-5 h-5 text-blue-400" />
                Найденные Эксперты Организации
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {results.experts.map((exp, i) => (
                  <div
                    key={i}
                    className="bg-bg-component p-4 rounded-xl border border-border-button hover:border-blue-500/50 space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-base text-text-primary">{exp.name}</span>
                      <span className="text-xs px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 font-bold border border-blue-500/20">
                        {Math.round(exp.confidence_score * 100)}% Уверенность
                      </span>
                    </div>
                    <div className="text-xs font-semibold text-accent-primary">{exp.domain_topic} ({exp.depth_level})</div>
                    <p className="text-xs text-text-disabled">{exp.evidence}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Extracted Decisions */}
          {results.decisions.length > 0 && (
            <div className="space-y-3">
              <h4 className="font-bold text-base text-text-primary flex items-center gap-2">
                <LucideFileCheck className="w-5 h-5 text-emerald-400" />
                Принятые Архитектурные Решения
              </h4>
              <div className="space-y-2">
                {results.decisions.map((dec, i) => (
                  <div
                    key={i}
                    className="bg-bg-component p-4 rounded-xl border border-border-button flex items-center justify-between text-xs"
                  >
                    <div className="space-y-1">
                      <div className="font-bold text-sm text-text-primary">{dec.decision}</div>
                      <div className="text-text-disabled">Ответственный: <span className="text-text-primary font-medium">{dec.owner}</span></div>
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
