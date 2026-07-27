import { useState } from 'react';
import request from '@/utils/request';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  LucideSearch,
  LucideBrain,
  LucideUserCheck,
  LucideCheckCircle2,
  LucideSparkles,
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
  user_id: string;
  confidence: number;
  conversation_id: string;
}

interface SearchResults {
  query: string;
  ai_synthesis: string;
  experts: ExpertItem[];
  decisions: DecisionItem[];
  source_snippets: { title: string; snippet: string }[];
}

export function IntelligenceSearchView() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResults | null>(null);

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
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 w-full max-w-5xl mx-auto">
      {/* Search Header */}
      <div className="bg-background rounded-2xl p-6 border border-border shadow-lg space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
            <LucideBrain className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-bold text-xl">"Google for Enterprise" Интеллектуальный Поиск</h3>
            <p className="text-xs text-muted-foreground">
              Единый гибридный ИИ-поиск по принятым решениям, знаниям и профильным экспертам организации
            </p>
          </div>
        </div>

        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="relative flex-1">
            <LucideSearch className="w-5 h-5 absolute left-3.5 top-3.5 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Спросите ИИ (например: Кто отвечает за HNSW индексы или какие решения принимались по API)..."
              className="pl-11 h-12 text-sm rounded-xl bg-background"
            />
          </div>
          <Button type="submit" disabled={loading} className="h-12 px-6 font-medium gap-2">
            <LucideSparkles className="w-4 h-4" />
            {loading ? 'Идет синтез...' : 'Искать'}
          </Button>
        </form>
      </div>

      {/* Results Container */}
      {results && (
        <div className="space-y-6">
          {/* AI Synthesis Box */}
          <div className="bg-gradient-to-br from-primary/10 via-background to-background rounded-2xl p-6 border border-primary/30 shadow-md space-y-2">
            <div className="flex items-center gap-2 text-primary font-bold text-sm">
              <LucideSparkles className="w-4 h-4" />
              ИИ-Синтез Ответа
            </div>
            <p className="text-sm leading-relaxed font-medium">{results.ai_synthesis}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Found Decisions */}
            <div className="bg-background rounded-2xl p-5 border border-border space-y-3">
              <h4 className="font-bold text-base flex items-center gap-2 text-emerald-400">
                <LucideCheckCircle2 className="w-5 h-5" />
                Принятые Решения и Задачи ({results.decisions.length})
              </h4>

              <div className="space-y-2">
                {results.decisions.length > 0 ? (
                  results.decisions.map((dec, i) => (
                    <div key={i} className="p-3.5 rounded-xl border border-border bg-background/50 space-y-1 text-xs">
                      <div className="font-bold text-foreground">{dec.decision}</div>
                      <div className="flex items-center justify-between text-muted-foreground pt-1">
                        <span>Автор: <strong className="text-foreground">{dec.owner}</strong></span>
                        <span className="font-mono text-emerald-400">Диалог #{dec.conversation_id}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-muted-foreground">Решений по данному запросу не найдено.</p>
                )}
              </div>
            </div>

            {/* Found Experts */}
            <div className="bg-background rounded-2xl p-5 border border-border space-y-3">
              <h4 className="font-bold text-base flex items-center gap-2 text-primary">
                <LucideUserCheck className="w-5 h-5" />
                Профильные Эксперты Организации ({results.experts.length})
              </h4>

              <div className="space-y-2">
                {results.experts.length > 0 ? (
                  results.experts.map((exp, i) => (
                    <div key={i} className="p-3.5 rounded-xl border border-primary/20 bg-primary/5 space-y-1 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-foreground">{exp.name}</span>
                        <span className="text-primary font-mono font-bold">
                          Уровень: {exp.depth_level}
                        </span>
                      </div>
                      <div className="text-muted-foreground text-[11px] font-semibold">Тема: {exp.domain_topic}</div>
                      <p className="text-muted-foreground text-[11px] italic">{exp.evidence}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-muted-foreground">Эксперты по данной теме не выявлены.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
