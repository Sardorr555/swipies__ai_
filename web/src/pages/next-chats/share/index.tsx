import { EmbedContainer } from '@/components/embed-container';
import { NextMessageInput } from '@/components/message-input/next';
import MessageItem from '@/components/message-item';
import PdfSheet from '@/components/pdf-drawer';
import { useClickDrawer } from '@/components/pdf-drawer/hooks';
import { useSyncThemeFromParams } from '@/components/theme-provider';
import { MessageType } from '@/constants/chat';
import { useFetchExternalChatInfo } from '@/hooks/use-chat-request';
import i18n, { changeLanguageAsync } from '@/locales/config';
import { buildMessageUuidWithRole } from '@/utils/chat';
import React, { forwardRef } from 'react';
import { useSendButtonDisabled } from '../hooks/use-button-disabled';
import {
  useGetSharedChatSearchParams,
  useSendSharedMessage,
} from '../hooks/use-send-shared-message';
import { useMessageReferences } from '../hooks/use-message-references';
import { EmptyReference } from '../utils';

const ChatContainer = () => {
  const {
    sharedId: conversationId,
    locale,
    theme,
    visibleAvatar,
  } = useGetSharedChatSearchParams();
  useSyncThemeFromParams(theme);
  const { visible, hideModal, documentId, selectedChunk, clickDocumentButton } =
    useClickDrawer();

  const {
    handlePressEnter,
    handleInputChange,
    value,
    sendLoading,
    derivedMessages,
    hasError,
    stopOutputMessage,
    scrollRef,
    messageContainerRef,
    removeAllMessagesExceptFirst,
  } = useSendSharedMessage();
  const sendDisabled = useSendButtonDisabled(value);
  const { data: chatInfo } = useFetchExternalChatInfo();

  const messageReferences = useMessageReferences(derivedMessages, undefined);

  React.useEffect(() => {
    if (locale && i18n.language !== locale) {
      changeLanguageAsync(locale, { persist: false });
    }
  }, [locale, visibleAvatar]);

  const avatarDialogSrc = chatInfo.avatar;

  if (!conversationId) {
    return <div>empty</div>;
  }

  return (
    <>
      <EmbedContainer
        title={chatInfo.title}
        avatar={chatInfo.avatar}
        handleReset={removeAllMessagesExceptFirst}
        hideReset={sendLoading}
      >
        <div className="flex flex-1 min-h-0 flex-col w-full h-full max-w-4xl mx-auto px-3 sm:px-6">
          <div
            className="flex-1 min-h-0 overflow-y-auto scrollbar-auto py-4 space-y-4"
            ref={messageContainerRef}
          >
            <div>
              {derivedMessages?.map((message, i) => {
                return (
                  <MessageItem
                    visibleAvatar={visibleAvatar}
                    key={buildMessageUuidWithRole(message)}
                    avatarDialog={avatarDialogSrc}
                    item={message}
                    nickname="You"
                    reference={messageReferences.get(message) ?? EmptyReference}
                    loading={
                      message.role === MessageType.Assistant &&
                      sendLoading &&
                      derivedMessages?.length - 1 === i
                    }
                    index={i}
                    isLast={i === derivedMessages.length - 1}
                    clickDocumentButton={clickDocumentButton}
                    showLikeButton={false}
                    showLoudspeaker={false}
                  ></MessageItem>
                );
              })}
            </div>
            <div ref={scrollRef} />
          </div>
          <div className="flex-shrink-0 pt-2 pb-3 sm:pb-4">
            <NextMessageInput
              isShared
              value={value}
              disabled={hasError}
              sendDisabled={sendDisabled}
              resize="none"
              conversationId={conversationId}
              onInputChange={handleInputChange}
              onPressEnter={handlePressEnter}
              sendLoading={sendLoading}
              uploadMethod="external_upload_and_parse"
              showUploadIcon={false}
              stopOutputMessage={stopOutputMessage}
              showReasoning
              showInternet={
                chatInfo?.has_web_search_provider ?? chatInfo?.has_tavily_key
              }
            ></NextMessageInput>
          </div>
        </div>
      </EmbedContainer>
      {visible && (
        <PdfSheet
          visible={visible}
          hideModal={hideModal}
          documentId={documentId}
          chunk={selectedChunk}
        ></PdfSheet>
      )}
    </>
  );
};

export default forwardRef(ChatContainer);
