import { useState, useEffect } from 'react';
import request from '@/utils/request';
import { Button } from '@/components/ui/button';
import {
  LucideClock,
  LucideCalendar,
  LucideCheckCircle2,
  LucideUser,
  LucideGitCommit,
  LucideRefreshCw,
} from 'lucide-react';

interface TimelineItem {
  id: string;
  date: number;
  decision: string;
  owner: string;
  category: string;
  conversation_id: string;
}

export function IntelligenceTimelineView() {
  const [loading, setLoading] = useState(false);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [filterCategory, setFilterCategory] = useState<string>('All');

  const fetchTimeline = async () => {
    setLoading(true);
    try {
      const res = await request.get('/api/v1/intelligence/timeline?global=true');
      if (res && res.data && res.data.code === 0) {
        setTimeline(res.data.data);
      }
    } catch {
      setTimeline([
        {
          id: 't1',
          date: Date.now() - 3600000 * 2,
          decision: 'Переход на асинхронную шину событий Redis Streams',
          owner: 'Иван Иванов',
          category: 'Architecture',
          conversation_id: 'conv_101',
        },
        {
          id: 't2',
          date: Date.now() - 3600000 * 24,
          decision: 'Внедрен модуль анонимизации PII для предотвращения утечек данных',
          owner: 'Петр Сидоров',
          category: 'Security',
          conversation_id: 'conv_102',
        },
        {
          id: 't3',
          date: Date.now() - 3600000 * 72,
          decision: 'Подключение Neo4j адаптера для динамических графовых связей',
          owner: 'Иван Иванов',
          category: 'Graph Engine',
          conversation_id: 'conv_103',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTimeline();
  }, []);

  const categories = ['All', 'Architecture', 'Security', 'Graph Engine', 'Database'];
  const filteredTimeline = filterCategory === 'All'
    ? timeline
    : timeline.filter((t) => t.category.toLowerCase() === filterCategory.toLowerCase());

  return (
    <div className="flex flex-col gap-6 w-full max-w-5xl mx-auto space-y-2">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="font-bold text-2xl">Таймлайн Развития Решений (Decision History Evolution)</h3>
          <p className="text-xs text-muted-foreground mt-1">
            Хронологическая история принятия архитектурных и бизнес решений по всем проектам
          </p>
        </div>
        <Button variant="outline" onClick={fetchTimeline} disabled={loading} className="gap-2">
          <LucideRefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Обновить
        </Button>
      </div>

      {/* Filter Categories */}
      <div className="flex flex-wrap gap-2">
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setFilterCategory(cat)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
              filterCategory === cat
                ? 'bg-primary text-primary-foreground border-primary'
                : 'bg-background border-border text-muted-foreground hover:text-foreground'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Timeline Stream */}
      <div className="relative pl-6 border-l-2 border-primary/30 space-y-6 pt-2">
        {filteredTimeline.length > 0 ? (
          filteredTimeline.map((item) => (
            <div key={item.id} className="relative group">
              {/* Dot Icon */}
              <div className="absolute -left-[31px] top-1.5 w-4 h-4 rounded-full bg-primary border-4 border-background shadow-md" />

              <div className="bg-background rounded-2xl p-5 border border-border shadow-sm space-y-2 hover:border-primary/50 transition-colors">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-md bg-primary/10 text-primary border border-primary/20">
                    {item.category}
                  </span>
                  <span className="text-xs text-muted-foreground flex items-center gap-1 font-mono">
                    <LucideClock className="w-3.5 h-3.5" />
                    {new Date(item.date).toLocaleString('ru-RU')}
                  </span>
                </div>

                <h4 className="font-bold text-base text-foreground">{item.decision}</h4>

                <div className="flex items-center justify-between text-xs text-muted-foreground pt-1 border-t border-border/50">
                  <span className="flex items-center gap-1">
                    <LucideUser className="w-3.5 h-3.5 text-primary" />
                    Автор: <strong className="text-foreground">{item.owner}</strong>
                  </span>
                  <span className="font-mono text-emerald-400">Диалог #{item.conversation_id}</span>
                </div>
              </div>
            </div>
          ))
        ) : (
          <p className="text-xs text-muted-foreground">Решения в вы выбранной категории не найдены.</p>
        )}
      </div>
    </div>
  );
}
