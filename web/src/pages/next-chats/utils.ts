import { NextMessageInputOnPressEnterParameter } from '@/components/message-input/next';
import { EmptyConversationId, MessageType } from '@/constants/chat';
import { IConversation, IMessage, IReference } from '@/interfaces/database/chat';
import storage from '@/utils/authorization-util';
import isEmpty from 'lodash/isEmpty';

/**
 * Regenerate is triggered from the transcript, which has no access to the input
 * box's thinking / internet toggles, so callers replay the options of their last
 * send. A view that hasn't sent anything yet has no record: fall back to the
 * input box's own defaults — it re-reads the persisted thinking level and starts
 * with internet off, so both stay in sync after a remount.
 */
export function resolveResendOptions(
  lastSendOptions: NextMessageInputOnPressEnterParameter,
): NextMessageInputOnPressEnterParameter {
  const {
    enableThinking = storage.getThinkingLevel(),
    enableInternet = false,
  } = lastSendOptions;

  return { enableThinking, enableInternet };
}

export const isConversationIdExist = (conversationId: string) => {
  return conversationId !== EmptyConversationId && conversationId !== '';
};

export const getDocumentIdsFromConversionReference = (data: IConversation) => {
  const documentIds = data.reference.reduce(
    (pre: Array<string>, cur: IReference) => {
      cur.doc_aggs
        ?.map((x) => x.doc_id)
        .forEach((x) => {
          if (pre.every((y) => y !== x)) {
            pre.push(x);
          }
        });
      return pre;
    },
    [],
  );
  return documentIds.join(',');
};

// Shared fallback so a message without a reference keeps handing MessageItem the
// same object across renders. A fresh literal here would break the item's memo
// on every streaming flush. See useMessageReferences.
export const EmptyReference: IReference = {
  doc_aggs: [],
  chunks: [],
  total: 0,
};

export const buildMessageItemReference = (
  conversation: { messages: IMessage[]; reference: IReference[] },
  message: IMessage,
) => {
  const assistantMessages = conversation.messages
    ?.filter(
      (x) =>
        x.role === MessageType.Assistant && x.content && !x.content.startsWith('**ERROR**:'), // Exclude error messages
    )
    .slice(1);
  const referenceIndex = assistantMessages.findIndex(
    (x) => x.id === message.id,
  );
  const reference = !isEmpty(message?.reference)
    ? message?.reference
    : (conversation?.reference ?? [])[referenceIndex];

  return reference ?? EmptyReference;
};
