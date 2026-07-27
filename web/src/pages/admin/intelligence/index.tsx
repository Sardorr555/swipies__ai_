import { useState } from 'react';
import { IntelligenceGraphView } from './graph-view';
import { IntelligenceSearchView } from './search-view';
import { IntelligenceDigestView } from './digest-view';
import { IntelligenceTimelineView } from './timeline-view';
import { IntelligenceRoiView } from './roi-view';
import { IntelligenceWikiBuilderView } from './wiki-builder-view';
import { IntelligenceSimulatorView } from './simulator-view';
import { LucideNetwork, LucideBrain, LucideBarChart3, LucideClock, LucideCoins, LucideBookOpen, LucideCpu } from 'lucide-react';

export default function AdminIntelligence() {
  const [activeTab, setActiveTab] = useState<'graph' | 'search' | 'digest' | 'wiki' | 'simulator' | 'timeline' | 'roi'>('graph');

  return (
    <div className="flex flex-col gap-6 size-full p-6 bg-background/40 rounded-2xl overflow-y-auto">
      {/* Top Header and Tab Navigation */}
      <div className="flex flex-col xl:flex-row items-start xl:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <h2 className="text-2xl font-bold">Enterprise Intelligence 3.0 (Панель Администратора)</h2>
          <p className="text-xs text-muted-foreground mt-1">
            Проактивный Мозг Организации: Сеть знаний, Умный поиск, Авто-Вики, "What-If" Симулятор и ROI
          </p>
        </div>

        {/* Tab Buttons */}
        <div className="flex flex-wrap items-center gap-2 bg-background p-1.5 rounded-xl border border-border">
          <button
            type="button"
            onClick={() => setActiveTab('graph')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'graph'
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <LucideNetwork className="w-3.5 h-3.5" />
            1. Сеть Знаний
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('search')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'search'
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <LucideBrain className="w-3.5 h-3.5" />
            2. Умный Поиск
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('digest')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'digest'
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <LucideBarChart3 className="w-3.5 h-3.5" />
            3. Дайджест & Экспорт
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('wiki')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'wiki'
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <LucideBookOpen className="w-3.5 h-3.5" />
            4. Авто-Вики
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('simulator')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'simulator'
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <LucideCpu className="w-3.5 h-3.5" />
            5. "What-If" Симулятор
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('timeline')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'timeline'
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <LucideClock className="w-3.5 h-3.5" />
            6. Таймлайн
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('roi')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'roi'
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <LucideCoins className="w-3.5 h-3.5" />
            7. ROI & Настроения
          </button>
        </div>
      </div>

      {/* Active Tab View */}
      <div className="flex-1 w-full">
        {activeTab === 'graph' && <IntelligenceGraphView />}
        {activeTab === 'search' && <IntelligenceSearchView />}
        {activeTab === 'digest' && <IntelligenceDigestView />}
        {activeTab === 'wiki' && <IntelligenceWikiBuilderView />}
        {activeTab === 'simulator' && <IntelligenceSimulatorView />}
        {activeTab === 'timeline' && <IntelligenceTimelineView />}
        {activeTab === 'roi' && <IntelligenceRoiView />}
      </div>
    </div>
  );
}
