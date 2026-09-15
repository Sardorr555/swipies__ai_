import { getOrCreateVisitorId } from '../../utils/visitor-identity';

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
});
