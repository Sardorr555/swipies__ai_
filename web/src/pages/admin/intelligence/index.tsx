import { useState } from 'react';
import { IntelligenceGraphView } from './graph-view';
import { IntelligenceSearchView } from './search-view';
import { IntelligenceDigestView } from './digest-view';
import { IntelligenceTimelineView } from './timeline-view';
import { IntelligenceRoiView } from './roi-view';
import { LucideNetwork, LucideBrain, LucideBarChart3, LucideClock, LucideCoins } from 'lucide-react';

export default function AdminIntelligence() {
  const [activeTab, setActiveTab] = useState<'graph' | 'search' | 'digest' | 'timeline' | 'roi'>('graph');

  return (
    <div className="flex flex-col gap-6 size-full p-6 bg-background/40 rounded-2xl overflow-y-auto">
      {/* Top Header and Tab Navigation */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <h2 className="text-2xl font-bold">Enterprise Intelligence 2.0 (Панель Администратора)</h2>
          <p className="text-xs text-muted-foreground mt-1">
            Глобальный Мозг Организации: Сеть знаний, умный поиск, таймлайн решений и аналитика ROI
          </p>
        </div>

        {/* Tab Buttons */}
        <div className="flex flex-wrap items-center gap-2 bg-background p-1.5 rounded-xl border border-border">
          <button
            type="button"
            onClick={() => setActiveTab('graph')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'graph'
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <LucideNetwork className="w-4 h-4" />
            1. Сеть Знаний
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('search')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'search'
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <LucideBrain className="w-4 h-4" />
            2. Умный Поиск
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('digest')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'digest'
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <LucideBarChart3 className="w-4 h-4" />
            3. Дайджест Руководства
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('timeline')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'timeline'
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <LucideClock className="w-4 h-4" />
            4. Таймлайн Решений
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('roi')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'roi'
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <LucideCoins className="w-4 h-4" />
            5. Аналитика ROI & Настроений
          </button>
        </div>
      </div>

      {/* Active Tab View */}
      <div className="flex-1 w-full">
        {activeTab === 'graph' && <IntelligenceGraphView />}
        {activeTab === 'search' && <IntelligenceSearchView />}
        {activeTab === 'digest' && <IntelligenceDigestView />}
        {activeTab === 'timeline' && <IntelligenceTimelineView />}
        {activeTab === 'roi' && <IntelligenceRoiView />}
      </div>
    </div>
  );
}
