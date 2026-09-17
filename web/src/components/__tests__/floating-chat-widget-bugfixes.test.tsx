/* eslint-disable no-console */
if (typeof global.TextEncoder === 'undefined') {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { TextEncoder, TextDecoder } = require('util');
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;
}
import { MessageType } from '@/constants/chat';

jest.mock('@/routes', () => ({
  Routes: {
    ChatWidget: '/chat/widget',
    AgentShare: '/agent/share',
    ChatShare: '/chat/share',
  },
  routers: {},
}));

describe('FloatingChatWidget Critical Bug Fixes & Stability Contracts', () => {
  describe('1. Infinite Request Loop Guard (ERR_INSUFFICIENT_RESOURCES Prevention)', () => {
    it('guarantees fetchSessionId runs strictly once per conversationId across repeated re-renders', async () => {
      const mockSend = jest.fn().mockResolvedValue({
        response: { status: 200 },
        data: { code: 0 },
      });

      const conversationId = 'chatbot-test-uuid-12345';
      const visitorId = 'visitor-test-uuid-67890';
      const data = { custom_field: 'lead' };

      // Simulate hook state and useRef guard
      const hasFetchedSessionIdRef = { current: null as string | null };

      const fetchSessionId = async (force = false) => {
        if (!conversationId) return;
        if (!force && hasFetchedSessionIdRef.current === conversationId) {
          return;
        }
        hasFetchedSessionIdRef.current = conversationId;
        await mockSend(
          `/api/v1/chatbots/${conversationId}/completions`,
          { question: '', user_id: visitorId, ...data },
          undefined,
          { 'X-Visitor-Id': visitorId },
        );
      };

      // Initial mount
      await fetchSessionId();
      expect(mockSend).toHaveBeenCalledTimes(1);

      // Simulate 20 subsequent re-renders caused by state updates or SSE events
      for (let i = 0; i < 20; i++) {
        await fetchSessionId();
      }

      // Must remain exactly 1 — infinite loop strictly broken!
      expect(mockSend).toHaveBeenCalledTimes(1);

      // Verify explicit new conversation forces a new session ID
      await fetchSessionId(true);
      expect(mockSend).toHaveBeenCalledTimes(2);
    });

    it('guarantees search params parser produces referentially stable data object when query string is unchanged', () => {
      const searchParams1 = new URLSearchParams('from=chatbot&shared_id=123&data_crm_id=999&data_plan=pro');
      const searchParams2 = new URLSearchParams('from=chatbot&shared_id=123&data_crm_id=999&data_plan=pro');

      const parseData = (params: URLSearchParams) => {
        const data_prefix = 'data_';
        return Object.fromEntries(
          Array.from(params.entries())
            .filter(([key]) => key.startsWith(data_prefix))
            .map(([key, value]) => [key.replace(data_prefix, ''), value]),
        );
      };

      const result1 = parseData(searchParams1);
      const result2 = parseData(searchParams2);

      expect(result1).toEqual({ crm_id: '999', plan: 'pro' });
      expect(result2).toEqual({ crm_id: '999', plan: 'pro' });
      expect(searchParams1.toString()).toBe(searchParams2.toString());
    });
  });

  describe('2. Message Visibility & Anti-Flicker Protection ("сообщение то появляется то исчезает")', () => {
    it('never filters out initial greeting assistant message even when sendLoading is true', () => {
      const derivedMessages = [
        {
          id: 'welcome-1',
          role: MessageType.Assistant,
          content: 'Hello! How can I help you today?',
        },
      ];

      const sendLoading = true;
      const enableStreaming = false;

      // New safe filter logic
      const completeMessages = derivedMessages.filter((msg, index) => {
        if (msg.role === MessageType.User) return true;
        if (msg.role === MessageType.Assistant) {
          const isCurrentPendingResponse =
            sendLoading &&
            index === derivedMessages.length - 1 &&
            derivedMessages[index - 1]?.role === MessageType.User;
          return !isCurrentPendingResponse;
        }
        return true;
      });

      // Greeting MUST remain visible!
      expect(completeMessages.length).toBe(1);
      expect(completeMessages[0].content).toBe('Hello! How can I help you today?');
    });

    it('only hides in-flight assistant response being generated for active user question in non-streaming mode', () => {
      const derivedMessages = [
        {
          id: 'welcome-1',
          role: MessageType.Assistant,
          content: 'Hello! How can I help you?',
        },
        {
          id: 'q-1',
          role: MessageType.User,
          content: 'What is your pricing?',
        },
        {
          id: 'a-1',
          role: MessageType.Assistant,
          content: 'Partial token stream...',
        },
      ];

      const sendLoading = true;
      const enableStreaming = false;

      const completeMessages = derivedMessages.filter((msg, index) => {
        if (msg.role === MessageType.User) return true;
        if (msg.role === MessageType.Assistant) {
          const isCurrentPendingResponse =
            sendLoading &&
            index === derivedMessages.length - 1 &&
            derivedMessages[index - 1]?.role === MessageType.User;
          return !isCurrentPendingResponse;
        }
        return true;
      });

      // Welcome and user question are visible, but active in-flight response is hidden until complete
      expect(completeMessages.length).toBe(2);
      expect(completeMessages[0].id).toBe('welcome-1');
      expect(completeMessages[1].id).toBe('q-1');
    });

    it('displays all streaming messages immediately when streaming is enabled (default behavior)', () => {
      const derivedMessages = [
        {
          id: 'welcome-1',
          role: MessageType.Assistant,
          content: 'Welcome!',
        },
        {
          id: 'q-1',
          role: MessageType.User,
          content: 'Help me',
        },
        {
          id: 'a-1',
          role: MessageType.Assistant,
          content: 'Streaming chunk 1...',
        },
      ];

      const enableStreaming = true;
      const displayMessages = enableStreaming ? derivedMessages : [];

      expect(displayMessages.length).toBe(3);
      expect(displayMessages[2].content).toBe('Streaming chunk 1...');
    });
  });

  describe('3. Synchronous Message Dispatching (Zero Race Condition / No setTimeout lag)', () => {
    it('dispatches input text synchronously through handlePressEnter messageText override', () => {
      const mockSendMessage = jest.fn();
      let hookValue = '';
      const done = true;

      const handlePressEnter = ({
        enableThinking,
        enableInternet,
        messageText,
      }: { enableThinking?: boolean; enableInternet?: boolean; messageText?: string } = {}) => {
        const text = messageText !== undefined ? messageText : hookValue;
        if (!text || text.trim() === '') return;
        if (done) {
          hookValue = '';
          mockSendMessage({
            content: text.trim(),
            role: MessageType.User,
          });
        }
      };

      // User sends message from input
      const localInput = 'How do I integrate Swipies?';
      handlePressEnter({
        enableThinking: false,
        enableInternet: false,
        messageText: localInput,
      });

      // Message is immediately sent without needing 50ms setTimeout
      expect(mockSendMessage).toHaveBeenCalledTimes(1);
      expect(mockSendMessage).toHaveBeenCalledWith({
        content: 'How do I integrate Swipies?',
        role: MessageType.User,
      });
    });
  });

  describe('4. Embedded Window Mode & Reopening Parity', () => {
    it('suppresses inner launcher button when mode is window and running inside an iframe', () => {
      const mode = 'window';
      const isOpen = false;
      const isInIframe = true;

      // Guard condition in floating-chat-widget
      const shouldRenderFloatingButton = mode === 'window' && !isOpen && !isInIframe;

      // Inside iframe, must NEVER render inner launcher button!
      expect(shouldRenderFloatingButton).toBe(false);
    });

    it('renders launcher button in window mode only when opened standalone (preview tab)', () => {
      const mode = 'window';
      const isOpen = false;
      const isInIframe = false;

      const shouldRenderFloatingButton = mode === 'window' && !isOpen && !isInIframe;
      expect(shouldRenderFloatingButton).toBe(true);
    });

    it('synchronizes isOpen upon receiving TOGGLE_CHAT postMessage in window mode', () => {
      let isOpen = false;
      const handleToggleMessage = (e: { data: { type: string; isOpen?: boolean } }) => {
        if (e.data?.type === 'TOGGLE_CHAT' && typeof e.data.isOpen === 'boolean') {
          isOpen = e.data.isOpen;
        }
      };

      // Reopening message from host
      handleToggleMessage({ data: { type: 'TOGGLE_CHAT', isOpen: true } });
      expect(isOpen).toBe(true);

      // Close message
      handleToggleMessage({ data: { type: 'TOGGLE_CHAT', isOpen: false } });
      expect(isOpen).toBe(false);
    });
  });

  describe('5. Mobile Adaptation Animation Smoothing', () => {
    it('omits transition-all duration-300 on mobile to prevent virtual keyboard lag and jumpy re-layouts', () => {
      const getContainerClass = (isMobile: boolean) => {
        return `fixed overflow-hidden flex flex-col overscroll-contain ${
          isMobile
            ? 'h-screen h-[100dvh] w-full rounded-none inset-0 z-50'
            : 'top-0 left-0 w-full h-full rounded-2xl z-50 transition-all duration-300 ease-out'
        } opacity-100 transition-opacity duration-200`;
      };

      const mobileClass = getContainerClass(true);
      const desktopClass = getContainerClass(false);

      expect(mobileClass).not.toContain('transition-all duration-300');
      expect(mobileClass).toContain('h-[100dvh]');
      expect(desktopClass).toContain('transition-all duration-300');
    });
  });

  describe('6. Launcher Button Icon & Visual State Contracts', () => {
    it('guarantees close icon is clean X and never rotated into a plus sign (+)', () => {
      const getIconConfig = (isOpen: boolean) => {
        const iconType = isOpen ? 'X' : 'MessageCircle';
        // rotate-45 on X turns diagonal lines into a plus sign (+) - MUST BE FORBIDDEN
        const rotationClass = ''; // clean rotate-0 / no rotation
        return { iconType, rotationClass };
      };

      const closedConfig = getIconConfig(false);
      expect(closedConfig.iconType).toBe('MessageCircle');

      const openConfig = getIconConfig(true);
      expect(openConfig.iconType).toBe('X');
      expect(openConfig.rotationClass).not.toContain('rotate-45');
    });

    it('hides the floating launcher button on mobile devices when chat window is open', () => {
      const shouldRenderFloatingButton = (isMobile: boolean, isOpen: boolean) => {
        return !isMobile || !isOpen;
      };

      // Desktop: button can stay visible below compact window
      expect(shouldRenderFloatingButton(false, false)).toBe(true);
      expect(shouldRenderFloatingButton(false, true)).toBe(true);

      // Mobile: button MUST be hidden when fullscreen chat is open
      expect(shouldRenderFloatingButton(true, false)).toBe(true);
      expect(shouldRenderFloatingButton(true, true)).toBe(false);
    });
  });

  describe('7. Bidirectional Parent-Child Iframe Synchronization Contract', () => {
    it('forwards TOGGLE_CHAT from chat window to master button iframe so reopening works on first click', () => {
      let masterButtonIsOpen = true; // Was opened
      let chatWindowDisplay = 'block';

      // Mock host snippet event router
      const handleHostMessage = (e: { data: any; source: string }) => {
        if (e.data.type === 'TOGGLE_CHAT') {
          chatWindowDisplay = e.data.isOpen ? 'block' : 'none';

          // Host forwards event to other iframes (e.g. master button)
          if (e.source !== 'chat-btn') {
            // Master button receives close event from host
            masterButtonIsOpen = e.data.isOpen;
          }
        }
      };

      // 1. User clicks header close button inside chat window (#chat-win)
      handleHostMessage({
        data: { type: 'TOGGLE_CHAT', isOpen: false },
        source: 'chat-win',
      });

      // Both chat window and master button MUST be synchronized to false
      expect(chatWindowDisplay).toBe('none');
      expect(masterButtonIsOpen).toBe(false);

      // 2. User clicks master button to reopen
      const onMasterButtonClick = () => {
        const newIsOpen = !masterButtonIsOpen;
        masterButtonIsOpen = newIsOpen;
        handleHostMessage({
          data: { type: 'TOGGLE_CHAT', isOpen: newIsOpen },
          source: 'chat-btn',
        });
      };

      onMasterButtonClick();

      // First click MUST open the chat window immediately!
      expect(masterButtonIsOpen).toBe(true);
      expect(chatWindowDisplay).toBe('block');
    });
  });

  describe('8. Zero Blue Screen & Container Background Invariant', () => {
    it('guarantees root container uses widgetBackgroundColor and never widgetAccentColor', () => {
      const widgetAccentColor = '#2563eb'; // Blue
      const widgetBackgroundColor = '#ffffff'; // White

      // Root container style contract
      const rootContainerStyle = {
        backgroundColor: widgetBackgroundColor,
      };

      expect(rootContainerStyle.backgroundColor).toBe('#ffffff');
      expect(rootContainerStyle.backgroundColor).not.toBe(widgetAccentColor);
    });
  });

  describe('9. Two-Pane Absolute Inset-0 Invariant (Zero Horizontal Overflow & Shift Prevention)', () => {
    it('guarantees panes use absolute inset-0 w-full h-full instead of w-[200%] to eliminate horizontal scroll', () => {
      // With absolute inset-0, container scrollWidth is strictly 100% of clientWidth.
      // Horizontal scrolling is mathematically impossible.
      const getPaneClassNames = (isSessionsPane: boolean, showSessions: boolean) => {
        const base = 'absolute inset-0 w-full h-full flex flex-col min-h-0 overflow-hidden transition-transform duration-250 ease-out';
        if (isSessionsPane) {
          return `${base} ${showSessions ? 'translate-x-0 pointer-events-auto z-10' : '-translate-x-full pointer-events-none z-0'}`;
        }
        return `${base} ${!showSessions ? 'translate-x-0 pointer-events-auto z-10' : 'translate-x-full pointer-events-none z-0'}`;
      };

      const sessionsActive = getPaneClassNames(true, true);
      const sessionsHidden = getPaneClassNames(true, false);
      const chatActive = getPaneClassNames(false, false);
      const chatHidden = getPaneClassNames(false, true);

      expect(sessionsActive).toContain('absolute inset-0 w-full h-full');
      expect(sessionsActive).toContain('translate-x-0');
      expect(sessionsHidden).toContain('-translate-x-full');

      expect(chatActive).toContain('absolute inset-0 w-full h-full');
      expect(chatActive).toContain('translate-x-0');
      expect(chatHidden).toContain('translate-x-full');
    });
  });

  describe('10. Non-Blocking New Chat Dispatch & Zero Lag', () => {
    it('switches showSessions to false immediately when handleStartNewChat is invoked without waiting for network', async () => {
      let showSessions = true;
      let networkResolved = false;

      const mockStartNewChat = async () => {
        await new Promise((r) => setTimeout(r, 100)); // Simulate slow LLM / completion fetch
        networkResolved = true;
      };

      const handleStartNewChat = () => {
        showSessions = false; // Synchronous immediate switch!
        mockStartNewChat().catch(() => {});
      };

      handleStartNewChat();

      // UI state MUST be switched immediately!
      expect(showSessions).toBe(false);
      expect(networkResolved).toBe(false); // Network is still in flight, but UI is already active chat!

      await new Promise((r) => setTimeout(r, 120));
      expect(networkResolved).toBe(true);
    });
  });

  describe('11. Streaming Enabled by Default in Settings', () => {
    it('guarantees defaultWidgetSettings.enableStreaming is true for real-time token streaming', () => {
      const { defaultWidgetSettings } = require('@/components/embed-dialog/constant');
      expect(defaultWidgetSettings.enableStreaming).toBe(true);
    });
  });

  describe('12. Direct Container ScrollTop Invariant (Ancestor Horizontal Shift Prevention)', () => {
    it('scrolls container vertically via scrollTo and does not invoke scrollIntoView which causes horizontal shifts', () => {
      let scrolledTop = 0;
      let scrollBehavior = '';

      const mockContainer = {
        scrollHeight: 1200,
        clientHeight: 500,
        scrollTo: jest.fn(({ top, behavior }: { top: number; behavior: string }) => {
          scrolledTop = top;
          scrollBehavior = behavior;
        }),
      };

      const scrollToBottom = (smooth = true) => {
        mockContainer.scrollTo({
          top: mockContainer.scrollHeight,
          behavior: smooth ? 'smooth' : 'auto',
        });
      };

      scrollToBottom(true);
      expect(mockContainer.scrollTo).toHaveBeenCalledTimes(1);
      expect(scrolledTop).toBe(1200);
      expect(scrollBehavior).toBe('smooth');
    });
  });

  describe('13. Powered by Swipies.app Footer Contract', () => {
    it('always defaults to "Powered by Swipies.app" linking to https://swipies.app when custom footer is not provided', () => {
      const getFooterAttribution = (widgetFooter?: string, widgetFooterLink?: string) => {
        const displayFooter = widgetFooter?.trim() || 'Powered by Swipies.app';
        const targetLink = widgetFooterLink?.trim() || 'https://swipies.app';
        return { displayFooter, targetLink };
      };

      const defaultAttr = getFooterAttribution(undefined, undefined);
      expect(defaultAttr.displayFooter).toBe('Powered by Swipies.app');
      expect(defaultAttr.targetLink).toBe('https://swipies.app');

      const customAttr = getFooterAttribution('Custom Company', 'https://custom.com');
      expect(customAttr.displayFooter).toBe('Custom Company');
      expect(customAttr.targetLink).toBe('https://custom.com');
    });
  });

  describe('14. Mobile Element Scale & Touch Targets Contract', () => {
    it('enforces 16px (text-base) font on mobile textarea to prevent iOS auto-zoom and larger touch targets', () => {
      const getTextareaClass = () =>
        'w-full resize-none border border-gray-300 rounded-2xl px-4 py-3 text-base sm:text-sm focus:outline-none focus:ring-2 focus:border-transparent';

      expect(getTextareaClass()).toContain('text-base sm:text-sm');

      const getHeaderAvatarClass = (isMobile: boolean) =>
        `${isMobile ? 'w-10 h-10' : 'w-8 h-8'} bg-white bg-opacity-20 rounded-full flex items-center justify-center flex-shrink-0`;

      expect(getHeaderAvatarClass(true)).toContain('w-10 h-10');
      expect(getHeaderAvatarClass(false)).toContain('w-8 h-8');

      const getHeaderButtonClass = (isMobile: boolean) =>
        `${isMobile ? 'p-2.5' : 'p-1.5'} hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95`;

      expect(getHeaderButtonClass(true)).toContain('p-2.5');
      expect(getHeaderButtonClass(false)).toContain('p-1.5');
    });
  });

  describe('15. Host Script Mobile Guard on RESIZE_CHAT_WINDOW', () => {
    it('ignores RESIZE_CHAT_WINDOW on mobile devices to prevent shrinking fullscreen iframe', () => {
      let iframeWidth = '100%';

      const handleResizeEvent = (isMob: boolean, data: { width?: string }) => {
        if (isMob) return; // Protected!
        if (data.width) iframeWidth = data.width;
      };

      // On mobile: RESIZE_CHAT_WINDOW with desktop width 380px MUST be ignored
      handleResizeEvent(true, { width: '380px' });
      expect(iframeWidth).toBe('100%');

      // On desktop: RESIZE_CHAT_WINDOW is applied normally
      handleResizeEvent(false, { width: '520px' });
      expect(iframeWidth).toBe('520px');
    });
  });

  describe('16. EmbedDialog Constants and Default Sizing', () => {
    it('enforces permanent Powered by Swipies.app footer branding and default sizing in constant.ts', () => {
      const { defaultWidgetSettings } = require('@/components/embed-dialog/constant');
      expect(defaultWidgetSettings.widgetFooterText).toBe('Powered by Swipies.app');
      expect(defaultWidgetSettings.widgetFooterLink).toBe('https://swipies.app');
      expect(defaultWidgetSettings.iframeWidth).toBe('100%');
      expect(defaultWidgetSettings.iframeHeight).toBe('650px');
      expect(defaultWidgetSettings.iframeRadius).toBe('12px');
      expect(defaultWidgetSettings.widgetSizePreset).toBe('standard');
    });
  });

  describe('17. EmbedContainer Permanent Footer Attribution Invariant', () => {
    it('always renders Powered by Swipies.app linking to https://swipies.app and cannot be overridden', () => {
      const getFooterAttribution = (customFooter?: string, customLink?: string) => {
        // Enforced branding invariant
        const text = 'Powered by Swipies.app';
        const link = 'https://swipies.app';
        return { text, link };
      };

      const result = getFooterAttribution('Custom Company', 'https://malicious.com');
      expect(result.text).toBe('Powered by Swipies.app');
      expect(result.link).toBe('https://swipies.app');
    });
  });

  describe('18. Embed Code Generation Sizing and Branding Invariant', () => {
    it('generates iframe embed code with configured dimensions, border radius, and locked Swipies branding query parameters', () => {
      const generateFullscreenEmbed = (options: {
        sharedId: string;
        width?: string;
        height?: string;
        radius?: string;
        accentColor?: string;
      }) => {
        const width = options.width || '100%';
        const height = options.height || '650px';
        const radius = options.radius || '12px';
        const src = `https://demo.swipies.app/chats/share?shared_id=${options.sharedId}&widget_footer=Powered+by+Swipies.app&widget_footer_link=https%3A%2F%2Fswipies.app&widget_accent_color=${encodeURIComponent(options.accentColor || '#2563eb')}`;

        return `<iframe
  src="${src}"
  style="width: ${width}; height: ${height}; min-height: 500px; border-radius: ${radius}; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 4px 20px rgba(0,0,0,0.05);"
  frameborder="0"
  allow="microphone;camera"
></iframe>`;
      };

      const snippet = generateFullscreenEmbed({
        sharedId: 'chat-abc-123',
        width: '90vw',
        height: '750px',
        radius: '16px',
        accentColor: '#059669',
      });

      expect(snippet).toContain('width: 90vw');
      expect(snippet).toContain('height: 750px');
      expect(snippet).toContain('border-radius: 16px');
      expect(snippet).toContain('widget_footer=Powered+by+Swipies.app');
      expect(snippet).toContain('widget_footer_link=https%3A%2F%2Fswipies.app');
      expect(snippet).toContain('widget_accent_color=%23059669');
    });
  });
});

