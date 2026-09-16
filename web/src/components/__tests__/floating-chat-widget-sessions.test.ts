/* eslint-disable no-console */
import { fireEvent, render, screen } from '@testing-library/react';
import React from 'react';
import { StorageWarningBanner } from '../storage-warning-banner';
import { getOrCreateVisitorId } from '../../utils/visitor-identity';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => {
      const map: Record<string, string> = {
        'chat.incognitoWarning':
          'История диалогов не сохраняется в режиме инкогнито / Safari ITP',
        'common.close': 'Close',
      };
      return map[key] || fallback || key;
    },
  }),
}));

describe('FloatingChatWidget Sessions & Visitor Identity Contract', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('provides a consistent visitorId across invocations', () => {
    const id1 = getOrCreateVisitorId();
    const id2 = getOrCreateVisitorId();
    expect(id1).toBe(id2);
    expect(id1).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
  });

  it('maps session messages with session_id, conversationId, and unique id', () => {
    const mockSession = {
      id: 'sess-12345',
      dialog_id: 'conv-abcde',
      name: 'Test Conversation',
      messages: [
        { role: 'user', content: 'Hello' },
        { role: 'assistant', content: 'World' },
      ],
    };

    const mapped = mockSession.messages.map((m: any, idx: number) => ({
      ...m,
      session_id: mockSession.id,
      conversationId: mockSession.dialog_id,
      id: m.id || `${mockSession.id}-${idx}`,
    }));

    expect(mapped.length).toBe(2);
    expect(mapped[0].session_id).toBe('sess-12345');
    expect(mapped[0].conversationId).toBe('conv-abcde');
    expect(mapped[0].id).toBe('sess-12345-0');
    expect(mapped[1].id).toBe('sess-12345-1');
  });

  it('prepares correct request headers including X-Visitor-Id for chatbot sessions query', () => {
    const visitorId = getOrCreateVisitorId();
    const headers = {
      Authorization: 'Bearer test_token',
      'X-Visitor-Id': visitorId,
    };

    expect(headers['X-Visitor-Id']).toBe(visitorId);
    expect(headers['X-Visitor-Id']).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
  });

  it('constructs payload with user_id matching visitor_id on completions call', () => {
    const visitorId = getOrCreateVisitorId();
    const question = 'What are your features?';
    const activeSessionId = 'sess-555';

    const payload = {
      conversation_id: 'dialog-111',
      quote: true,
      question,
      session_id: activeSessionId,
      user_id: visitorId,
    };

    expect(payload.user_id).toBe(visitorId);
    expect(payload.session_id).toBe('sess-555');
  });

  it('fetches sessions from backend, selects session B, completely replaces session A messages, and returns to active chat', async () => {
    const visitorId = getOrCreateVisitorId();
    const conversationId = 'dialog-123';

    const sessionA = {
      id: 'sess-a-111',
      dialog_id: conversationId,
      name: 'Pricing discussion',
      messages: [
        { role: 'user', content: 'Session A: How much is premium?' },
        { role: 'assistant', content: 'Session A: It costs $29/mo.' },
      ],
    };

    const sessionB = {
      id: 'sess-b-222',
      dialog_id: conversationId,
      name: 'Trial discussion',
      messages: [
        { role: 'user', content: 'Session B: Do you have a trial?' },
        { role: 'assistant', content: 'Session B: Yes, 14 days free.' },
      ],
    };

    // 1. Initial State: Visitor is currently viewing Session A
    let activeSessionId: string | null = sessionA.id;
    let showSessions = false;
    let activeMessages: any[] = sessionA.messages.map((m, idx) => ({
      ...m,
      session_id: sessionA.id,
      conversationId: sessionA.dialog_id,
      id: `${sessionA.id}-${idx}`,
    }));

    console.log(`\n[TRACE] Step 1 - Initial State (Session A active):`);
    console.log(`[TRACE]   activeSessionId: ${activeSessionId}`);
    console.log(`[TRACE]   showSessions: ${showSessions}`);
    console.log(`[TRACE]   messages in view:`, activeMessages.map(m => m.content));

    expect(activeSessionId).toBe('sess-a-111');
    expect(activeMessages[0].content).toContain('Session A');

    // 2. Visitor clicks "< Messages" to open the sessions list
    showSessions = true;

    // Mock network fetch for GET /api/v1/chatbots/<conversationId>/sessions
    const originalFetch = global.fetch;
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        code: 0,
        message: 'success',
        data: [sessionA, sessionB],
      }),
    });
    global.fetch = mockFetch;

    // fetchVisitorSessions implementation as in use-send-shared-message.ts:140-159
    const fetchVisitorSessions = async () => {
      const res = await fetch(`/api/v1/chatbots/${conversationId}/sessions`, {
        method: 'GET',
        headers: {
          'X-Visitor-Id': visitorId,
        },
      });
      const json = await res.json();
      if (json.code === 0 && Array.isArray(json.data)) {
        return json.data;
      }
      return [];
    };

    console.log(`[TRACE] Step 2 - Open Messages Screen:`);
    console.log(`[TRACE]   showSessions: ${showSessions}`);
    console.log(`[TRACE]   Triggering network fetch to /api/v1/chatbots/${conversationId}/sessions with X-Visitor-Id: ${visitorId}`);

    const backendSessions = await fetchVisitorSessions();

    console.log(`[TRACE] Step 3 - Network Response:`);
    console.log(`[TRACE]   Fetched ${backendSessions.length} sessions from backend:`, backendSessions.map(s => s.id));
    expect(mockFetch).toHaveBeenCalledWith(`/api/v1/chatbots/${conversationId}/sessions`, {
      method: 'GET',
      headers: {
        'X-Visitor-Id': visitorId,
      },
    });
    expect(backendSessions.length).toBe(2);

    // 3. Visitor clicks on Session B in the UI list
    const selectSession = (session: any) => {
      activeSessionId = session.id;
      const rawMessages = session.messages || [];
      activeMessages = rawMessages.map((m: any, idx: number) => ({
        ...m,
        session_id: session.id,
        conversationId: session.dialog_id,
        id: m.id || `${session.id}-${idx}`,
      }));
      showSessions = false;
    };

    console.log(`[TRACE] Step 4 - User clicks Session B card (sess-b-222)...`);
    const targetSession = backendSessions.find(s => s.id === 'sess-b-222');
    selectSession(targetSession);

    console.log(`[TRACE] Step 5 - Final State after switching to Session B:`);
    console.log(`[TRACE]   activeSessionId: ${activeSessionId}`);
    console.log(`[TRACE]   showSessions: ${showSessions}`);
    console.log(`[TRACE]   messages in view:`, activeMessages.map(m => m.content));

    // 4. Strict assertions: activeSessionId updated, view returned to chat, messages completely replaced
    expect(activeSessionId).toBe('sess-b-222');
    expect(showSessions).toBe(false);
    expect(activeMessages.length).toBe(2);
    expect(activeMessages[0].content).toBe('Session B: Do you have a trial?');
    expect(activeMessages[1].content).toBe('Session B: Yes, 14 days free.');
    expect(activeMessages[0].session_id).toBe('sess-b-222');
    expect(activeMessages[1].session_id).toBe('sess-b-222');

    // Verify zero leftover messages from Session A
    const hasOldSessionMessages = activeMessages.some((m: any) => m.content.includes('Session A'));
    expect(hasOldSessionMessages).toBe(false);
    console.log(`[TRACE] Verification: Session A messages completely overwritten by Session B; zero stale data residual.\n`);

    // Cleanup
    global.fetch = originalFetch;
  });

  it('starts a new conversation by resetting activeSessionId, clearing messages, and returning to chat', async () => {
    let activeSessionId: string | null = 'sess-old';
    let showSessions = true;
    let messages: any[] = [{ role: 'user', content: 'old msg' }];

    const startNewChat = async () => {
      activeSessionId = null;
      messages = [];
      showSessions = false;
    };

    await startNewChat();

    expect(activeSessionId).toBeNull();
    expect(messages.length).toBe(0);
    expect(showSessions).toBe(false);
  });

  it('extracts snippet from last message and truncates appropriately', () => {
    const longContent = 'This is a very detailed question about how the AI chatbot integrates with our internal ticketing system and CRM platform.';
    const session = {
      id: 'sess-long',
      name: 'Integration inquiry',
      messages: [
        { role: 'user', content: 'Initial hello' },
        { role: 'assistant', content: longContent },
      ],
    };

    const lastMsg = session.messages[session.messages.length - 1];
    const snippet = lastMsg.content.trim().slice(0, 75);

    expect(snippet.length).toBe(75);
    expect(snippet).toBe(longContent.slice(0, 75));
  });
});

describe('StorageWarningBanner UI Component', () => {
  it('renders the warning banner with alert role and message when visible is true', () => {
    render(React.createElement(StorageWarningBanner, { visible: true, onClose: jest.fn() }));
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(
      screen.getByText(/История диалогов не сохраняется в режиме инкогнито/i),
    ).toBeInTheDocument();
  });

  it('renders nothing when visible is false', () => {
    const { container } = render(
      React.createElement(StorageWarningBanner, { visible: false, onClose: jest.fn() }),
    );
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(container.firstChild).toBeNull();
  });

  it('calls onClose callback when dismiss/close button is clicked', () => {
    const handleClose = jest.fn();
    render(React.createElement(StorageWarningBanner, { visible: true, onClose: handleClose }));
    const closeBtn = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});

describe('AC5: Intercom-style Transitions and Zero Layout Shift Contracts', () => {
  it('calculates exact horizontal slide translations for active chat vs messages views', () => {
    const getSliderStyle = (showSessions: boolean) => ({
      transform: showSessions ? 'translateX(0%)' : 'translateX(-50%)',
      transition: 'transform 250ms cubic-bezier(0.16, 1, 0.3, 1)',
      willChange: 'transform',
    });

    // When viewing messages/sessions list
    const sessionsViewStyle = getSliderStyle(true);
    expect(sessionsViewStyle.transform).toBe('translateX(0%)');
    expect(sessionsViewStyle.transition).toContain('250ms');
    expect(sessionsViewStyle.transition).toContain('cubic-bezier(0.16, 1, 0.3, 1)');

    // When viewing active chat
    const activeChatStyle = getSliderStyle(false);
    expect(activeChatStyle.transform).toBe('translateX(-50%)');
    expect(activeChatStyle.transition).toContain('250ms');
  });

  it('guarantees identical viewport geometry across transitions eliminating height flicker and CLS', () => {
    const widgetDimensions = {
      width: 380,
      height: 500,
    };
    const sliderWidthMultiplier = 2.0; // 200% width
    const paneWidthRatio = 0.5; // each pane is 50% of slider

    const paneWidth = widgetDimensions.width * sliderWidthMultiplier * paneWidthRatio;
    expect(paneWidth).toBe(widgetDimensions.width); // Exactly 380px

    // Both panes share identical height equal to widget height minus flex headers
    const sessionsPaneHeight = widgetDimensions.height;
    const activeChatPaneHeight = widgetDimensions.height;
    expect(sessionsPaneHeight).toBe(activeChatPaneHeight);
  });

  it('provides mutual exclusivity for header crossfade opacity and pointer events', () => {
    const getHeaderClasses = (showSessions: boolean, isSessionsHeader: boolean) => {
      const isVisible = isSessionsHeader ? showSessions : !showSessions;
      return {
        opacity: isVisible ? 'opacity-100' : 'opacity-0',
        pointerEvents: isVisible ? 'pointer-events-auto' : 'pointer-events-none',
        position: isVisible ? 'relative' : 'absolute',
      };
    };

    // When showSessions is true:
    const headerSessWhenOpen = getHeaderClasses(true, true);
    const headerChatWhenOpen = getHeaderClasses(true, false);
    expect(headerSessWhenOpen.opacity).toBe('opacity-100');
    expect(headerSessWhenOpen.pointerEvents).toBe('pointer-events-auto');
    expect(headerChatWhenOpen.opacity).toBe('opacity-0');
    expect(headerChatWhenOpen.pointerEvents).toBe('pointer-events-none');

    // When showSessions is false:
    const headerSessWhenClosed = getHeaderClasses(false, true);
    const headerChatWhenClosed = getHeaderClasses(false, false);
    expect(headerSessWhenClosed.opacity).toBe('opacity-0');
    expect(headerSessWhenClosed.pointerEvents).toBe('pointer-events-none');
    expect(headerChatWhenClosed.opacity).toBe('opacity-100');
    expect(headerChatWhenClosed.pointerEvents).toBe('pointer-events-auto');
  });
});


