import { NextMessageInputOnPressEnterParameter } from '@/components/message-input/next';
import message from '@/components/ui/message';
import { MessageType, SharedFrom } from '@/constants/chat';
import {
  useHandleMessageInputChange,
  useSelectDerivedMessages,
  useSendMessageWithSse,
} from '@/hooks/logic-hooks';
import { useFetchExternalChatInfo } from '@/hooks/use-chat-request';
import { Message } from '@/interfaces/database/chat';
import { getAuthorization } from '@/utils/authorization-util';
import { getOrCreateVisitorId } from '@/utils/visitor-identity';
import { get } from 'lodash';
import trim from 'lodash/trim';
import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import { v4 as uuid } from 'uuid';

const isCompletionError = (res: any) =>
  res && (res?.response.status !== 200 || res?.data?.code !== 0);

export const useSendButtonDisabled = (value: string) => {
  return trim(value) === '';
};

export const useGetSharedChatSearchParams = () => {
  const [searchParams] = useSearchParams();
  const data_prefix = 'data_';
  const data = Object.fromEntries(
    Array.from(searchParams.entries())
      .filter(([key]) => key.startsWith(data_prefix))
      .map(([key, value]) => [key.replace(data_prefix, ''), value]),
  );
  return {
    from: searchParams.get('from') as SharedFrom,
    sharedId: searchParams.get('shared_id'),
    locale: searchParams.get('locale'),
    theme: searchParams.get('theme'),
    data: data,
    visibleAvatar: searchParams.get('visible_avatar')
      ? searchParams.get('visible_avatar') !== '1'
      : true,
  };
};

export const useSendSharedMessage = () => {
  const {
    from,
    sharedId: conversationId,
    data: data,
  } = useGetSharedChatSearchParams();
  const visitorId = getOrCreateVisitorId();
  const { handleInputChange, value, setValue } = useHandleMessageInputChange();
  const completionUrl = `/api/v1/${from === SharedFrom.Agent ? 'agentbots' : 'chatbots'}/${conversationId}/completions`;
  const { data: chatInfo } = useFetchExternalChatInfo();
  const { send, answer, done, stopOutputMessage } = useSendMessageWithSse();
  const {
    derivedMessages,
    setDerivedMessages,
    removeLatestMessage,
    addNewestAnswer,
    addNewestQuestion,
    scrollRef,
    messageContainerRef,
    removeAllMessages,
    removeAllMessagesExceptFirst,
  } = useSelectDerivedMessages();
  const [hasError, setHasError] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (
      message: Message,
      id?: string,
      enableThinking?: boolean,
      enableInternet?: boolean,
    ) => {
      const visitorHeaders = { 'X-Visitor-Id': visitorId };
      const res = await send(
        completionUrl,
        {
          conversation_id: id ?? conversationId,
          quote: true,
          question: message.content,
          session_id: activeSessionId || get(derivedMessages, '0.session_id'),
          reasoning: enableThinking,
          internet: enableInternet,
          user_id: visitorId,
          ...(chatInfo?.llm_id ? { model_name: chatInfo.llm_id } : {}),
        },
        undefined,
        visitorHeaders,
      );

      if (isCompletionError(res)) {
        // cancel loading
        setValue(message.content);
        removeLatestMessage();
      }
    },
    [
      send,
      completionUrl,
      conversationId,
      activeSessionId,
      derivedMessages,
      setValue,
      removeLatestMessage,
      chatInfo,
      visitorId,
    ],
  );

  const handleSendMessage = useCallback(
    async (
      message: Message,
      enableThinking?: boolean,
      enableInternet?: boolean,
    ) => {
      sendMessage(message, undefined, enableThinking, enableInternet);
    },
    [sendMessage],
  );

  const fetchSessionId = useCallback(async () => {
    const payload = { question: '', user_id: visitorId };
    const visitorHeaders = { 'X-Visitor-Id': visitorId };
    const ret = await send(
      completionUrl,
      { ...payload, ...data },
      undefined,
      visitorHeaders,
    );
    if (isCompletionError(ret)) {
      message.error(ret?.data.message ?? 'Unknown error');
      setHasError(true);
    }
  }, [send, completionUrl, visitorId, data]);

  const fetchVisitorSessions = useCallback(async () => {
    if (from === SharedFrom.Agent || !conversationId) return [];
    try {
      const auth = getAuthorization();
      const res = await fetch(`/api/v1/chatbots/${conversationId}/sessions`, {
        method: 'GET',
        headers: {
          ...(auth ? { Authorization: auth } : {}),
          'X-Visitor-Id': visitorId,
        },
      });
      const json = await res.json();
      if (json.code === 0 && Array.isArray(json.data)) {
        return json.data;
      }
    } catch (err) {
      console.error('Failed to load visitor sessions:', err);
    }
    return [];
  }, [conversationId, from, visitorId]);

  const selectSession = useCallback(
    (session: any) => {
      if (!session) return;
      setActiveSessionId(session.id);
      const rawMessages = session.messages || [];
      const mapped = rawMessages.map((m: any, idx: number) => ({
        ...m,
        session_id: session.id,
        conversationId: session.dialog_id,
        id: m.id || `${session.id}-${idx}`,
      }));
      setDerivedMessages(mapped);
    },
    [setDerivedMessages],
  );

  const startNewChat = useCallback(async () => {
    setActiveSessionId(null);
    removeAllMessages();
    await fetchSessionId();
  }, [removeAllMessages, fetchSessionId]);

  useEffect(() => {
    fetchSessionId();
  }, [fetchSessionId]);

  useEffect(() => {
    if (answer.answer) {
      addNewestAnswer(answer);
    }
  }, [answer, addNewestAnswer]);

  const handlePressEnter = useCallback(
    ({
      enableThinking,
      enableInternet,
    }: NextMessageInputOnPressEnterParameter) => {
      if (trim(value) === '') return;
      const id = uuid();
      if (done) {
        setValue('');
        addNewestQuestion({
          content: value,
          doc_ids: [],
          id,
          role: MessageType.User,
        });
        handleSendMessage(
          {
            content: value.trim(),
            id,
            role: MessageType.User,
          },
          enableThinking,
          enableInternet,
        );
      }
    },
    [addNewestQuestion, done, handleSendMessage, setValue, value],
  );

  return {
    handlePressEnter,
    handleInputChange,
    value,
    sendLoading: !done,
    loading: false,
    derivedMessages,
    hasError,
    stopOutputMessage,
    scrollRef,
    messageContainerRef,
    removeAllMessages,
    removeAllMessagesExceptFirst,
    visitorId,
    currentSessionId: activeSessionId || get(derivedMessages, '0.session_id'),
    fetchVisitorSessions,
    selectSession,
    startNewChat,
  };
};

