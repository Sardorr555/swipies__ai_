import { fireEvent, render, screen } from '@testing-library/react';
import { GuideTab } from '../tabs/GuideTab';
import { PublisherTab } from '../tabs/PublisherTab';
import { FraudTab } from '../tabs/FraudTab';
import { TeamTab } from '../tabs/TeamTab';
import { InsightsTab } from '../tabs/InsightsTab';
import {
  AdvertiserInsightsData,
  BlacklistEntryItem,
  FraudOverviewData,
  PlacementItem,
  PublisherPayoutItem,
  PublisherProfileData,
  TeamMemberItem,
} from '@/services/ad-service';

describe('Ads Tabs Render Suite', () => {
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

