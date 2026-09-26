import { fireEvent, render, screen } from '@testing-library/react';
import { GuideTab } from '../tabs/GuideTab';
import { PublisherTab } from '../tabs/PublisherTab';
import { PlacementItem, PublisherPayoutItem, PublisherProfileData } from '@/services/ad-service';

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

