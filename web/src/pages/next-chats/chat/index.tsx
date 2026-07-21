import EmbedDialog from '@/components/embed-dialog';
import { useShowEmbedModal } from '@/components/embed-dialog/use-show-embed-dialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { SharedFrom } from '@/constants/chat';
import {
  useFetchSessionList,
  useFetchSessionManually,
  useGetChatSearchParams,
} from '@/hooks/use-chat-request';
import { IClientConversation } from '@/interfaces/database/chat';
import { RootLayoutContainer } from '@/layouts/root-layout';
import { cn } from '@/lib/utils';
import { Routes } from '@/routes';
import { useMount } from 'ahooks';
import { isEmpty } from 'lodash';
import {
  LucideArrowBigLeft,
  LucideArrowLeft,
  LucideArrowUpRight,
  LucideCode,
} from 'lucide-react';
import { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router';
import { useHandleClickConversationCard } from '../hooks/use-click-card';
import { ChatSettings } from './app-settings/chat-settings';
import { MultipleChatBox } from './chat-box/next-multiple-chat-box';
import { SingleChatBox } from './chat-box/single-chat-box';
import { Sessions } from './sessions';
import { useAddChatBox } from './use-add-box';
import { useSwitchDebugMode } from './use-switch-debug-mode';

export default function Chat() {
  const { t } = useTranslation();
  const { id } = useParams();
  const [currentConversation, setCurrentConversation] =
    useState<IClientConversation>({} as IClientConversation);

  const { fetchSessionManually } = useFetchSessionManually();

  const { handleConversationCardClick, controller, stopOutputMessage } =
    useHandleClickConversationCard();

  const { isDebugMode, switchDebugMode } = useSwitchDebugMode();
  const { removeChatBox, addChatBox, chatBoxIds, hasSingleChatBox } =
    useAddChatBox(isDebugMode);

  const { conversationId, isNew } = useGetChatSearchParams();

  const { data: dialogList } = useFetchSessionList();

  const { showEmbedModal, hideEmbedModal, embedVisible, beta } =
    useShowEmbedModal();

  const currentConversationName = useMemo(() => {
    return (
      dialogList.find((x) => x.id === conversationId)?.name ||
      t('chat.newConversation')
    );
  }, [conversationId, dialogList, t]);

  const fetchConversation: typeof handleConversationCardClick = useCallback(
    async (conversationId, isNew) => {
      if (conversationId && !isNew) {
        const conversation = await fetchSessionManually(conversationId);
        if (!isEmpty(conversation)) {
          setCurrentConversation(conversation);
        }
      }
    },
    [fetchSessionManually],
  );

  const handleSessionClick: typeof handleConversationCardClick = useCallback(
    (conversationId, isNew) => {
      handleConversationCardClick(conversationId, isNew);
      fetchConversation(conversationId, isNew);
    },
    [fetchConversation, handleConversationCardClick],
  );

  useMount(() => {
    fetchConversation(conversationId, isNew === 'true');
  });

  if (isDebugMode) {
    return (
      <section
        className="pt-5 pb-14 h-[100vh] flex flex-col"
        data-testid="chat-detail-multimodel-root"
      >
        <header className="px-10 pb-5">
          <div className="mb-5">
            <Button
              variant="outline"
              onClick={switchDebugMode}
              data-testid="chat-detail-multimodel-back"
            >
              <LucideArrowBigLeft />
              <span>{t('common.back')}</span>
            </Button>
          </div>

          <span className="text-2xl">
            {t('chat.multipleModels')} ({chatBoxIds.length}/3)
          </span>
        </header>

        <MultipleChatBox
          chatBoxIds={chatBoxIds}
          controller={controller}
          removeChatBox={removeChatBox}
          addChatBox={addChatBox}
          stopOutputMessage={stopOutputMessage}
          conversation={currentConversation}
        ></MultipleChatBox>
      </section>
    );
  }

  return (
    <RootLayoutContainer>
      <section className="h-full flex flex-col" data-testid="chat-detail">
        <article className="flex flex-1 min-h-0 pb-9">
          <Sessions handleConversationCardClick={handleSessionClick}></Sessions>

          <Card className="flex-1 min-w-0 bg-transparent border-none shadow-none h-full">
            <CardContent className="flex p-0 h-full">
              <Card className="flex flex-col flex-1 bg-transparent min-w-0">
                <CardHeader
                  className={cn('p-4 border-b border-border-button bg-bg-card/40', {
                    'border-b-0.5 border-border-button': hasSingleChatBox,
                  })}
                >
                  <div className="flex items-center justify-between gap-4 w-full">
                    {/* Left: Back to main page button */}
                    <div className="flex items-center gap-2 min-w-0">
                      <Button
                        variant="outline"
                        size="sm"
                        asChild
                        className="gap-2 text-text-secondary hover:text-text-primary border-border-button shrink-0"
                        data-testid="chat-detail-back-button"
                      >
                        <Link to={Routes.Chats}>
                          <LucideArrowLeft className="size-4" />
                          <span>{t('common.back') || 'Назад'}</span>
                        </Link>
                      </Button>
                      <span className="truncate text-sm font-semibold text-text-primary hidden md:inline ml-2">
                        {currentConversationName}
                      </span>
                    </div>

                    {/* Center: Embed into webpage button */}
                    <div className="flex items-center justify-center">
                      <Button
                        onClick={showEmbedModal}
                        size="sm"
                        className="gap-2 bg-gradient-to-r from-[#478AF5] to-[#42D7E7] hover:from-[#3a7ae0] hover:to-[#35c5d4] text-white font-semibold px-4 py-1.5 rounded-full shadow-md hover:shadow-lg transition-all duration-200 hover:scale-105"
                        data-testid="chat-detail-embed-button-prominent"
                      >
                        <LucideCode className="size-4 stroke-[2.2]" />
                        <span className="text-xs sm:text-sm">
                          {t('common.embedIntoSite') || 'Embed into webpage'}
                        </span>
                      </Button>
                    </div>

                    {/* Right: Multiple Models Toggle */}
                    <div className="flex items-center justify-end gap-2 min-w-0">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={switchDebugMode}
                        data-testid="chat-detail-multimodel-toggle"
                        className="text-xs gap-1"
                      >
                        <LucideArrowUpRight className="size-4" />
                        <span className="hidden sm:inline">
                          {t('chat.multipleModels')}
                        </span>
                      </Button>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="flex-1 p-0 min-h-0">
                  <SingleChatBox
                    controller={controller}
                    stopOutputMessage={stopOutputMessage}
                    conversation={currentConversation}
                  />
                </CardContent>
              </Card>

              <ChatSettings hasSingleChatBox={hasSingleChatBox}></ChatSettings>
            </CardContent>
          </Card>
        </article>
      </section>

      {/* Embed Dialog */}
      <EmbedDialog
        visible={embedVisible}
        hideModal={hideEmbedModal}
        token={id || conversationId || ''}
        from={SharedFrom.Chat}
        beta={beta}
        isAgent={false}
      />
    </RootLayoutContainer>
  );
}
