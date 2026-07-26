import { useState } from 'react';
import { IntelligenceGraphView } from './graph-view';
import { IntelligenceSearchView } from './search-view';
import { IntelligenceDigestView } from './digest-view';
import { LucideNetwork, LucideBrain, LucideBarChart3 } from 'lucide-react';

export default function UserSettingIntelligence() {
  const [activeTab, setActiveTab] = useState<'graph' | 'search' | 'digest'>('graph');

  return (
    <div className="flex flex-col gap-6 size-full p-6 bg-bg-component/40 rounded-2xl overflow-y-auto">
      {/* Top Header and Tab Navigation */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-border-button">
        <div>
          <h2 className="text-2xl font-bold text-text-primary">Enterprise Intelligence Center</h2>
          <p className="text-xs text-text-disabled mt-1">
            Единая панель управления знаниями, графом связей и аналитикой компании
          </p>
        </div>

        {/* Tab Buttons */}
        <div className="flex items-center gap-2 bg-bg-component p-1.5 rounded-xl border border-border-button">
          <button
            type="button"
            onClick={() => setActiveTab('graph')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'graph'
                ? 'bg-accent-primary text-white shadow-md'
                : 'text-text-disabled hover:text-text-primary'
            }`}
          >
            <LucideNetwork className="w-4 h-4" />
            1. Сеть Знаний (Graph)
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('search')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'search'
                ? 'bg-accent-primary text-white shadow-md'
                : 'text-text-disabled hover:text-text-primary'
            }`}
          >
            <LucideBrain className="w-4 h-4" />
            2. Умный Поиск (AI Search)
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('digest')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'digest'
                ? 'bg-accent-primary text-white shadow-md'
                : 'text-text-disabled hover:text-text-primary'
            }`}
          >
            <LucideBarChart3 className="w-4 h-4" />
            3. Дайджест Руководства
          </button>
        </div>
      </div>

      {/* Active Tab View */}
      <div className="flex-1 w-full">
        {activeTab === 'graph' && <IntelligenceGraphView />}
        {activeTab === 'search' && <IntelligenceSearchView />}
        {activeTab === 'digest' && <IntelligenceDigestView />}
      </div>
    </div>
  );
}
