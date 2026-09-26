import { fireEvent, render, screen } from '@testing-library/react';
import { GuideTab } from '../tabs/GuideTab';
import { PublisherTab } from '../tabs/PublisherTab';
import { FraudTab } from '../tabs/FraudTab';
import { TeamTab } from '../tabs/TeamTab';
import { InsightsTab } from '../tabs/InsightsTab';
import { BillingTab } from '../tabs/BillingTab';
import { SettingsTab } from '../tabs/SettingsTab';
import { AttributionTab } from '../tabs/AttributionTab';
import { AnalyticsTab } from '../tabs/AnalyticsTab';
import {
  AdTransactionItem,
  AdvertiserInsightsData,
  AdvertiserSettingsData,
  AttributionSummaryResponse,
  TimelineAnalyticsData,
  BlacklistEntryItem,
  ConversionJourneyPath,
  FraudOverviewData,
  FunnelAnalyticsResponse,
  NotificationSettingsData,
  PlacementItem,
  PublisherPayoutItem,
  PublisherProfileData,
  SavedPaymentMethodItem,
  TeamMemberItem,
  UserSubscriptionData,
} from '@/services/ad-service';

describe('Ads Tabs Render Suite', () => {
  beforeAll(() => {
    if (typeof window !== 'undefined' && !window.ResizeObserver) {
      class ResizeObserverMock {
        callback: any;
        constructor(callback: any) {
          this.callback = callback;
        }
        observe(target: any) {
          if (this.callback) {
            this.callback([
              {
                target,
                contentRect: { width: 800, height: 280, top: 0, left: 0, bottom: 280, right: 800, x: 0, y: 0 },
              },
            ]);
          }
        }
        unobserve() {}
        disconnect() {}
      }
      window.ResizeObserver = ResizeObserverMock as any;
      (globalThis as any).ResizeObserver = ResizeObserverMock as any;
    }
  });

  describe('GuideTab', () => {
    it('renders without throwing exceptions', () => {
      expect(() => render(<GuideTab />)).not.toThrow();
    });

    it('renders all three core principles cards and headings', () => {
      render(<GuideTab />);

      expect(screen.getByText('The Swipies Ads Principles')).toBeInTheDocument();
      expect(screen.getByText(/How native AI intent recommendations work/i)).toBeInTheDocument();
      expect(screen.getByText(/1\. Intent & Semantic Matching/i)).toBeInTheDocument();
      expect(screen.getByText(/2\. Transparent & Non-Intrusive/i)).toBeInTheDocument();
      expect(screen.getByText(/3\. Performance Driven \(CPC\/CPM\)/i)).toBeInTheDocument();
      expect(screen.getByText('[Sponsored]')).toBeInTheDocument();
    });
  });

  describe('PublisherTab', () => {
    const mockPublisher: PublisherProfileData = {
      id: 'pub-1',
      name: 'Test Publisher',
      api_key: 'pub_live_abc123xyz',
      balance: 125.5,
      total_earned: 500.0,
      total_withdrawn: 374.5,
      default_rev_share: 0.7,
      payout_card: '8600 **** 1234',
      payout_holder: 'Sardor A.',
      status: 'active',
    };

    const mockPlacement: PlacementItem = {
      id: 'plc-1',
      publisher_id: 'pub-1',
      name: 'AI Support Bot',
      domain_or_bot: '@swipies_support_bot',
      placement_type: 'telegram_bot',
      rev_share_rate: 0.7,
      status: 'active',
      impressions: 12500,
      clicks: 450,
      earnings: 87.5,
      create_time: 1700000000000,
    };

    const mockPayout: PublisherPayoutItem = {
      id: 'pay-1',
      publisher_id: 'pub-1',
      amount: 50.0,
      currency: 'USD',
      destination_card: '8600 **** 1234',
      destination_holder: 'Sardor A.',
      status: 'paid',
      note: 'Auto payout',
      create_time: 1700000000000,
    };

    it('renders empty state without crashing', () => {
      const { container } = render(
        <PublisherTab
          publisher={null}
          placements={[]}
          payouts={[]}
          onRefresh={jest.fn()}
          onRegenerateKey={jest.fn()}
          onDeletePlacement={jest.fn()}
          onOpenPlacementModal={jest.fn()}
          onOpenPayoutModal={jest.fn()}
          onOpenSdkSnippetModal={jest.fn()}
        />,
      );

      expect(container).toBeDefined();
      expect(screen.getByText(/Монетизация & Партнёрская сеть \(Publisher SDK\)/i)).toBeInTheDocument();
      expect(screen.getByText(/У вас пока нет созданных рекламных мест/i)).toBeInTheDocument();
      expect(screen.getByText(/Заявок на выплату пока не было/i)).toBeInTheDocument();
    });

    it('renders populated KPI metrics, placement rows and payout history', () => {
      render(
        <PublisherTab
          publisher={mockPublisher}
          placements={[mockPlacement]}
          payouts={[mockPayout]}
          onRefresh={jest.fn()}
          onRegenerateKey={jest.fn()}
          onDeletePlacement={jest.fn()}
          onOpenPlacementModal={jest.fn()}
          onOpenPayoutModal={jest.fn()}
          onOpenSdkSnippetModal={jest.fn()}
        />,
      );

      expect(screen.getByText('$125.50')).toBeInTheDocument();
      expect(screen.getByText('$500.00')).toBeInTheDocument();
      expect(screen.getByText('$374.50')).toBeInTheDocument();
      expect(screen.getAllByText('70%').length).toBeGreaterThanOrEqual(2);
      expect(screen.getByText('pub_live_abc123xyz')).toBeInTheDocument();
      expect(screen.getByText('AI Support Bot')).toBeInTheDocument();
      expect(screen.getByText('@swipies_support_bot')).toBeInTheDocument();
      expect(screen.getByText('$87.5000')).toBeInTheDocument();
      expect(screen.getByText('$50.00 USD')).toBeInTheDocument();
      expect(screen.getByText('✅ Выплачено')).toBeInTheDocument();
    });

    it('wires action buttons to corresponding callback props', () => {
      const onOpenPayoutModal = jest.fn();
      const onOpenPlacementModal = jest.fn();
      const onOpenSdkSnippetModal = jest.fn();
      const onDeletePlacement = jest.fn();
      const onRefresh = jest.fn();

      render(
        <PublisherTab
          publisher={mockPublisher}
          placements={[mockPlacement]}
          payouts={[mockPayout]}
          onRefresh={onRefresh}
          onRegenerateKey={jest.fn()}
          onDeletePlacement={onDeletePlacement}
          onOpenPlacementModal={onOpenPlacementModal}
          onOpenPayoutModal={onOpenPayoutModal}
          onOpenSdkSnippetModal={onOpenSdkSnippetModal}
        />,
      );

      fireEvent.click(screen.getByText(/Вывести доход/i));
      expect(onOpenPayoutModal).toHaveBeenCalledTimes(1);

      fireEvent.click(screen.getByText(/\+ Создать размещение/i));
      expect(onOpenPlacementModal).toHaveBeenCalledTimes(1);

      fireEvent.click(screen.getByText(/Код SDK/i));
      expect(onOpenSdkSnippetModal).toHaveBeenCalledWith(mockPlacement);

      const deleteBtn = screen.getByRole('button', { name: /удалить размещение/i });
      expect(deleteBtn).toBeInTheDocument();
      fireEvent.click(deleteBtn);
      expect(onDeletePlacement).toHaveBeenCalledWith('plc-1');
    });

    it('renders gracefully when placements or payouts are empty or non-array', () => {
      render(
        <PublisherTab
          publisher={null}
          placements={[] as any}
          payouts={null as any}
          onRefresh={jest.fn()}
          onRegenerateKey={jest.fn()}
          onDeletePlacement={jest.fn()}
          onOpenPlacementModal={jest.fn()}
          onOpenPayoutModal={jest.fn()}
          onOpenSdkSnippetModal={jest.fn()}
        />,
      );

      expect(screen.getByText(/У вас пока нет созданных рекламных мест/i)).toBeInTheDocument();
      expect(screen.getByText(/Заявок на выплату пока не было/i)).toBeInTheDocument();
    });

    it('renders without throwing when publisher, placement, or payout numeric fields are undefined or null', () => {
      const undefinedPublisher: any = {
        id: 'pub-undef',
        name: 'Undef Pub',
        api_key: 'key-123',
        balance: undefined,
        total_earned: null,
        total_withdrawn: undefined,
        default_rev_share: undefined,
        status: 'active',
      };

      const undefinedPlacement: any = {
        id: 'plc-undef',
        name: 'Undef Placement',
        placement_type: 'telegram_bot',
        rev_share_rate: undefined,
        impressions: undefined,
        clicks: null,
        earnings: undefined,
      };

      const undefinedPayout: any = {
        id: 'pay-undef',
        amount: undefined,
        currency: 'USD',
        create_time: 1700000000000,
        status: 'pending',
      };

      expect(() =>
        render(
          <PublisherTab
            publisher={undefinedPublisher}
            placements={[undefinedPlacement]}
            payouts={[undefinedPayout]}
            onRefresh={jest.fn()}
            onRegenerateKey={jest.fn()}
            onDeletePlacement={jest.fn()}
            onOpenPlacementModal={jest.fn()}
            onOpenPayoutModal={jest.fn()}
            onOpenSdkSnippetModal={jest.fn()}
          />,
        ),
      ).not.toThrow();

      // Expect safe defaults to be rendered
      expect(screen.getAllByText('$0.00').length).toBeGreaterThan(0);
      expect(screen.getByText('0%')).toBeInTheDocument();
      expect(screen.getByText('$0.0000')).toBeInTheDocument();
      expect(screen.getByText('$0.00 USD')).toBeInTheDocument();
    });
  });

  describe('FraudTab', () => {
    const mockFraudOverview: FraudOverviewData = {
      total_blocked_clicks: 142,
      total_cost_saved: 78.45,
      bot_detections: 95,
      active_blacklist_count: 3,
      rate_limit_blocks: 25,
      blacklist_blocks: 15,
      recent_logs: [
        {
          id: 'log-1',
          campaign_id: 'cmp-1',
          campaign_name: 'Summer AI Promo',
          event_type: 'bot_click',
          reason: 'bot_user_agent',
          ip_hash: 'abc123def4567890abcdef',
          user_agent: 'Scrapy/2.11.0',
          cost_saved: 0.55,
          create_time: 1700000000000,
        },
        {
          id: 'log-2',
          campaign_id: 'cmp-2',
          campaign_name: 'Telegram Bot Ads',
          event_type: 'datacenter_ip',
          reason: 'blacklist_ip',
          ip_hash: 'deadbeef12345678cafe',
          user_agent: 'Mozilla/5.0',
          cost_saved: 1.2,
          create_time: 1700000000000,
        },
        {
          id: 'log-3',
          campaign_id: 'cmp-3',
          campaign_name: 'Search Boost',
          event_type: 'rapid_clicks',
          reason: 'rapid_repeat_clicks',
          ip_hash: '99887766554433221100',
          user_agent: 'HeadlessChrome',
          cost_saved: 0.8,
          create_time: 1700000000000,
        },
      ],
    };

    const mockFraudBlacklist: BlacklistEntryItem[] = [
      {
        id: 'bl-1',
        ip_address: '192.168.1.100',
        is_system: false,
        reason: 'Manual block by admin',
        status: 'active',
        create_time: 1700000000000,
        auto_expires_at: 1727280000000,
      },
      {
        id: 'bl-2',
        ip_address: '10.0.0.1/24',
        is_system: true,
        reason: 'Known DC datacenter range',
        status: 'active',
        create_time: 1700000000000,
        auto_expires_at: undefined,
      },
    ];

    it('renders empty state without crashing', () => {
      const { container } = render(
        <FraudTab
          fraudOverview={null}
          fraudBlacklist={[]}
          onRefresh={jest.fn()}
          onOpenBlacklistModal={jest.fn()}
          onRemoveBlacklist={jest.fn()}
        />,
      );

      expect(container).toBeDefined();
      expect(screen.getByText('Anti-Fraud Shield & Защита от скликивания')).toBeInTheDocument();
      expect(
        screen.getByText(/Многоуровневая система фильтрации ботов, повторных кликов и датацентровых прокси/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/Подозрительной активности не зафиксировано/i)).toBeInTheDocument();
      expect(screen.getByText(/Черный список пуст/i)).toBeInTheDocument();
    });

    it('renders populated KPI metrics, live fraud incident logs and blacklist items', () => {
      render(
        <FraudTab
          fraudOverview={mockFraudOverview}
          fraudBlacklist={mockFraudBlacklist}
          onRefresh={jest.fn()}
          onOpenBlacklistModal={jest.fn()}
          onRemoveBlacklist={jest.fn()}
        />,
      );

      // KPI checks
      expect(screen.getByText('142')).toBeInTheDocument();
      expect(screen.getByText('$78.45')).toBeInTheDocument();
      expect(screen.getByText('95')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();

      // Incident logs checks
      expect(screen.getByText('Summer AI Promo')).toBeInTheDocument();
      expect(screen.getByText('🤖 Бот / Web Scraper')).toBeInTheDocument();
      expect(screen.getByText('+$0.55')).toBeInTheDocument();

      expect(screen.getByText('Telegram Bot Ads')).toBeInTheDocument();
      expect(screen.getByText('🚫 Заблокированный IP')).toBeInTheDocument();
      expect(screen.getByText('+$1.20')).toBeInTheDocument();

      expect(screen.getByText('Search Boost')).toBeInTheDocument();
      expect(screen.getByText('⚡ Скликивание (>2 в мин)')).toBeInTheDocument();
      expect(screen.getByText('+$0.80')).toBeInTheDocument();

      // Blacklist table checks
      expect(screen.getByText('192.168.1.100')).toBeInTheDocument();
      expect(screen.getByText('👤 Персональный')).toBeInTheDocument();
      expect(screen.getByText('Manual block by admin')).toBeInTheDocument();

      expect(screen.getByText('10.0.0.1/24')).toBeInTheDocument();
      expect(screen.getByText('🌐 Системный глобальный')).toBeInTheDocument();
      expect(screen.getByText('Known DC datacenter range')).toBeInTheDocument();
      expect(screen.getByText('Бессрочно')).toBeInTheDocument();
    });

    it('wires action buttons to corresponding callback props', () => {
      const onOpenBlacklistModal = jest.fn();
      const onRefresh = jest.fn();
      const onRemoveBlacklist = jest.fn();

      render(
        <FraudTab
          fraudOverview={mockFraudOverview}
          fraudBlacklist={mockFraudBlacklist}
          onRefresh={onRefresh}
          onOpenBlacklistModal={onOpenBlacklistModal}
          onRemoveBlacklist={onRemoveBlacklist}
        />,
      );

      // Header "Заблокировать IP" button
      fireEvent.click(screen.getByRole('button', { name: /заблокировать ip/i }));
      expect(onOpenBlacklistModal).toHaveBeenCalledTimes(1);

      // Blacklist table "Добавить IP" button
      fireEvent.click(screen.getByRole('button', { name: /добавить ip/i }));
      expect(onOpenBlacklistModal).toHaveBeenCalledTimes(2);

      // Refresh button
      fireEvent.click(screen.getByRole('button', { name: /обновить данные антифрода/i }));
      expect(onRefresh).toHaveBeenCalledTimes(1);

      // Unblock button for personal rule (semantic role test per user guidance)
      const unblockBtn = screen.getByRole('button', { name: /разблокировать/i });
      expect(unblockBtn).toBeInTheDocument();
      fireEvent.click(unblockBtn);
      expect(onRemoveBlacklist).toHaveBeenCalledWith('bl-1');
    });

    it('renders gracefully when recent_logs or fraudBlacklist are null or non-array', () => {
      const corruptOverview: any = {
        total_blocked_clicks: 0,
        total_cost_saved: 0,
        bot_detections: 0,
        active_blacklist_count: 0,
        recent_logs: null,
      };

      render(
        <FraudTab
          fraudOverview={corruptOverview}
          fraudBlacklist={null as any}
          onRefresh={jest.fn()}
          onOpenBlacklistModal={jest.fn()}
          onRemoveBlacklist={jest.fn()}
        />,
      );

      expect(screen.getByText(/Подозрительной активности не зафиксировано/i)).toBeInTheDocument();
      expect(screen.getByText(/Черный список пуст/i)).toBeInTheDocument();
    });

    it('renders without throwing when numeric fields are undefined, null, or invalid', () => {
      const undefinedFraudOverview: any = {
        total_blocked_clicks: undefined,
        total_cost_saved: undefined,
        bot_detections: null,
        active_blacklist_count: undefined,
        recent_logs: [
          {
            id: 'log-undef',
            campaign_name: 'Undef Promo',
            reason: 'bot_user_agent',
            ip_hash: null,
            user_agent: 'Curl',
            cost_saved: undefined,
            create_time: null,
          },
        ],
      };

      expect(() =>
        render(
          <FraudTab
            fraudOverview={undefinedFraudOverview}
            fraudBlacklist={[]}
            onRefresh={jest.fn()}
            onOpenBlacklistModal={jest.fn()}
            onRemoveBlacklist={jest.fn()}
          />,
        ),
      ).not.toThrow();

      expect(screen.getByText('$0.00')).toBeInTheDocument();
      expect(screen.getByText('+$0.00')).toBeInTheDocument();
      expect(screen.getByText('Undef Promo')).toBeInTheDocument();
    });
  });

  describe('TeamTab', () => {
    const mockTeamMembers: TeamMemberItem[] = [
      {
        id: 'member-1',
        advertiser_id: 'adv-123',
        email: 'admin@swipies.ai',
        role: 'admin',
        status: 'active',
        create_time: 1700000000000,
      },
      {
        id: 'member-2',
        advertiser_id: 'adv-123',
        email: 'marketer@swipies.ai',
        role: 'manager',
        status: 'active',
        create_time: 1705000000000,
      },
    ];

    it('renders without throwing exceptions with empty members', () => {
      expect(() =>
        render(
          <TeamTab
            teamMembers={[]}
            loadingTeam={false}
            onOpenInviteModal={jest.fn()}
            onRefresh={jest.fn()}
            onUpdateRole={jest.fn()}
            onDeleteMember={jest.fn()}
          />,
        ),
      ).not.toThrow();

      expect(screen.getByText('Командный доступ & Роли')).toBeInTheDocument();
      expect(
        screen.getByText(
          'У вас пока нет приглашенных участников. Вы единственный владелец кабинета.',
        ),
      ).toBeInTheDocument();
    });

    it('renders roles matrix cards', () => {
      render(
        <TeamTab
          teamMembers={[]}
          loadingTeam={false}
          onOpenInviteModal={jest.fn()}
          onRefresh={jest.fn()}
          onUpdateRole={jest.fn()}
          onDeleteMember={jest.fn()}
        />,
      );

      expect(screen.getByText('👑 Администратор')).toBeInTheDocument();
      expect(screen.getByText('🎯 Маркетолог')).toBeInTheDocument();
      expect(screen.getByText('📊 Аналитик')).toBeInTheDocument();
      expect(screen.getByText('💳 Бухгалтерия')).toBeInTheDocument();
    });

    it('renders members table when teamMembers are provided', () => {
      render(
        <TeamTab
          teamMembers={mockTeamMembers}
          loadingTeam={false}
          onOpenInviteModal={jest.fn()}
          onRefresh={jest.fn()}
          onUpdateRole={jest.fn()}
          onDeleteMember={jest.fn()}
        />,
      );

      expect(screen.getByText('admin@swipies.ai')).toBeInTheDocument();
      expect(screen.getByText('marketer@swipies.ai')).toBeInTheDocument();
      expect(screen.getAllByText('🟢 Активен')).toHaveLength(2);
    });

    it('wires action buttons properly (invite, refresh, delete)', () => {
      const handleOpenInvite = jest.fn();
      const handleRefresh = jest.fn();
      const handleDelete = jest.fn();

      render(
        <TeamTab
          teamMembers={mockTeamMembers}
          loadingTeam={false}
          onOpenInviteModal={handleOpenInvite}
          onRefresh={handleRefresh}
          onUpdateRole={jest.fn()}
          onDeleteMember={handleDelete}
        />,
      );

      const inviteBtn = screen.getByText(/\+ Пригласить участника/i);
      fireEvent.click(inviteBtn);
      expect(handleOpenInvite).toHaveBeenCalledTimes(1);

      const refreshBtn = screen.getByLabelText('Обновить список участников');
      fireEvent.click(refreshBtn);
      expect(handleRefresh).toHaveBeenCalledTimes(1);

      const deleteBtn = screen.getByLabelText('Отозвать доступ marketer@swipies.ai');
      fireEvent.click(deleteBtn);
      expect(handleDelete).toHaveBeenCalledWith('member-2');
    });
  });

  describe('InsightsTab', () => {
    const mockInsightsData: AdvertiserInsightsData = {
      score: 84,
      total_insights: 5,
      insights: [
        {
          id: 'ins-1',
          campaign_id: 'cmp-1',
          campaign_name: 'Summer AI Sale',
          type: 'negative_keywords',
          category: 'cost',
          severity: 'high',
          title: 'Добавьте минус-слова для экономии бюджета',
          description: 'Обнаружено 15 нецелевых поисковых запросов.',
          estimated_impact: 'Экономия ~15% бюджета',
          suggested_action: 'Добавить "бесплатно, torrent, скачать" в минус-слова',
          action_payload: { keywords: ['бесплатно', 'torrent'] },
        },
        {
          id: 'ins-2',
          campaign_id: 'cmp-2',
          campaign_name: 'B2B Leads Campaign',
          type: 'ad_copy_refresh',
          category: 'quality',
          severity: 'medium',
          title: 'Обновите рекламный креатив',
          description: 'CTR креатива снизился за последние 7 дней.',
          estimated_impact: '+22% к кликабельности',
          suggested_action: 'Сгенерировать новые офферы с AI Copilot',
          action_payload: {},
        },
        {
          id: 'ins-3',
          campaign_id: 'cmp-3',
          campaign_name: 'Target CPA Scaling',
          type: 'switch_to_cpa',
          category: 'bidding',
          severity: 'low',
          title: 'Переход на автостратегию Smart CPA',
          description: 'Кампания накопила более 50 конверсий.',
          estimated_impact: 'Снижение CPA на 18%',
          suggested_action: 'Включить автоматический биддинг по целевой стоимости',
          action_payload: {},
        },
        {
          id: 'ins-4',
          campaign_id: 'cmp-4',
          campaign_name: 'Expansion Campaign',
          type: 'keyword_expansion',
          category: 'reach',
          severity: 'medium',
          title: 'Расширьте семантическое ядро',
          description: 'Найдено 40 новых релевантных фраз для таргетинга.',
          estimated_impact: '+35% к охвату',
          suggested_action: 'Добавить 40 семантических кластеров',
          action_payload: {},
        },
        {
          id: 'ins-5',
          campaign_id: 'cmp-5',
          campaign_name: 'Growth Experiments',
          type: 'ab_test_recommendation',
          category: 'growth',
          severity: 'low',
          title: 'Запустите сплит-тест заголовков',
          description: 'Текущий креатив демонстрирует усталость аудитории.',
          estimated_impact: '+10% CR',
          suggested_action: 'Создать A/B вариацию с акцентом на выгоду',
          action_payload: {},
        },
      ],
    };

    it('renders empty state when insightsData is null or empty', () => {
      render(
        <InsightsTab
          insightsData={null}
          loadingInsights={false}
          onRefresh={jest.fn()}
          onApplyInsight={jest.fn()}
        />,
      );

      expect(screen.getByText('AI Рекламный Аудит & Оптимизатор')).toBeInTheDocument();
      expect(screen.getByText('100%')).toBeInTheDocument();
      expect(screen.getByText('Кампании максимально оптимизированы!')).toBeInTheDocument();
    });

    it('renders loading state when loadingInsights is true', () => {
      render(
        <InsightsTab
          insightsData={null}
          loadingInsights={true}
          onRefresh={jest.fn()}
          onApplyInsight={jest.fn()}
        />,
      );

      expect(screen.getByText('Идет аудит рекламных кампаний...')).toBeInTheDocument();
    });

    it('renders populated recommendations cards and score badge for all 5 categories', () => {
      render(
        <InsightsTab
          insightsData={mockInsightsData}
          loadingInsights={false}
          onRefresh={jest.fn()}
          onApplyInsight={jest.fn()}
        />,
      );

      expect(screen.getByText('84%')).toBeInTheDocument();

      // Cost category
      expect(screen.getByText('Summer AI Sale')).toBeInTheDocument();
      expect(screen.getByText('Добавьте минус-слова для экономии бюджета')).toBeInTheDocument();
      expect(screen.getByText('🛡️ Защита бюджета')).toBeInTheDocument();
      expect(screen.getByText('Экономия ~15% бюджета')).toBeInTheDocument();

      // Quality category
      expect(screen.getByText('B2B Leads Campaign')).toBeInTheDocument();
      expect(screen.getByText('🎨 Оффер & CTR')).toBeInTheDocument();

      // Bidding category
      expect(screen.getByText('Target CPA Scaling')).toBeInTheDocument();
      expect(screen.getByText('⚡ Smart CPA')).toBeInTheDocument();

      // Reach category
      expect(screen.getByText('Expansion Campaign')).toBeInTheDocument();
      expect(screen.getByText('🔍 Охват запросов')).toBeInTheDocument();

      // Growth category
      expect(screen.getByText('Growth Experiments')).toBeInTheDocument();
      expect(screen.getByText('🧪 A/B Эксперимент')).toBeInTheDocument();
    });

    it('wires action buttons properly (onRefresh, onApplyInsight, applying state)', () => {
      const handleRefresh = jest.fn();
      const handleApplyInsight = jest.fn();

      const { rerender } = render(
        <InsightsTab
          insightsData={mockInsightsData}
          loadingInsights={false}
          applyingInsightId={null}
          onRefresh={handleRefresh}
          onApplyInsight={handleApplyInsight}
        />,
      );

      const refreshBtn = screen.getByRole('button', { name: /пересканировать кампании/i });
      fireEvent.click(refreshBtn);
      expect(handleRefresh).toHaveBeenCalledTimes(1);

      const applyButtons = screen.getAllByRole('button', { name: /применить рекомендацию/i });
      expect(applyButtons.length).toBe(5);
      fireEvent.click(applyButtons[0]);
      expect(handleApplyInsight).toHaveBeenCalledWith(mockInsightsData.insights[0]);

      // Re-render with applying state
      rerender(
        <InsightsTab
          insightsData={mockInsightsData}
          loadingInsights={false}
          applyingInsightId="ins-1"
          onRefresh={handleRefresh}
          onApplyInsight={handleApplyInsight}
        />,
      );

      expect(screen.getByText('Применение...')).toBeInTheDocument();
    });
  });

  describe('BillingTab', () => {
    const mockSubscription: UserSubscriptionData = {
      id: 'sub-1',
      user_id: 'user-1',
      tenant_id: 'tenant-1',
      plan_id: 'pro',
      status: 'active',
      auto_renew: true,
      price_usd: 49.99,
      current_period_start: 1700000000000,
      current_period_end: 1702592000000,
      next_billing_time: 1702592000000,
      cancel_at_period_end: false,
      card: {
        id: 'card-1',
        card_pan_masked: '**** 4242',
        card_type: 'visa',
        card_expiry: '12/28',
      },
    };

    const mockSavedCards: SavedPaymentMethodItem[] = [
      {
        id: 'card-1',
        card_pan_masked: '**** 4242',
        card_expiry: '12/28',
        card_type: 'visa',
        is_default: true,
        create_time: 1700000000000,
      },
      {
        id: 'card-2',
        card_pan_masked: '**** 8888',
        card_expiry: '06/27',
        card_type: 'mastercard',
        is_default: false,
        create_time: 1701000000000,
      },
    ];

    const mockTransactions: AdTransactionItem[] = [
      {
        id: 'tx-1',
        type: 'deposit',
        description: 'Пополнение баланса картой',
        amount: 100.0,
        reference_id: 'ref-1',
        created_at: 1700000000000,
      },
      {
        id: 'tx-2',
        type: 'spend',
        description: 'Списание за клики кампании "AI Promo"',
        amount: -25.5,
        reference_id: 'ref-2',
        created_at: 1701000000000,
      },
    ];

    it('renders empty / free state when subscription is null and transactions are empty', () => {
      render(
        <BillingTab
          subscription={null}
          loadingSubscriptionAction={false}
          savedCards={[]}
          balance={0}
          currency="USD"
          transactions={[]}
          onToggleAutoRenew={jest.fn()}
          onOpenCardsModal={jest.fn()}
          onOpenTopUpModal={jest.fn()}
          onExportTransactions={jest.fn()}
        />,
      );

      expect(screen.getByText('Тариф и Автопродление')).toBeInTheDocument();
      expect(screen.getByText('FREE')).toBeInTheDocument();
      expect(screen.getByText('$0.00 / мес')).toBeInTheDocument();
      expect(screen.getByText('Базовый (Free)')).toBeInTheDocument();
      expect(screen.getByText('⏸️ Отключено')).toBeInTheDocument();
      expect(screen.getByText('No transactions recorded yet.')).toBeInTheDocument();
      expect(screen.getByText('Сохранённые карты (0)')).toBeInTheDocument();
    });

    it('renders active pro subscription with price, cards count, balance, and transaction history', () => {
      render(
        <BillingTab
          subscription={mockSubscription}
          loadingSubscriptionAction={false}
          savedCards={mockSavedCards}
          balance={250.75}
          currency="USD"
          transactions={mockTransactions}
          onToggleAutoRenew={jest.fn()}
          onOpenCardsModal={jest.fn()}
          onOpenTopUpModal={jest.fn()}
          onExportTransactions={jest.fn()}
        />,
      );

      expect(screen.getByText('PRO')).toBeInTheDocument();
      expect(screen.getByText('$49.99 / мес')).toBeInTheDocument();
      expect(screen.getByText('Активна')).toBeInTheDocument();
      expect(screen.getByText('🟢 Включено (каждые 30 дн.)')).toBeInTheDocument();
      expect(screen.getByText('**** 4242')).toBeInTheDocument();
      expect(screen.getByText('Сохранённые карты (2)')).toBeInTheDocument();

      // Wallet
      expect(screen.getByText('$250.75 USD')).toBeInTheDocument();

      // Transactions
      expect(screen.getByText('deposit')).toBeInTheDocument();
      expect(screen.getByText('Пополнение баланса картой')).toBeInTheDocument();
      expect(screen.getByText('+$100.00')).toBeInTheDocument();

      expect(screen.getByText('spend')).toBeInTheDocument();
      expect(screen.getByText('-$25.50')).toBeInTheDocument();
    });

    it('wires action buttons properly (toggle auto-renew, open modals, export)', () => {
      const handleToggleAutoRenew = jest.fn();
      const handleOpenCards = jest.fn();
      const handleOpenTopUp = jest.fn();
      const handleExport = jest.fn();

      const { rerender } = render(
        <BillingTab
          subscription={mockSubscription}
          loadingSubscriptionAction={false}
          savedCards={mockSavedCards}
          balance={250.75}
          currency="USD"
          transactions={mockTransactions}
          onToggleAutoRenew={handleToggleAutoRenew}
          onOpenCardsModal={handleOpenCards}
          onOpenTopUpModal={handleOpenTopUp}
          onExportTransactions={handleExport}
        />,
      );

      // Auto-renew button
      const autoRenewBtn = screen.getByRole('button', { name: /отключить автопродление/i });
      fireEvent.click(autoRenewBtn);
      expect(handleToggleAutoRenew).toHaveBeenCalledTimes(1);

      // Open cards modal
      fireEvent.click(screen.getByRole('button', { name: /управление сохранёнными картами/i }));
      expect(handleOpenCards).toHaveBeenCalledTimes(1);

      // Open topup modal
      fireEvent.click(screen.getByRole('button', { name: /пополнить баланс кабинета/i }));
      expect(handleOpenTopUp).toHaveBeenCalledTimes(1);

      // Export CSV
      fireEvent.click(screen.getByRole('button', { name: /экспорт транзакций в csv/i }));
      expect(handleExport).toHaveBeenCalledTimes(1);

      // Re-render with loading state on auto-renew
      rerender(
        <BillingTab
          subscription={mockSubscription}
          loadingSubscriptionAction={true}
          savedCards={mockSavedCards}
          balance={250.75}
          currency="USD"
          transactions={mockTransactions}
          onToggleAutoRenew={handleToggleAutoRenew}
          onOpenCardsModal={handleOpenCards}
          onOpenTopUpModal={handleOpenTopUp}
          onExportTransactions={handleExport}
        />,
      );

      expect(screen.getByRole('button', { name: /отключить автопродление/i })).toBeDisabled();
    });

    it('handles defensive edge cases (past_due status, null/undefined numeric values)', () => {
      const corruptSubscription: any = {
        id: 'sub-corrupt',
        plan_id: undefined,
        status: 'past_due',
        auto_renew: false,
        price_usd: undefined,
      };

      const corruptTransactions: any = [
        {
          id: 'tx-corrupt',
          type: 'adjustment',
          description: 'Corrupt row',
          amount: undefined,
          created_at: 1700000000000,
        },
      ];

      expect(() =>
        render(
          <BillingTab
            subscription={corruptSubscription}
            loadingSubscriptionAction={false}
            savedCards={null as any}
            balance={undefined as any}
            currency="USD"
            transactions={corruptTransactions}
            onToggleAutoRenew={jest.fn()}
            onOpenCardsModal={jest.fn()}
            onOpenTopUpModal={jest.fn()}
            onExportTransactions={jest.fn()}
          />,
        ),
      ).not.toThrow();

      expect(screen.getByText('Ошибка оплаты')).toBeInTheDocument();
      expect(screen.getByText('+$0.00')).toBeInTheDocument();
      expect(screen.getByText('$0.00 USD')).toBeInTheDocument();
      expect(screen.getByText('Сохранённые карты (0)')).toBeInTheDocument();
    });
  });

  describe('SettingsTab', () => {
    const mockAdvSettings: AdvertiserSettingsData = {
      advertiser_id: 'adv-1',
      company_name: 'Acme AI Labs',
      contact_email: 'ads@acme.ai',
      website_url: 'https://acme.ai',
      currency: 'USD',
      pixel_id: 'px_live_abc123',
      balance: 100,
      status: 'active',
      language: 'ru',
      default_regions: ['UZ', 'US'],
      default_models: ['gpt-4o', 'claude-3-5-sonnet'],
      daily_spend_ceiling: 75,
      default_frequency_cap: 4,
      auto_pause_low_ctr: true,
      low_ctr_threshold: 0.8,
      timezone: 'Asia/Tashkent',
    };

    const mockNotifSettings: NotificationSettingsData = {
      email_alerts_enabled: true,
      email_target: 'alerts@acme.ai',
      telegram_alerts_enabled: true,
      telegram_chat_id: '123456789',
      webhook_url: 'https://acme.ai/webhook',
      webhook_secret: 'secret123',
      notify_low_balance: true,
      low_balance_threshold: 10,
      notify_daily_budget_reached: true,
      notify_moderation_status: true,
      notify_conversion_milestone: true,
    };

    it('renders profile, targeting, safety, and notification settings cards', () => {
      render(
        <SettingsTab
          advSettings={mockAdvSettings}
          onUpdateAdvSettings={jest.fn()}
          notifSettings={mockNotifSettings}
          onUpdateNotifSettings={jest.fn()}
          isSavingAdvSettings={false}
          onSaveAdvSettings={jest.fn()}
          copiedPixelSuccess={false}
          onCopyPixelId={jest.fn()}
          currentLang="ru"
          onLanguageChange={jest.fn()}
          testingNotifChannel={null}
          onSendTestNotification={jest.fn()}
        />,
      );

      // Profile
      expect(screen.getByDisplayValue('Acme AI Labs')).toBeInTheDocument();
      expect(screen.getByDisplayValue('ads@acme.ai')).toBeInTheDocument();
      expect(screen.getByDisplayValue('https://acme.ai')).toBeInTheDocument();
      expect(screen.getByDisplayValue('px_live_abc123')).toBeInTheDocument();

      // Targeting
      expect(screen.getByText('🇺🇿 Uzbekistan')).toBeInTheDocument();
      expect(screen.getByText('🇺🇸 United States')).toBeInTheDocument();
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
      expect(screen.getByText('Claude 3.5 Sonnet')).toBeInTheDocument();

      // Safety
      expect(screen.getByText('$75 / day')).toBeInTheDocument();
      expect(screen.getByDisplayValue('4')).toBeInTheDocument();
      expect(screen.getByDisplayValue('0.8')).toBeInTheDocument();

      // Notifications
      expect(screen.getByDisplayValue('123456789')).toBeInTheDocument();
      expect(screen.getByDisplayValue('alerts@acme.ai')).toBeInTheDocument();
      expect(screen.getByDisplayValue('https://acme.ai/webhook')).toBeInTheDocument();
    });

    it('wires action buttons and updates properly (save, copy pixel, test notif, region/model toggle)', () => {
      const handleSave = jest.fn();
      const handleCopyPixel = jest.fn();
      const handleSendTest = jest.fn();
      const handleUpdateAdvSettings = jest.fn();

      const { rerender } = render(
        <SettingsTab
          advSettings={mockAdvSettings}
          onUpdateAdvSettings={handleUpdateAdvSettings}
          notifSettings={mockNotifSettings}
          onUpdateNotifSettings={jest.fn()}
          isSavingAdvSettings={false}
          onSaveAdvSettings={handleSave}
          copiedPixelSuccess={false}
          onCopyPixelId={handleCopyPixel}
          currentLang="ru"
          onLanguageChange={jest.fn()}
          testingNotifChannel={null}
          onSendTestNotification={handleSendTest}
        />,
      );

      // Save button (header and bottom)
      const saveButtons = screen.getAllByRole('button', { name: /сохранить настройки/i });
      expect(saveButtons.length).toBeGreaterThan(0);
      fireEvent.click(saveButtons[0]);
      expect(handleSave).toHaveBeenCalledTimes(1);

      // Copy pixel
      const copyBtn = screen.getByRole('button', { name: /копировать/i });
      fireEvent.click(copyBtn);
      expect(handleCopyPixel).toHaveBeenCalledTimes(1);

      // Region toggle fallback: click unselected region RU
      const ruRegionBtn = screen.getByText('🇷🇺 Russia');
      fireEvent.click(ruRegionBtn);
      expect(handleUpdateAdvSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          default_regions: ['UZ', 'US', 'RU'],
        }),
      );

      // Model toggle fallback: click unselected model DeepSeek
      const deepseekBtn = screen.getByText('DeepSeek V3');
      fireEvent.click(deepseekBtn);
      expect(handleUpdateAdvSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          default_models: ['gpt-4o', 'claude-3-5-sonnet', 'deepseek-v3'],
        }),
      );

      // Send test alert
      const testAlertBtn = screen.getByRole('button', { name: /отправить тестовое уведомление/i });
      fireEvent.click(testAlertBtn);
      expect(handleSendTest).toHaveBeenCalledWith('all');

      // Re-render with saving state and explicit onToggle callbacks
      const handleToggleRegion = jest.fn();
      const handleToggleModel = jest.fn();
      rerender(
        <SettingsTab
          advSettings={mockAdvSettings}
          onUpdateAdvSettings={handleUpdateAdvSettings}
          notifSettings={mockNotifSettings}
          onUpdateNotifSettings={jest.fn()}
          isSavingAdvSettings={true}
          onSaveAdvSettings={handleSave}
          copiedPixelSuccess={true}
          onCopyPixelId={handleCopyPixel}
          onToggleDefaultRegion={handleToggleRegion}
          onToggleDefaultModel={handleToggleModel}
          currentLang="ru"
          onLanguageChange={jest.fn()}
          testingNotifChannel={null}
          onSendTestNotification={handleSendTest}
        />,
      );

      expect(screen.getAllByRole('button', { name: /сохранение\.\.\./i })[0]).toBeDisabled();

      // Explicit onToggle props delegation
      fireEvent.click(screen.getByText('🇺🇸 United States'));
      expect(handleToggleRegion).toHaveBeenCalledWith('US');

      fireEvent.click(screen.getByText('GPT-4o'));
      expect(handleToggleModel).toHaveBeenCalledWith('gpt-4o');
    });

    it('handles notification alert toggles and verifies 1:1 legacy webhook clear behavior', () => {
      const handleUpdateNotifSettings = jest.fn();

      const { rerender } = render(
        <SettingsTab
          advSettings={mockAdvSettings}
          onUpdateAdvSettings={jest.fn()}
          notifSettings={mockNotifSettings}
          onUpdateNotifSettings={handleUpdateNotifSettings}
          isSavingAdvSettings={false}
          onSaveAdvSettings={jest.fn()}
          copiedPixelSuccess={false}
          onCopyPixelId={jest.fn()}
          currentLang="ru"
          onLanguageChange={jest.fn()}
          testingNotifChannel={null}
          onSendTestNotification={jest.fn()}
        />,
      );

      // Telegram alert toggle
      const tgCheckbox = screen.getByRole('checkbox', { name: /telegram/i });
      expect(tgCheckbox).toBeChecked();
      fireEvent.click(tgCheckbox);
      expect(handleUpdateNotifSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          telegram_alerts_enabled: false,
        }),
      );

      // Email alert toggle
      const emailCheckbox = screen.getByRole('checkbox', { name: /email/i });
      expect(emailCheckbox).toBeChecked();
      fireEvent.click(emailCheckbox);
      expect(handleUpdateNotifSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          email_alerts_enabled: false,
        }),
      );

      // Webhook alert toggle (unchecking clears webhook_url - legacy behavior)
      const webhookCheckbox = screen.getByRole('checkbox', { name: /webhook/i });
      expect(webhookCheckbox).toBeChecked();
      fireEvent.click(webhookCheckbox);
      expect(handleUpdateNotifSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          webhook_url: '',
        }),
      );

      // When webhook_url is empty, checking does nothing (verified 1:1 legacy behavior)
      handleUpdateNotifSettings.mockClear();
      rerender(
        <SettingsTab
          advSettings={mockAdvSettings}
          onUpdateAdvSettings={jest.fn()}
          notifSettings={{ ...mockNotifSettings, webhook_url: '' }}
          onUpdateNotifSettings={handleUpdateNotifSettings}
          isSavingAdvSettings={false}
          onSaveAdvSettings={jest.fn()}
          copiedPixelSuccess={false}
          onCopyPixelId={jest.fn()}
          currentLang="ru"
          onLanguageChange={jest.fn()}
          testingNotifChannel={null}
          onSendTestNotification={jest.fn()}
        />,
      );

      const emptyWebhookCheckbox = screen.getByRole('checkbox', { name: /webhook/i });
      expect(emptyWebhookCheckbox).not.toBeChecked();
      fireEvent.click(emptyWebhookCheckbox);
      expect(handleUpdateNotifSettings).not.toHaveBeenCalled();
    });

    it('renders without throwing when advSettings or notifSettings fields are null or undefined', () => {
      const corruptAdvSettings: any = {
        company_name: '',
        contact_email: '',
        website_url: '',
        currency: undefined,
        pixel_id: null,
        language: undefined,
        default_regions: null,
        default_models: undefined,
        daily_spend_ceiling: undefined,
        default_frequency_cap: null,
        auto_pause_low_ctr: false,
        low_ctr_threshold: undefined,
      };

      expect(() =>
        render(
          <SettingsTab
            advSettings={corruptAdvSettings}
            onUpdateAdvSettings={jest.fn()}
            notifSettings={null}
            onUpdateNotifSettings={jest.fn()}
            isSavingAdvSettings={false}
            onSaveAdvSettings={jest.fn()}
            copiedPixelSuccess={false}
            onCopyPixelId={jest.fn()}
            currentLang="ru"
            onLanguageChange={jest.fn()}
            testingNotifChannel={null}
            onSendTestNotification={jest.fn()}
          />,
        ),
      ).not.toThrow();

      expect(screen.getByDisplayValue('px_swipies_live')).toBeInTheDocument();
      expect(screen.getByText('$50 / day')).toBeInTheDocument();
    });
  });

  describe('AttributionTab', () => {
    const mockMtaSummary: AttributionSummaryResponse = {
      model_selected: 'position_based',
      days: 30,
      total_conversions: 142,
      total_revenue: 12540.5,
      avg_touchpoints_per_conversion: 3.4,
      avg_journey_duration_hours: 18.5,
      campaigns: [
        {
          campaign_id: 'cmp-1',
          campaign_name: 'AI CRM Enterprise Search',
          product_name: 'CRM Copilot',
          total_spend: 3400.0,
          first_touch_count: 50,
          last_touch_count: 45,
          assisted_count: 32,
          credited_conversions: 52.4,
          credited_revenue: 5800.0,
          effective_cpa: 64.88,
          roas: 1.71,
        },
      ],
    };

    const mockFunnelData: FunnelAnalyticsResponse = {
      days: 30,
      overall_funnel_conversion_rate: 4.8,
      stages: [
        { stage_id: 'stg-1', name: 'AI Recommendation', count: 10000, conversion_from_prev: 100, dropoff_rate: 0 },
        { stage_id: 'stg-2', name: 'Product Click', count: 2500, conversion_from_prev: 25.0, dropoff_rate: 75.0 },
        { stage_id: 'stg-3', name: 'Target Conversion', count: 480, conversion_from_prev: 19.2, dropoff_rate: 80.8 },
      ],
    };

    const mockMtaPaths: ConversionJourneyPath[] = [
      {
        id: 'pth-1',
        visitor_id: 'v_user_998877665544',
        conversion_type: 'subscription_purchase',
        conversion_value: 299.0,
        total_touchpoints: 2,
        journey_duration_hours: 4.2,
        first_touch: 'Smart Search discovery',
        last_touch: 'AI Retargeting chat',
        create_time: 1711500000000,
        path_steps: [
          { seq: 1, campaign_name: 'Smart Search discovery', type: 'click', channel: 'search', device: 'desktop' },
          { seq: 2, campaign_name: 'AI Retargeting chat', type: 'click', channel: 'chat', device: 'mobile' },
        ],
      },
    ];

    it('renders toolbar, model callout, KPI cards, funnel stages, campaign credits table, and journey paths', () => {
      render(
        <AttributionTab
          mtaModel="position_based"
          mtaDays={30}
          mtaSummary={mockMtaSummary}
          mtaPaths={mockMtaPaths}
          funnelData={mockFunnelData}
          loadingMta={false}
          loadingFunnel={false}
          onMtaModelChange={jest.fn()}
          onMtaDaysChange={jest.fn()}
          onRefresh={jest.fn()}
        />,
      );

      // Header & callout
      expect(screen.getByText('Мультитач Аттрибуция & Карта Пути Клиента (MTA)')).toBeInTheDocument();
      expect(screen.getByText('U-Shaped / Position-Based модель:')).toBeInTheDocument();

      // KPI cards
      expect(screen.getByText('142')).toBeInTheDocument();
      expect(screen.getByText('$12540.50')).toBeInTheDocument();
      expect(screen.getByText('3.4')).toBeInTheDocument();
      expect(screen.getByText('18.5 ч')).toBeInTheDocument();

      // Funnel
      expect(screen.getByText('Общая конверсия воронки: 4.8%')).toBeInTheDocument();
      expect(screen.getByText('AI Recommendation')).toBeInTheDocument();
      expect(screen.getByText('Product Click')).toBeInTheDocument();
      expect(screen.getByText('Target Conversion')).toBeInTheDocument();

      // Campaign table
      expect(screen.getByText('AI CRM Enterprise Search')).toBeInTheDocument();
      expect(screen.getByText('CRM Copilot')).toBeInTheDocument();
      expect(screen.getByText('1.71x')).toBeInTheDocument();

      // Journey path
      expect(screen.getByText(/v_user_99887766/i)).toBeInTheDocument();
      expect(screen.getByText(/Smart Search discovery/i)).toBeInTheDocument();
      expect(screen.getByText(/AI Retargeting chat/i)).toBeInTheDocument();
    });

    it('wires model selector, days filter, and refresh button properly', () => {
      const handleModelChange = jest.fn();
      const handleDaysChange = jest.fn();
      const handleRefresh = jest.fn();

      render(
        <AttributionTab
          mtaModel="position_based"
          mtaDays={30}
          mtaSummary={mockMtaSummary}
          mtaPaths={mockMtaPaths}
          funnelData={mockFunnelData}
          loadingMta={false}
          loadingFunnel={false}
          onMtaModelChange={handleModelChange}
          onMtaDaysChange={handleDaysChange}
          onRefresh={handleRefresh}
        />,
      );

      // Click model button
      fireEvent.click(screen.getByRole('button', { name: 'First Touch' }));
      expect(handleModelChange).toHaveBeenCalledWith('first_touch');

      // Click days button
      fireEvent.click(screen.getByRole('button', { name: '14 дней' }));
      expect(handleDaysChange).toHaveBeenCalledWith(14);

      // Click refresh button
      fireEvent.click(screen.getByRole('button', { name: /обновить аналитику/i }));
      expect(handleRefresh).toHaveBeenCalledTimes(1);
    });

    it('handles data consistency and prevents displaying stale metrics under newly selected model during network lag', () => {
      const { rerender } = render(
        <AttributionTab
          mtaModel="position_based"
          mtaDays={30}
          mtaSummary={mockMtaSummary}
          mtaPaths={mockMtaPaths}
          funnelData={mockFunnelData}
          loadingMta={false}
          loadingFunnel={false}
          onMtaModelChange={jest.fn()}
          onMtaDaysChange={jest.fn()}
          onRefresh={jest.fn()}
        />,
      );

      expect(screen.getByText('По модели position based')).toBeInTheDocument();
      expect(screen.getByText('AI CRM Enterprise Search')).toBeInTheDocument();

      // User switches model to 'first_touch', but data hasn't arrived yet (loadingMta: true, mtaSummary still has model_selected: 'position_based')
      rerender(
        <AttributionTab
          mtaModel="first_touch"
          mtaDays={30}
          mtaSummary={mockMtaSummary}
          mtaPaths={mockMtaPaths}
          funnelData={mockFunnelData}
          loadingMta={true}
          loadingFunnel={false}
          onMtaModelChange={jest.fn()}
          onMtaDaysChange={jest.fn()}
          onRefresh={jest.fn()}
        />,
      );

      // Verify that stale revenue is NOT attributed to first touch without qualification
      expect(screen.getByText('По модели position based (обновление...)')).toBeInTheDocument();

      // Verify that campaign table immediately switches to loader instead of displaying old weights under new model
      expect(screen.getByText(/Расчет мультитач весов \(first touch\)\.\.\./i)).toBeInTheDocument();
      expect(screen.queryByText('AI CRM Enterprise Search')).not.toBeInTheDocument();

      // When fresh data arrives with model_selected: 'first_touch'
      const freshMtaSummary: AttributionSummaryResponse = {
        ...mockMtaSummary,
        model_selected: 'first_touch',
        total_revenue: 15200.0,
      };

      rerender(
        <AttributionTab
          mtaModel="first_touch"
          mtaDays={30}
          mtaSummary={freshMtaSummary}
          mtaPaths={mockMtaPaths}
          funnelData={mockFunnelData}
          loadingMta={false}
          loadingFunnel={false}
          onMtaModelChange={jest.fn()}
          onMtaDaysChange={jest.fn()}
          onRefresh={jest.fn()}
        />,
      );

      expect(screen.getByText('По модели first touch')).toBeInTheDocument();
      expect(screen.getByText('$15200.00')).toBeInTheDocument();
      expect(screen.getByText('AI CRM Enterprise Search')).toBeInTheDocument();
    });

    it('renders gracefully when mtaSummary, mtaPaths, or funnelData are null, empty, or have corrupt numeric fields', () => {
      const corruptSummary: any = {
        model_selected: undefined,
        days: null,
        total_conversions: undefined,
        total_revenue: null,
        avg_touchpoints_per_conversion: undefined,
        avg_journey_duration_hours: null,
        campaigns: null,
      };

      expect(() =>
        render(
          <AttributionTab
            mtaModel="position_based"
            mtaDays={30}
            mtaSummary={corruptSummary}
            mtaPaths={[]}
            funnelData={null}
            loadingMta={false}
            loadingFunnel={false}
            onMtaModelChange={jest.fn()}
            onMtaDaysChange={jest.fn()}
            onRefresh={jest.fn()}
          />,
        ),
      ).not.toThrow();

      // Fallbacks
      expect(screen.getByText('$0.00')).toBeInTheDocument();
      expect(screen.getByText('1')).toBeInTheDocument(); // avg_touchpoints fallback
      expect(screen.getByText('0 ч')).toBeInTheDocument(); // avg_journey fallback
      expect(screen.getByText('Недостаточно данных для построения воронки')).toBeInTheDocument();
      expect(screen.getByText('Кампании пока не зафиксировали конверсионных путей')).toBeInTheDocument();
      expect(screen.getByText('Нет зафиксированных мультикасательных путей')).toBeInTheDocument();
    });
  });

  describe('AnalyticsTab', () => {
    const mockTimelineData: TimelineAnalyticsData = {
      days: 14,
      total_impressions: 15420,
      total_clicks: 1230,
      total_spend: 450.75,
      ctr: 7.98,
      timeline: [
        { date: '2026-09-01', impressions: 1000, clicks: 80, ctr: 8.0, spend: 30.0 },
        { date: '2026-09-02', impressions: 1200, clicks: 95, ctr: 7.9, spend: 35.5 },
      ],
      languages: {
        ru: 800,
        uz: 350,
        en: 150,
        other: 50,
      },
      models: {
        'gpt-4o': 600,
        deepseek: 450,
        claude: 250,
        other: 50,
      },
      devices: {
        desktop: 700,
        mobile: 600,
        tablet: 50,
      },
      regions: {
        tashkent: 800,
        samarkand: 250,
        fergana: 150,
        bukhara: 80,
        andijan: 50,
        namangan: 10,
        other: 10,
      },
    };

    it('renders empty state when timelineData is null', () => {
      const { container } = render(
        <AnalyticsTab
          timelineData={null}
          timelineDays={14}
          loadingTimeline={false}
          onTimelineDaysChange={jest.fn()}
          onRefresh={jest.fn()}
          onExportCsv={jest.fn()}
          onExportReport={jest.fn()}
        />,
      );

      expect(screen.getByText('Интерактивная статистика эффективности')).toBeInTheDocument();
      expect(screen.getByText('Динамика вовлеченности аудитории за последние 14 дней')).toBeInTheDocument();
      expect(screen.getByText('За выбранный период данных нет')).toBeInTheDocument();
      expect(container.querySelector('.recharts-surface')).not.toBeInTheDocument();
      expect(screen.getByText('$0.00')).toBeInTheDocument();
      expect(screen.getByText('0%')).toBeInTheDocument();
    });

    it('renders populated KPI metrics, breakdown cards, and timeline points', () => {
      const { container } = render(
        <AnalyticsTab
          timelineData={mockTimelineData}
          timelineDays={14}
          loadingTimeline={false}
          onTimelineDaysChange={jest.fn()}
          onRefresh={jest.fn()}
          onExportCsv={jest.fn()}
          onExportReport={jest.fn()}
        />,
      );

      // Verify Recharts chart renders in JSDOM via ResponsiveContainer + surface + legend
      expect(container.querySelector('.recharts-responsive-container')).toBeInTheDocument();
      expect(container.querySelector('.recharts-surface')).toBeInTheDocument();
      expect(screen.getByText('Показы (Impressions)')).toBeInTheDocument();
      expect(screen.getByText('Клики (Clicks)')).toBeInTheDocument();

      // KPI metrics
      expect(screen.getByText((15420).toLocaleString())).toBeInTheDocument();
      expect(screen.getByText((1230).toLocaleString())).toBeInTheDocument();
      expect(screen.getByText('7.98%')).toBeInTheDocument();
      expect(screen.getByText('$450.75')).toBeInTheDocument();

      // Breakdown headers
      expect(screen.getByText('Языки запросов пользователей')).toBeInTheDocument();
      expect(screen.getByText('Используемые модели LLM')).toBeInTheDocument();
      expect(screen.getByText('Устройства и платформы')).toBeInTheDocument();
      expect(screen.getByText('Регионы Узбекистана')).toBeInTheDocument();

      // Breakdown content items
      expect(screen.getByText('🇷🇺 Русский')).toBeInTheDocument();
      expect(screen.getByText('🇺🇿 Oʻzbekcha')).toBeInTheDocument();
      expect(screen.getByText('🤖 GPT-4o / Mini')).toBeInTheDocument();
      expect(screen.getByText('⚡ DeepSeek R1 / V3')).toBeInTheDocument();
      expect(screen.getByText('🖥️ Desktop (ПК)')).toBeInTheDocument();
      expect(screen.getByText('📱 Mobile (Смартфоны)')).toBeInTheDocument();
      expect(screen.getByText('📍 Ташкент')).toBeInTheDocument();
      expect(screen.getByText('📍 Самарканд')).toBeInTheDocument();
      // Verifies that namangan (10) + other (10) are aggregated into "🌐 Другие регионы" = 20
      expect(screen.getByText(/20 \(1%\)/)).toBeInTheDocument();
    });

    it('wires date range selector, refresh, and export callbacks correctly', () => {
      const onTimelineDaysChange = jest.fn();
      const onRefresh = jest.fn();
      const onExportCsv = jest.fn();
      const onExportReport = jest.fn();

      render(
        <AnalyticsTab
          timelineData={mockTimelineData}
          timelineDays={14}
          loadingTimeline={false}
          onTimelineDaysChange={onTimelineDaysChange}
          onRefresh={onRefresh}
          onExportCsv={onExportCsv}
          onExportReport={onExportReport}
        />,
      );

      // Click 7 days filter
      fireEvent.click(screen.getByRole('button', { name: '7 дней' }));
      expect(onTimelineDaysChange).toHaveBeenCalledWith(7);

      // Click 30 days filter
      fireEvent.click(screen.getByRole('button', { name: '30 дней' }));
      expect(onTimelineDaysChange).toHaveBeenCalledWith(30);

      // Click refresh
      fireEvent.click(screen.getByRole('button', { name: 'Обновить данные' }));
      expect(onRefresh).toHaveBeenCalled();

      // Click CSV export
      fireEvent.click(screen.getByRole('button', { name: 'Экспорт динамики в CSV' }));
      expect(onExportCsv).toHaveBeenCalledWith(14);

      // Click PDF report export
      fireEvent.click(screen.getByRole('button', { name: 'Открыть PDF / Печатную версию отчета' }));
      expect(onExportReport).toHaveBeenCalledWith(14);
    });

    it('applies stale indicator during loading or mismatched timelineDays (ARCH-Race-Conditions guard)', () => {
      const { rerender, container } = render(
        <AnalyticsTab
          timelineData={mockTimelineData}
          timelineDays={14}
          loadingTimeline={false}
          onTimelineDaysChange={jest.fn()}
          onRefresh={jest.fn()}
          onExportCsv={jest.fn()}
          onExportReport={jest.fn()}
        />,
      );

      // Initially matched and not loading -> not stale (no opacity-70 on the metrics grid)
      const metricsGrid = container.querySelector('.grid.gap-4.md\\:grid-cols-4');
      expect(metricsGrid).not.toHaveClass('opacity-70');

      // User changed period to 30 days, data still has days = 14 and loading = true
      rerender(
        <AnalyticsTab
          timelineData={mockTimelineData} // days is 14
          timelineDays={30}
          loadingTimeline={true}
          onTimelineDaysChange={jest.fn()}
          onRefresh={jest.fn()}
          onExportCsv={jest.fn()}
          onExportReport={jest.fn()}
        />,
      );

      expect(metricsGrid).toHaveClass('opacity-70');
    });

    it('safely handles corrupt / unexpected timeline structures without throwing', () => {
      const corruptData = {
        days: 7,
        total_impressions: null as any,
        total_clicks: undefined as any,
        total_spend: NaN,
        ctr: null as any,
        timeline: 'not-an-array' as any,
        languages: null as any,
        models: undefined as any,
        devices: 'invalid' as any,
        regions: null as any,
      };

      expect(() =>
        render(
          <AnalyticsTab
            timelineData={corruptData}
            timelineDays={7}
            loadingTimeline={false}
            onTimelineDaysChange={jest.fn()}
            onRefresh={jest.fn()}
            onExportCsv={jest.fn()}
            onExportReport={jest.fn()}
          />,
        ),
      ).not.toThrow();

      expect(screen.getByText('За выбранный период данных нет')).toBeInTheDocument();
      expect(screen.getByText('$0.00')).toBeInTheDocument();
      expect(screen.getByText('0%')).toBeInTheDocument();
    });
  });

  describe('format-utils', () => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { toFixedSafe, toLocaleSafe } = require('../format-utils');

    it('toFixedSafe safely handles undefined, null, NaN, strings, and numbers', () => {
      expect(toFixedSafe(undefined)).toBe('0.00');
      expect(toFixedSafe(null)).toBe('0.00');
      expect(toFixedSafe('')).toBe('0.00');
      expect(toFixedSafe(NaN)).toBe('0.00');
      expect(toFixedSafe(Infinity)).toBe('0.00');
      expect(toFixedSafe(123.456, 2)).toBe('123.46');
      expect(toFixedSafe(123.4, 2)).toBe('123.40');
      expect(toFixedSafe('42.5', 2)).toBe('42.50');
      expect(toFixedSafe(0, 0)).toBe('0');
      expect(toFixedSafe(70.2, 0)).toBe('70');
      expect(toFixedSafe(5, 4)).toBe('5.0000');
    });

    it('toLocaleSafe safely handles undefined, null, NaN, strings, and numbers', () => {
      expect(toLocaleSafe(undefined)).toBe('0');
      expect(toLocaleSafe(null)).toBe('0');
      expect(toLocaleSafe('')).toBe('0');
      expect(toLocaleSafe(NaN)).toBe('0');
      expect(toLocaleSafe(Infinity)).toBe('0');
      expect(toLocaleSafe(0)).toBe('0');
      expect(toLocaleSafe(1000)).toBe((1000).toLocaleString());
      expect(toLocaleSafe('5000')).toBe((5000).toLocaleString());
    });
  });
});

