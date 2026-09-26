import { fireEvent, render, screen } from '@testing-library/react';
import { GuideTab } from '../tabs/GuideTab';
import { PublisherTab } from '../tabs/PublisherTab';
import { FraudTab } from '../tabs/FraudTab';
import {
  BlacklistEntryItem,
  FraudOverviewData,
  PlacementItem,
  PublisherPayoutItem,
  PublisherProfileData,
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
      recent_logs: [
        {
          id: 'log-1',
          campaign_name: 'Summer AI Promo',
          reason: 'bot_user_agent',
          ip_hash: 'abc123def4567890abcdef',
          user_agent: 'Scrapy/2.11.0',
          cost_saved: 0.55,
          create_time: 1700000000000,
        },
        {
          id: 'log-2',
          campaign_name: 'Telegram Bot Ads',
          reason: 'blacklist_ip',
          ip_hash: 'deadbeef12345678cafe',
          user_agent: 'Mozilla/5.0',
          cost_saved: 1.2,
          create_time: 1700000000000,
        },
        {
          id: 'log-3',
          campaign_name: 'Search Boost',
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
        auto_expires_at: '2026-09-25T15:00:00Z',
      },
      {
        id: 'bl-2',
        ip_address: '10.0.0.1/24',
        is_system: true,
        reason: 'Known DC datacenter range',
        auto_expires_at: null,
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

