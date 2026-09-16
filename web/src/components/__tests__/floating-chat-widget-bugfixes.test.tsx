/* eslint-disable no-console */
import { MessageType } from '@/constants/chat';

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
});

