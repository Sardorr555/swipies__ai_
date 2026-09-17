/*
 *  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

import CopyToClipboard from '@/components/copy-to-clipboard';
import PdfSheet from '@/components/pdf-drawer';
import { useClickDrawer } from '@/components/pdf-drawer/hooks';
import { MessageType, SharedFrom } from '@/constants/chat';
import { useFetchExternalAgentInputs } from '@/hooks/use-agent-request';
import { useFetchExternalChatInfo } from '@/hooks/use-chat-request';
import i18n, { changeLanguageAsync } from '@/locales/config';
import { useSendNextSharedMessage } from '@/pages/agent/hooks/use-send-shared-message';
import { removeThinkSection } from '@/utils/chat';
import {
  ChevronDown,
  ChevronLeft,
  History,
  Maximize2,
  MessageCircle,
  MessageSquare,
  Minimize2,
  Minus,
  Plus,
  Send,
  X,
} from 'lucide-react';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { formatRelativeTime } from '@/utils/date';
import {
  useGetSharedChatSearchParams,
  useSendSharedMessage,
} from '../pages/next-chats/hooks/use-send-shared-message';
import { isStorageAvailable } from '../utils/visitor-identity';
import { useWidgetResponsive } from '@/hooks/use-widget-responsive';
import FloatingChatWidgetMarkdown from './floating-chat-widget-markdown';

/**
 * Normalizes a hex color input and falls back to a safe default when invalid.
 */
const normalizeHexColor = (value: string | null, fallback: string) => {
  return value && /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(value)
    ? value
    : fallback;
};

/**
 * Darkens a hex color to derive hover and gradient variants for the widget chrome.
 */
const darkenHexColor = (hexColor: string, amount = 0.12) => {
  const normalizedHex = hexColor.replace('#', '');
  const expandedHex =
    normalizedHex.length === 3
      ? normalizedHex
          .split('')
          .map((char) => `${char}${char}`)
          .join('')
      : normalizedHex;
  const channels = expandedHex.match(/.{2}/g);

  if (!channels) {
    return hexColor;
  }

  return `#${channels
    .map((channel) => {
      const value = parseInt(channel, 16);
      const adjustedValue = Math.max(
        0,
        Math.min(255, Math.round(value * (1 - amount))),
      );
      return adjustedValue.toString(16).padStart(2, '0');
    })
    .join('')}`;
};

/**
 * Accepts a footer link from the widget query string and returns a safe HTTP(S) URL.
 */
const normalizeWidgetFooterLink = (value: string | null) => {
  const normalizedValue = value?.trim();

  if (!normalizedValue) {
    return undefined;
  }

  const candidate = /^[a-z][a-z\d+.-]*:/i.test(normalizedValue)
    ? normalizedValue
    : `https://${normalizedValue}`;

  try {
    const url = new URL(candidate);

    if (url.protocol === 'http:' || url.protocol === 'https:') {
      return url.toString();
    }
  } catch {
    return undefined;
  }

  return undefined;
};

export { StorageWarningBanner } from './storage-warning-banner';
import { StorageWarningBanner } from './storage-warning-banner';

/**
 * Stable id for the seeded agent prologue. `addNewestOneAnswer` dedupes by
 * message id, so a re-invoked effect (e.g. under React StrictMode) merges
 * into the seeded message instead of appending a duplicate.
 */
const PROLOGUE_MESSAGE_ID = 'prologue';

/**
 * Renders the embeddable floating chat widget and applies URL-driven widget settings.
 */
const FloatingChatWidget = () => {
  const { t } = useTranslation();
  const { isMobile, visualViewportHeight, visualViewportOffsetTop } = useWidgetResponsive();
  const urlParams = new URLSearchParams(
    typeof window !== 'undefined' ? window.location.search : '',
  );
  const mode = urlParams.get('mode') || 'full'; // 'button', 'window', or 'full'

  const [isOpen, setIsOpen] = useState(() => mode === 'window');
  const [isMinimized, setIsMinimized] = useState(false);
  // AC6: Desktop widget resize state.
  // Per specification (Out of Scope): "Размер сбрасывается в Compact при новом визите",
  // so this is strictly an in-memory React state with default false (Compact: 380x500).
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  const toggleResize = useCallback(() => {
    if (isMobile) return; // Strict guard: never allow resize on mobile!
    setIsExpanded((prev) => !prev);
  }, [isMobile]);
  const [inputValue, setInputValue] = useState('');
  const [lastResponseId, setLastResponseId] = useState<string | null>(null);
  const [displayMessages, setDisplayMessages] = useState<any[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const fullMessagesContainerRef = useRef<HTMLDivElement>(null);

  const {
    sharedId: conversationId,
    locale,
    from,
  } = useGetSharedChatSearchParams();

  const isFromAgent = from === SharedFrom.Agent;
  const enableStreaming = urlParams.get('streaming') !== 'false'; // Enabled by default for real-time SSE streaming
  const isMuted = urlParams.get('muted') === 'true';
  const widgetTitle = urlParams.get('widget_title')?.trim();
  const widgetSubtitle = urlParams.get('widget_subtitle')?.trim();
  const widgetFooter = urlParams.get('widget_footer')?.trim();
  const widgetFooterLink = normalizeWidgetFooterLink(
    urlParams.get('widget_footer_link'),
  );
  const widgetAccentColor = normalizeHexColor(
    urlParams.get('widget_accent_color'),
    '#2563eb',
  );
  const widgetAccentColorStrong = darkenHexColor(widgetAccentColor);
  const widgetBackgroundColor = normalizeHexColor(
    urlParams.get('widget_background_color'),
    '#ffffff',
  );
  const widgetTextColor = normalizeHexColor(
    urlParams.get('widget_text_color'),
    '#111827',
  );
  const widgetHeaderTextColor = normalizeHexColor(
    urlParams.get('widget_header_text_color'),
    '#ffffff',
  );
  const widgetFooterTextColor = normalizeHexColor(
    urlParams.get('widget_footer_text_color'),
    '#111827',
  );

  const hookResult = (
    isFromAgent ? useSendNextSharedMessage : useSendSharedMessage
  )(() => {});
  const {
    handlePressEnter,
    handleInputChange,
    value: hookValue,
    setValue,
    sendLoading,
    derivedMessages,
    hasError,
  } = hookResult;
  const findReferenceByMessageId = (hookResult as any).findReferenceByMessageId;
  const fetchVisitorSessions = (hookResult as any).fetchVisitorSessions;
  const selectSession = (hookResult as any).selectSession;
  const startNewChat = (hookResult as any).startNewChat;
  const currentSessionId = (hookResult as any).currentSessionId;

  const [showSessions, setShowSessions] = useState(false);
  const [sessionsList, setSessionsList] = useState<any[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [storageAvailable] = useState(() => isStorageAvailable());
  const [showStorageWarning, setShowStorageWarning] = useState(true);

  const sessionFetchSeqRef = useRef(0);

  const handleBackFromSessions = useCallback(() => {
    sessionFetchSeqRef.current++;
    setLoadingSessions(false);
    setShowSessions(false);
  }, []);

  const handleOpenSessions = useCallback(async () => {
    setShowSessions(true);
    if (fetchVisitorSessions) {
      const currentSeq = ++sessionFetchSeqRef.current;
      setLoadingSessions(true);
      try {
        const list = await fetchVisitorSessions();
        if (currentSeq === sessionFetchSeqRef.current) {
          setSessionsList(Array.isArray(list) ? list : []);
        }
      } catch (e) {
        if (currentSeq === sessionFetchSeqRef.current) {
          console.error('Failed to fetch visitor sessions:', e);
        }
      } finally {
        if (currentSeq === sessionFetchSeqRef.current) {
          setLoadingSessions(false);
        }
      }
    }
  }, [fetchVisitorSessions]);

  const handleSelectSession = useCallback(
    (session: any) => {
      sessionFetchSeqRef.current++;
      if (selectSession) {
        selectSession(session);
      }
      setShowSessions(false);
    },
    [selectSession],
  );

  const handleStartNewChat = useCallback(async () => {
    sessionFetchSeqRef.current++;
    setShowSessions(false);
    if (startNewChat) {
      startNewChat().catch(() => {});
    }
  }, [startNewChat]);

  // Only the agent flow exposes these. The chat flow receives its prologue
  // through the completions handshake instead, so both stay optional here.
  const { addNewestOneAnswer, isTaskMode } = hookResult as Partial<
    Pick<
      ReturnType<typeof useSendNextSharedMessage>,
      'addNewestOneAnswer' | 'isTaskMode'
    >
  >;

  // Sync our local input with the hook's value when needed
  useEffect(() => {
    setInputValue(hookValue);
  }, [hookValue]);

  // If there's an error from the hook, we can show it in the UI
  useEffect(() => {
    if (hasError) {
      // Handle error state if needed
    }
  }, [hasError]);

  // AC3 & AC5: Handle mobile fullscreen and scroll lock across embedded iframe and standalone modes
  useEffect(() => {
    if (typeof window === 'undefined') return;
    let isInIframe = false;
    try {
      isInIframe = window.self !== window.top;
    } catch {
      isInIframe = true;
    }

    if (!isInIframe) {
      // Standalone / preview mode: directly manage host document.body scroll lock
      if (isMobile && isOpen) {
        const originalOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        return () => {
          document.body.style.overflow = originalOverflow;
        };
      }
    } else {
      // Embedded mode: communicate fullscreen and scroll lock to parent snippet via postMessage
      if (isMobile && isOpen) {
        window.parent.postMessage(
          {
            type: 'SET_FULLSCREEN',
            isFullscreen: true,
          },
          '*',
        );
        return () => {
          window.parent.postMessage(
            {
              type: 'SET_FULLSCREEN',
              isFullscreen: false,
            },
            '*',
          );
        };
      }
    }
  }, [isMobile, isOpen]);

  // AC6: Desktop resize toggle protocol communication
  useEffect(() => {
    if (isMobile) return; // Strict guard: never send RESIZE_CHAT_WINDOW on mobile!

    let isInIframe = false;
    try {
      isInIframe = window.self !== window.top;
    } catch {
      isInIframe = true;
    }

    if (isInIframe) {
      window.parent.postMessage(
        {
          type: 'RESIZE_CHAT_WINDOW',
          width: isExpanded ? '520px' : '380px',
          height: isExpanded ? '640px' : '500px',
          maxWidth: 'calc(100vw - 48px)',
          maxHeight: 'calc(100vh - 128px)',
        },
        '*',
      );
    }
  }, [isMobile, isExpanded]);

  const renderStorageWarning = () => (
    <StorageWarningBanner
      visible={!storageAvailable && showStorageWarning}
      onClose={() => setShowStorageWarning(false)}
    />
  );

  const { data } = (
    isFromAgent ? useFetchExternalAgentInputs : useFetchExternalChatInfo
  )();

  // Seed the agent's opening statement. The agent send hook derives the
  // prologue from the agent canvas graph store, which is never populated on
  // the widget page, so mirror pages/agent/share and take the prologue from
  // the agentbots inputs endpoint instead. The chat flow already gets its
  // prologue from the completions handshake.
  useEffect(() => {
    if (!isFromAgent || isTaskMode) {
      return;
    }
    if (data?.prologue) {
      addNewestOneAnswer?.({
        answer: data.prologue,
        id: PROLOGUE_MESSAGE_ID,
      });
    }
  }, [isFromAgent, isTaskMode, data?.prologue, addNewestOneAnswer]);

  const title = data.title;
  const displayTitle = widgetTitle || title || t('chat.chatSupport');
  const displaySubtitle = widgetSubtitle || t('chat.replyInstantly');

  const renderFooter = () => {
    const displayFooter = widgetFooter?.trim() || 'Powered by Swipies.app';
    const targetLink = widgetFooterLink?.trim() || 'https://swipies.app';
    return (
      <div
        className="text-center p-2 text-xs opacity-80 border-t border-gray-100 flex items-center justify-center select-none"
        style={{ color: widgetFooterTextColor }}
      >
        <a
          href={targetLink}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:underline flex items-center space-x-1 font-medium transition-opacity hover:opacity-100"
          style={{ color: widgetFooterTextColor }}
        >
          <span>{displayFooter}</span>
        </a>
      </div>
    );
  };
  const headerPaddingStyle: React.CSSProperties = {
    paddingTop: isMobile
      ? 'calc(16px + env(safe-area-inset-top, 0px))'
      : '16px',
    paddingBottom: '16px',
    paddingLeft: isMobile
      ? 'calc(16px + env(safe-area-inset-left, 0px))'
      : '16px',
    paddingRight: isMobile
      ? 'calc(16px + env(safe-area-inset-right, 0px))'
      : '16px',
  };
  const bodyContainerStyle: React.CSSProperties = {
    borderRadius: isMobile ? '0' : '0 0 16px 16px',
    backgroundColor: widgetBackgroundColor,
    color: widgetTextColor,
  };
  const inputStyle: React.CSSProperties = {
    minHeight: '44px',
    maxHeight: '120px',
    color: widgetTextColor,
    backgroundColor: widgetBackgroundColor,
  };

  const renderSessionsView = () => {
    return (
      <div
        className="flex flex-col flex-1 min-h-0 overflow-hidden"
        style={bodyContainerStyle}
      >
        <div className="flex-1 overflow-y-auto overscroll-contain p-3 space-y-2">
          {loadingSessions ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 space-y-2 py-10">
              <div
                className="w-7 h-7 border-2 border-t-transparent rounded-full animate-spin"
                style={{
                  borderColor: widgetAccentColor,
                  borderTopColor: 'transparent',
                }}
              />
              <span className="text-xs">{t('common.loading') || 'Loading...'}</span>
            </div>
          ) : sessionsList.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-3">
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center"
                style={{ backgroundColor: `${widgetAccentColor}18` }}
              >
                <MessageSquare size={22} style={{ color: widgetAccentColor }} />
              </div>
              <div>
                <p className="text-sm font-semibold" style={{ color: widgetTextColor }}>
                  {t('chat.noConversations') || 'No conversations yet'}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {t('chat.startNewConversationTip') ||
                    'Your conversation history will appear here.'}
                </p>
              </div>
              <button
                type="button"
                onClick={handleStartNewChat}
                className="mt-2 px-4 py-2 text-xs font-medium text-white rounded-xl shadow-sm hover:opacity-90 transition-opacity"
                style={{ backgroundColor: widgetAccentColor }}
              >
                {t('chat.newConversation') || 'Start a conversation'}
              </button>
            </div>
          ) : (
            sessionsList.map((sess) => {
              const isCurrent = sess.id === currentSessionId;
              const relativeTime = formatRelativeTime(sess.update_time || sess.create_time);
              const count = sess.messages?.length || 0;
              const title =
                sess.name || t('chat.newConversation') || 'New conversation';
              const lastMsg = Array.isArray(sess.messages) && sess.messages.length > 0
                ? sess.messages[sess.messages.length - 1]
                : null;
              const snippet = typeof lastMsg?.content === 'string' && lastMsg.content.trim()
                ? lastMsg.content.trim().slice(0, 75)
                : null;

              return (
                <div
                  key={sess.id}
                  onClick={() => handleSelectSession(sess)}
                  className={`rounded-xl cursor-pointer transition-all duration-150 ease-out border text-left group flex items-start space-x-3 active:scale-[0.98] ${
                    isMobile ? 'p-3.5' : 'p-3'
                  } ${
                    isCurrent
                      ? 'border-blue-300 bg-blue-50/70 shadow-sm'
                      : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50/90'
                  }`}
                  style={
                    isCurrent
                      ? {
                          borderColor: `${widgetAccentColor}60`,
                          backgroundColor: `${widgetAccentColor}12`,
                        }
                      : {}
                  }
                >
                  <div
                    className={`rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
                      isMobile ? 'w-10 h-10' : 'w-8 h-8'
                    }`}
                    style={{
                      backgroundColor: isCurrent ? `${widgetAccentColor}22` : 'rgba(148, 163, 184, 0.15)',
                    }}
                  >
                    <MessageSquare
                      size={isMobile ? 18 : 15}
                      style={{ color: isCurrent ? widgetAccentColor : '#64748b' }}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between space-x-1">
                      <span
                        className={`truncate flex-1 min-w-0 max-w-[75%] block ${
                          isMobile ? 'text-sm font-semibold' : 'text-xs font-medium'
                        }`}
                        style={{ color: widgetTextColor }}
                      >
                        {title}
                      </span>
                      {relativeTime && (
                        <span
                          className={`text-gray-400 flex-shrink-0 font-normal ${
                            isMobile ? 'text-xs' : 'text-[10px]'
                          }`}
                        >
                          {relativeTime}
                        </span>
                      )}
                    </div>
                    {snippet && (
                      <p
                        className={`text-gray-500 truncate mt-0.5 ${
                          isMobile ? 'text-xs' : 'text-[11px]'
                        }`}
                      >
                        {snippet}
                      </p>
                    )}
                    <div className="flex items-center space-x-2 mt-1">
                      {isCurrent && (
                        <span
                          className={`rounded-full font-semibold ${
                            isMobile ? 'text-xs px-2 py-0.5' : 'text-[10px] px-1.5 py-0.2'
                          }`}
                          style={{
                            backgroundColor: `${widgetAccentColor}20`,
                            color: widgetAccentColor,
                          }}
                        >
                          {t('chat.active') || 'Active'}
                        </span>
                      )}
                      {count > 0 && (
                        <span
                          className={`text-gray-400 ${
                            isMobile ? 'text-xs' : 'text-[10px]'
                          }`}
                        >
                          {count} {count === 1 ? 'msg' : 'msgs'}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer / New chat button */}
        <div
          className="border-t border-gray-100 p-3 flex-shrink-0 space-y-2"
          style={bodyContainerStyle}
        >
          <button
            type="button"
            onClick={handleStartNewChat}
            className={`w-full flex items-center justify-center space-x-2 font-medium text-white rounded-xl shadow-sm hover:opacity-95 active:scale-[0.98] transition-all duration-150 ${
              isMobile ? 'py-3.5 px-5 text-sm font-semibold' : 'py-2.5 px-4 text-xs'
            }`}
            style={{ backgroundColor: widgetAccentColor }}
          >
            <Plus size={isMobile ? 18 : 15} />
            <span>{t('chat.newConversation') || 'New Conversation'}</span>
          </button>
          {renderFooter()}
        </div>
      </div>
    );
  };

  const { visible, hideModal, documentId, selectedChunk, clickDocumentButton } =
    useClickDrawer();

  // PDF drawer state tracking
  useEffect(() => {
    // Drawer state management
  }, [visible, documentId, selectedChunk]);

  // Play sound when opening
  const playNotificationSound = useCallback(() => {
    if (isMuted) {
      return;
    }

    try {
      const audioContext = new (
        window.AudioContext || (window as any).webkitAudioContext
      )();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.frequency.value = 800;
      oscillator.type = 'sine';

      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(
        0.01,
        audioContext.currentTime + 0.3,
      );

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.3);
    } catch (error) {
      console.warn(error);
      // Silent fail if audio not supported
    }
  }, [isMuted]);

  // Play sound for AI responses (Intercom-style)
  const playResponseSound = useCallback(() => {
    if (isMuted) {
      return;
    }

    try {
      const audioContext = new (
        window.AudioContext || (window as any).webkitAudioContext
      )();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.frequency.value = 600;
      oscillator.type = 'sine';

      gainNode.gain.setValueAtTime(0.2, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(
        0.01,
        audioContext.currentTime + 0.2,
      );

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.2);
    } catch (error) {
      console.warn(error);

      // Silent fail if audio not supported
    }
  }, [isMuted]);

  // Set loaded state and locale
  useEffect(() => {
    // Set component as loaded after a brief moment to prevent flash
    const timer = setTimeout(() => {
      setIsLoaded(true);
      // Tell parent window that we're ready to be shown
      window.parent.postMessage(
        {
          type: 'WIDGET_READY',
        },
        '*',
      );
    }, 50);

    if (locale && i18n.language !== locale) {
      changeLanguageAsync(locale, { persist: false });
    }

    return () => clearTimeout(timer);
  }, [locale]);

  // Handle message display based on streaming preference
  useEffect(() => {
    if (!derivedMessages) {
      setDisplayMessages([]);
      return;
    }

    if (enableStreaming) {
      // Show messages as they stream
      setDisplayMessages(derivedMessages);
    } else {
      // Only show complete messages (non-streaming mode)
      const completeMessages = derivedMessages.filter((msg, index) => {
        // Always show user messages immediately
        if (msg.role === MessageType.User) return true;

        // For AI messages, only hide in-flight generation (when loading and actively responding to previous user msg)
        if (msg.role === MessageType.Assistant) {
          const isCurrentPendingResponse =
            sendLoading &&
            index === derivedMessages.length - 1 &&
            derivedMessages[index - 1]?.role === MessageType.User;
          return !isCurrentPendingResponse;
        }

        return true;
      });
      setDisplayMessages(completeMessages);
    }
  }, [derivedMessages, enableStreaming, sendLoading]);

  const scrollToBottom = useCallback((smooth = true) => {
    const containers = [
      messagesContainerRef.current,
      fullMessagesContainerRef.current,
    ];
    containers.forEach((container) => {
      if (container) {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: smooth ? 'smooth' : 'auto',
        });
      }
    });
  }, []);

  // Auto-scroll to bottom when display messages change
  useEffect(() => {
    scrollToBottom(true);
  }, [displayMessages, scrollToBottom]);

  // Scroll to bottom immediately when opened
  useEffect(() => {
    if (isOpen) {
      scrollToBottom(false);
    }
  }, [isOpen, scrollToBottom]);

  // Render different content based on mode
  // Master mode - handles everything and creates second iframe dynamically
  useEffect(() => {
    if (mode !== 'master') return;

    const isInIframe = window.self !== window.top;

    if (isInIframe) {
      // Embedded: tell parent to create chat window iframe
      window.parent.postMessage(
        {
          type: 'CREATE_CHAT_WINDOW',
          src: window.location.href.replace('mode=master', 'mode=window'),
          isMobile,
        },
        '*',
      );
    } else {
      // Standalone: create chat window iframe ourselves
      if (!document.getElementById('chat-win')) {
        const i = document.createElement('iframe');
        i.id = 'chat-win';
        i.src = window.location.href.replace('mode=master', 'mode=window');
        i.style.cssText = isMobile
          ? 'position:fixed;top:0;left:0;right:0;bottom:0;width:100%;height:100%;height:100dvh;border:none;background:transparent;z-index:999999;display:none;border-radius:0'
          : 'position:fixed;bottom:104px;right:24px;width:380px;max-width:calc(100vw - 48px);height:500px;max-height:calc(100vh - 128px);border:none;background:transparent;z-index:9998;display:none';
        i.frameBorder = '0';
        i.allow = 'microphone;camera';
        document.body.appendChild(i);
      }
    }

    // Listen for toggle and resize messages to control the chat window iframe in standalone preview
    const handleToggle = (e: MessageEvent) => {
      const chatWindow = document.getElementById(
        'chat-win',
      ) as HTMLIFrameElement;
      if (!chatWindow) return;

      if (e.data.type === 'TOGGLE_CHAT') {
        chatWindow.style.display = e.data.isOpen ? 'block' : 'none';
        setIsOpen(e.data.isOpen);
        if (!e.data.isOpen && (window as any).__chat_prev_overflow !== undefined) {
          document.body.style.overflow = (window as any).__chat_prev_overflow;
          delete (window as any).__chat_prev_overflow;
        }
      } else if (e.data.type === 'SET_FULLSCREEN') {
        if (e.data.isFullscreen) {
          if ((window as any).__chat_prev_overflow === undefined) {
            (window as any).__chat_prev_overflow = document.body.style.overflow || '';
          }
          document.body.style.overflow = 'hidden';
          chatWindow.style.top = '0';
          chatWindow.style.left = '0';
          chatWindow.style.right = '0';
          chatWindow.style.bottom = '0';
          chatWindow.style.width = '100%';
          chatWindow.style.height = '100%';
          chatWindow.style.maxWidth = '';
          chatWindow.style.maxHeight = '';
          chatWindow.style.borderRadius = '0';
          chatWindow.style.zIndex = '999999';
        } else {
          if ((window as any).__chat_prev_overflow !== undefined) {
            document.body.style.overflow = (window as any).__chat_prev_overflow;
            delete (window as any).__chat_prev_overflow;
          }
          chatWindow.style.top = '';
          chatWindow.style.left = '';
          chatWindow.style.bottom = '104px';
          chatWindow.style.right = '24px';
          chatWindow.style.width = '380px';
          chatWindow.style.height = '500px';
          chatWindow.style.maxWidth = 'calc(100vw - 48px)';
          chatWindow.style.maxHeight = 'calc(100vh - 128px)';
          chatWindow.style.borderRadius = '';
          chatWindow.style.zIndex = '9998';
        }
      } else if (e.data.type === 'RESIZE_CHAT_WINDOW') {
        if (isMobile) return;
        if ((window as any).__chat_prev_overflow === undefined) {
          if (e.data.width) chatWindow.style.width = e.data.width;
          if (e.data.height) chatWindow.style.height = e.data.height;
          if (e.data.maxWidth) chatWindow.style.maxWidth = e.data.maxWidth;
          if (e.data.maxHeight) chatWindow.style.maxHeight = e.data.maxHeight;
          if (e.data.bottom) chatWindow.style.bottom = e.data.bottom;
          if (e.data.right) chatWindow.style.right = e.data.right;
        }
      }
    };

    window.addEventListener('message', handleToggle);
    return () => window.removeEventListener('message', handleToggle);
  }, [mode, isMobile]);

  // Synchronize isOpen state when TOGGLE_CHAT is received from host or parent window
  useEffect(() => {
    const handleToggleMessage = (e: MessageEvent) => {
      if (e.data?.type === 'TOGGLE_CHAT' && typeof e.data.isOpen === 'boolean') {
        setIsOpen(e.data.isOpen);
      }
    };
    window.addEventListener('message', handleToggleMessage);
    return () => window.removeEventListener('message', handleToggleMessage);
  }, []);

  // Play sound only when AI response is complete (not streaming chunks)
  useEffect(() => {
    if (derivedMessages && derivedMessages.length > 0 && !sendLoading) {
      const lastMessage = derivedMessages[derivedMessages.length - 1];
      if (
        lastMessage.role === MessageType.Assistant &&
        lastMessage.id !== lastResponseId &&
        derivedMessages.length > 1
      ) {
        setLastResponseId(lastMessage.id || '');
        playResponseSound();
      }
    }
  }, [derivedMessages, sendLoading, lastResponseId, playResponseSound]);

  const toggleChat = useCallback(() => {
    if (mode === 'button') {
      // In button mode, communicate with parent window to show/hide chat window
      window.parent.postMessage(
        {
          type: 'TOGGLE_CHAT',
          isOpen: !isOpen,
        },
        '*',
      );
      setIsOpen(!isOpen);
      if (!isOpen) {
        playNotificationSound();
      }
    } else {
      // In full mode, handle locally
      if (!isOpen) {
        setIsOpen(true);
        setIsMinimized(false);
        playNotificationSound();
      } else {
        setIsOpen(false);
        setIsMinimized(false);
      }
    }
  }, [isOpen, mode, playNotificationSound]);

  const minimizeChat = useCallback(() => {
    setIsMinimized(true);
  }, []);

  const handleClose = useCallback(() => {
    // Invalidate any in-flight visitor sessions fetch
    sessionFetchSeqRef.current++;
    setLoadingSessions(false);

    let isInIframe = false;
    try {
      isInIframe = typeof window !== 'undefined' && window.self !== window.top;
    } catch {
      isInIframe = true;
    }

    // Send TOGGLE_CHAT with isOpen: false to parent (if embedded) or self (if standalone)
    const target = isInIframe ? window.parent : window;
    target.postMessage(
      {
        type: 'TOGGLE_CHAT',
        isOpen: false,
      },
      '*',
    );
    setIsOpen(false);
    setIsMinimized(false);
  }, []);

  const handleSendMessage = useCallback(() => {
    const textToSend = inputValue.trim();
    if (!textToSend || sendLoading) return;

    setInputValue('');
    if (setValue) {
      setValue('');
    }
    handlePressEnter({
      enableThinking: false,
      enableInternet: false,
      messageText: textToSend,
    } as any);
  }, [inputValue, sendLoading, handlePressEnter, setValue]);

  const handleKeyPress = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
        e.preventDefault();
        handleSendMessage();
      }
    },
    [handleSendMessage],
  );

  if (!conversationId) {
    return (
      <div className="fixed bottom-5 right-5 z-50">
        <div className="bg-red-500 text-white p-4 rounded-lg shadow-lg">
          Error: No conversation ID provided
        </div>
      </div>
    );
  }

  // Remove the blocking return - we'll handle visibility with CSS instead

  const messageCount = displayMessages?.length || 0;

  // Show just the button in master mode
  if (mode === 'master') {
    // Only render the floating button in the master iframe
    return (
      <div
        className={`fixed bottom-6 right-6 z-50 transition-opacity duration-300 ${isLoaded ? 'opacity-100' : 'opacity-0'}`}
      >
        <button
          type="button"
          onClick={() => {
            const newIsOpen = !isOpen;
            setIsOpen(newIsOpen);
            if (newIsOpen) playNotificationSound();

            // Send toggle message to parent (if embedded) or self (if standalone)
            const target = window.self !== window.top ? window.parent : window;
            target.postMessage(
              {
                type: 'TOGGLE_CHAT',
                isOpen: newIsOpen,
              },
              '*',
            );
          }}
          className="w-14 h-14 text-white rounded-full shadow-lg transition-transform duration-200 active:scale-95 hover:scale-105 flex items-center justify-center group"
          style={{ backgroundColor: widgetAccentColor }}
          title={isOpen ? (t('common.close') || 'Close') : (t('chat.chatSupport') || 'Open chat')}
          aria-label={isOpen ? 'Close' : 'Open chat'}
        >
          <div className="flex items-center justify-center transition-transform duration-200">
            {isOpen ? <X size={24} /> : <MessageCircle size={24} />}
          </div>
        </button>

        {/* Unread Badge */}
        {!isOpen && messageCount > 0 && (
          <div className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center animate-pulse">
            {messageCount > 9 ? '9+' : messageCount}
          </div>
        )}
      </div>
    );
  }

  if (mode === 'button') {
    // Only render the floating button
    return (
      <div
        className={`fixed bottom-6 right-6 z-50 transition-opacity duration-300 ${isLoaded ? 'opacity-100' : 'opacity-0'}`}
      >
        <button
          type="button"
          onClick={toggleChat}
          className="w-14 h-14 text-white rounded-full shadow-lg transition-transform duration-200 active:scale-95 hover:scale-105 flex items-center justify-center group"
          style={{ backgroundColor: widgetAccentColor }}
          title={isOpen ? (t('common.close') || 'Close') : (t('chat.chatSupport') || 'Open chat')}
          aria-label={isOpen ? 'Close' : 'Open chat'}
        >
          <div className="flex items-center justify-center transition-transform duration-200">
            {isOpen ? <X size={24} /> : <MessageCircle size={24} />}
          </div>
        </button>

        {/* Unread Badge */}
        {!isOpen && messageCount > 0 && (
          <div className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center animate-pulse">
            {messageCount > 9 ? '9+' : messageCount}
          </div>
        )}
      </div>
    );
  }

  if (mode === 'window') {
    let isInIframe = false;
    try {
      isInIframe = typeof window !== 'undefined' && window.self !== window.top;
    } catch {
      isInIframe = true;
    }

    if (!isOpen && !isInIframe) {
      // In standalone mode, if closed, allow reopening via floating launcher button
      return (
        <div className="fixed bottom-6 right-6 z-50">
          <button
            type="button"
            onClick={() => setIsOpen(true)}
            className="w-14 h-14 text-white rounded-full flex items-center justify-center shadow-lg transition-transform active:scale-95"
            style={{ backgroundColor: widgetAccentColor }}
            title={t('chat.chatSupport') || 'Open chat'}
            aria-label="Open chat"
          >
            <MessageCircle size={24} />
          </button>
        </div>
      );
    }

    // Render the chat window (when open)
    return (
      <>
        <div
          data-testid="chat-widget-container"
          className={`fixed overflow-hidden flex flex-col overscroll-contain ${
            isMobile
              ? 'h-screen h-[100dvh] w-full rounded-none inset-0 z-50'
              : 'top-0 left-0 w-full h-full rounded-2xl z-50 transition-all duration-300 ease-out'
          } ${isLoaded ? 'opacity-100' : 'opacity-0'} transition-opacity duration-200`}
          style={{
            backgroundColor: widgetBackgroundColor,
            ...(isMobile
              ? {
                  height: visualViewportHeight ? `${visualViewportHeight}px` : '100dvh',
                  top: visualViewportOffsetTop ? `${visualViewportOffsetTop}px` : 0,
                }
              : {
                  width: '100%',
                  height: '100%',
                }),
          }}
        >
          {/* Header */}
          <div
            data-testid="widget-header"
            className={`flex items-center justify-between text-white ${
              isMobile ? 'rounded-none' : 'rounded-t-2xl'
            } flex-shrink-0 relative overflow-hidden`}
            style={{
              background: `linear-gradient(to right, ${widgetAccentColor}, ${widgetAccentColorStrong})`,
              ...headerPaddingStyle,
            }}
          >
            {/* Sessions Header (cross-fade) */}
            <div
              className={`flex items-center justify-between w-full transition-opacity duration-200 ease-out ${
                showSessions
                  ? 'opacity-100 pointer-events-auto'
                  : 'opacity-0 pointer-events-none absolute inset-0'
              }`}
              style={!showSessions ? headerPaddingStyle : undefined}
            >
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={handleBackFromSessions}
                  className={`${isMobile ? 'p-2.5' : 'p-1.5'} hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95`}
                  title={t('common.back') || 'Back'}
                  aria-label="Back"
                >
                  <ChevronLeft size={isMobile ? 22 : 18} />
                </button>
                <h3
                  className={`font-bold ${isMobile ? 'text-base' : 'text-sm'}`}
                  style={{ color: widgetHeaderTextColor }}
                >
                  {t('chat.conversations') || 'Messages'}
                </h3>
              </div>
              <div className="flex items-center space-x-1">
                <button
                  type="button"
                  onClick={handleStartNewChat}
                  className={`${isMobile ? 'p-2.5' : 'p-1.5'} hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95`}
                  title={t('chat.newConversation') || 'New conversation'}
                >
                  <Plus size={isMobile ? 22 : 18} />
                </button>
                {!isMobile && (
                  <button
                    type="button"
                    onClick={toggleResize}
                    className="p-1.5 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95 flex-shrink-0"
                    title={isExpanded ? (t('common.collapse') || 'Compact view') : (t('common.expand') || 'Expanded view')}
                    aria-label={isExpanded ? 'Compact view' : 'Expanded view'}
                    data-testid="sessions-resize-button"
                  >
                    {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleClose}
                  className={`${isMobile ? 'p-2.5' : 'p-1.5'} hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95 flex-shrink-0`}
                  title={t('common.close') || 'Close'}
                  aria-label="Close"
                  data-testid="sessions-close-button"
                >
                  {isMobile ? <ChevronDown size={24} /> : <X size={18} />}
                </button>
              </div>
            </div>

            {/* Active Chat Header (cross-fade) */}
            <div
              className={`flex items-center justify-between w-full transition-opacity duration-200 ease-out ${
                !showSessions
                  ? 'opacity-100 pointer-events-auto'
                  : 'opacity-0 pointer-events-none absolute inset-0'
              }`}
              style={showSessions ? headerPaddingStyle : undefined}
            >
              <div className="flex items-center space-x-2.5 min-w-0">
                {!isFromAgent && (
                  <button
                    type="button"
                    onClick={handleOpenSessions}
                    className={`${isMobile ? 'p-2.5 -ml-1' : 'p-1.5 -ml-1'} hover:bg-white hover:bg-opacity-20 rounded-full transition-colors flex-shrink-0 active:scale-95`}
                    title={t('chat.conversations') || 'Messages'}
                    aria-label="Messages"
                  >
                    <ChevronLeft size={isMobile ? 22 : 18} />
                  </button>
                )}
                <div
                  className={`${
                    isMobile ? 'w-10 h-10' : 'w-8 h-8'
                  } bg-white bg-opacity-20 rounded-full flex items-center justify-center flex-shrink-0`}
                >
                  <MessageCircle size={isMobile ? 22 : 18} />
                </div>
                <div className="min-w-0">
                  <h3
                    className={`font-semibold truncate ${isMobile ? 'text-base' : 'text-sm'}`}
                    style={{ color: widgetHeaderTextColor }}
                  >
                    {displayTitle}
                  </h3>
                  <p
                    className={`truncate ${isMobile ? 'text-xs opacity-95' : 'text-xs opacity-90'}`}
                    style={{ color: widgetHeaderTextColor }}
                  >
                    {displaySubtitle}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-1 flex-shrink-0">
                {!isFromAgent && (
                  <>
                    <button
                      type="button"
                      onClick={handleStartNewChat}
                      className={`${isMobile ? 'p-2.5' : 'p-1.5'} hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95`}
                      title={t('chat.newConversation') || 'New conversation'}
                    >
                      <Plus size={isMobile ? 22 : 18} />
                    </button>
                    <button
                      type="button"
                      onClick={handleOpenSessions}
                      className={`${isMobile ? 'p-2.5' : 'p-1.5'} hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95`}
                      title={t('chat.conversations') || 'Conversations'}
                    >
                      <History size={isMobile ? 22 : 18} />
                    </button>
                  </>
                )}
                {!isMobile && (
                  <button
                    type="button"
                    onClick={toggleResize}
                    className="p-1.5 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95 flex-shrink-0"
                    title={isExpanded ? (t('common.collapse') || 'Compact view') : (t('common.expand') || 'Expanded view')}
                    aria-label={isExpanded ? 'Compact view' : 'Expanded view'}
                    data-testid="widget-resize-button"
                  >
                    {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleClose}
                  className={`${isMobile ? 'p-2.5' : 'p-1.5'} hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95 flex-shrink-0`}
                  title={t('common.close') || 'Close'}
                  aria-label="Close"
                  data-testid="widget-close-button"
                >
                  {isMobile ? <ChevronDown size={24} /> : <X size={18} />}
                </button>
              </div>
            </div>
          </div>

          {/* Safari ITP / Incognito Warning Banner */}
          {renderStorageWarning()}

          {/* Sliding Two-Pane Viewport: Absolute Inset Zero Layers (Zero Horizontal Overflow) */}
          <div
            className="relative flex-1 min-h-0 overflow-hidden w-full"
            style={{ backgroundColor: widgetBackgroundColor }}
          >
            {/* Left Pane: Sessions View */}
            <div
              className={`absolute inset-0 w-full h-full flex flex-col min-h-0 overflow-hidden transition-transform duration-250 ease-out ${
                showSessions
                  ? 'translate-x-0 pointer-events-auto z-10'
                  : '-translate-x-full pointer-events-none z-0'
              }`}
              style={{
                transitionTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
                willChange: 'transform',
              }}
              aria-hidden={!showSessions}
            >
              {renderSessionsView()}
            </div>

            {/* Right Pane: Active Chat */}
            <div
              className={`absolute inset-0 w-full h-full flex flex-col min-h-0 overflow-hidden transition-transform duration-250 ease-out ${
                !showSessions
                  ? 'translate-x-0 pointer-events-auto z-10'
                  : 'translate-x-full pointer-events-none z-0'
              }`}
              style={{
                transitionTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
                willChange: 'transform',
              }}
              aria-hidden={showSessions}
            >
              <div className="flex flex-col flex-1 min-h-0 h-full" style={bodyContainerStyle}>
                <div
                  ref={messagesContainerRef}
                  className={`flex-1 overflow-y-auto overscroll-contain space-y-4 ${
                    isMobile ? 'p-3.5' : 'p-4'
                  }`}
                  onWheel={(e) => {
                    const element = e.currentTarget;
                    const isAtTop = element.scrollTop === 0;
                    const isAtBottom =
                      element.scrollTop + element.clientHeight >=
                      element.scrollHeight - 1;

                    // Allow scroll to pass through to parent when at boundaries
                    if ((isAtTop && e.deltaY < 0) || (isAtBottom && e.deltaY > 0)) {
                      // Let the parent handle the scroll
                      window.parent.postMessage(
                        {
                          type: 'SCROLL_PASSTHROUGH',
                          deltaY: e.deltaY,
                        },
                        '*',
                      );
                    }
                  }}
                >
                  {displayMessages?.map((message, index) => (
                    <div
                      key={index}
                      className={`flex ${message.role === MessageType.User ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`group px-4 rounded-2xl ${
                          isMobile ? 'py-3 max-w-[88%]' : 'py-2 max-w-[85%] md:max-w-[75%]'
                        } ${
                          message.role === MessageType.User
                            ? 'text-white rounded-br-md'
                            : 'rounded-bl-md'
                        }`}
                        style={
                          message.role === MessageType.User
                            ? { backgroundColor: widgetAccentColor }
                            : {
                                backgroundColor: 'rgba(148, 163, 184, 0.14)',
                                color: widgetTextColor,
                              }
                        }
                      >
                        {message.role === MessageType.User ? (
                          <p className="text-[15px] sm:text-sm leading-relaxed whitespace-pre-wrap">
                            {message.content}
                          </p>
                        ) : (
                          <div className="space-y-2">
                            <FloatingChatWidgetMarkdown
                              loading={false}
                              content={message.content}
                              reference={
                                findReferenceByMessageId?.(message.id) ||
                                message.reference || {
                                  doc_aggs: [],
                                  chunks: [],
                                  total: 0,
                                }
                              }
                              clickDocumentButton={clickDocumentButton}
                            />
                            <div
                              className={`flex justify-end transition-opacity ${
                                isMobile ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                              }`}
                              role="toolbar"
                            >
                              <CopyToClipboard
                                text={removeThinkSection(message.content)}
                                className="border-0"
                                size="icon-xs"
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {/* Clean Typing Indicator */}
                  {sendLoading &&
                    (!enableStreaming ||
                      displayMessages.length === 0 ||
                      displayMessages[displayMessages.length - 1]?.role ===
                        MessageType.User ||
                      !displayMessages[displayMessages.length - 1]?.content) && (
                    <div className="flex justify-start pl-4">
                      <div className="flex space-x-1">
                        <div
                          className="w-2 h-2 rounded-full animate-bounce"
                          style={{ backgroundColor: widgetAccentColor }}
                        ></div>
                        <div
                          className="w-2 h-2 rounded-full animate-bounce"
                          style={{
                            backgroundColor: widgetAccentColor,
                            animationDelay: '0.1s',
                          }}
                        ></div>
                        <div
                          className="w-2 h-2 rounded-full animate-bounce"
                          style={{
                            backgroundColor: widgetAccentColor,
                            animationDelay: '0.2s',
                          }}
                        ></div>
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div
                  data-testid="widget-input-area"
                  className="border-t border-gray-200 flex-shrink-0"
                  style={{
                    ...bodyContainerStyle,
                    paddingTop: isMobile ? '12px' : '16px',
                    paddingBottom: isMobile
                      ? 'calc(12px + env(safe-area-inset-bottom, 0px))'
                      : '16px',
                    paddingLeft: isMobile
                      ? 'calc(14px + env(safe-area-inset-left, 0px))'
                      : '16px',
                    paddingRight: isMobile
                      ? 'calc(14px + env(safe-area-inset-right, 0px))'
                      : '16px',
                  }}
                >
                  <div className="flex items-end space-x-2.5 sm:space-x-3">
                    <div className="flex-1">
                      <textarea
                        value={inputValue}
                        onChange={(e) => {
                          const newValue = e.target.value;
                          setInputValue(newValue);
                          handleInputChange(e);
                        }}
                        onKeyPress={handleKeyPress}
                        placeholder={t('chat.typeYourMessage')}
                        rows={1}
                        className="w-full resize-none border border-gray-300 rounded-2xl px-4 py-3 text-base sm:text-sm focus:outline-none focus:ring-2 focus:border-transparent"
                        style={inputStyle}
                        disabled={hasError || sendLoading}
                      />
                    </div>
                    <button
                      type="button"
                      onClick={handleSendMessage}
                      disabled={!inputValue.trim() || sendLoading}
                      className={`${
                        isMobile ? 'p-3.5' : 'p-3'
                      } text-white rounded-full disabled:opacity-50 disabled:cursor-not-allowed transition-transform active:scale-95 flex-shrink-0 flex items-center justify-center`}
                      style={{ backgroundColor: widgetAccentColor }}
                    >
                      <Send size={isMobile ? 20 : 18} />
                    </button>
                  </div>
                  {renderFooter()}
                </div>
              </div>
            </div>
          </div>
        </div>
        {visible && (
          <PdfSheet
            visible={visible}
            hideModal={hideModal}
            documentId={documentId}
            chunk={selectedChunk}
            width={'100vw'}
            height={'100vh'}
          />
        )}
      </>
    );
  } // Full mode - render everything together (original behavior)
  return (
    <div
      className={`transition-opacity duration-300 ${isLoaded ? 'opacity-100' : 'opacity-0'}`}
    >
      {/* Chat Widget Container */}
      {isOpen && (
        <div
          data-testid="chat-widget-container"
          className={`fixed overflow-hidden flex flex-col overscroll-contain ${
            isMobile
              ? 'h-screen h-[100dvh] w-full rounded-none inset-0 z-50'
              : `bottom-24 right-6 z-50 rounded-2xl ${
                  isMinimized ? 'h-16' : ''
                } transition-all duration-300 ease-out`
          }`}
          style={{
            backgroundColor: widgetBackgroundColor,
            ...(isMobile
              ? {
                  height: visualViewportHeight ? `${visualViewportHeight}px` : '100dvh',
                  top: visualViewportOffsetTop ? `${visualViewportOffsetTop}px` : undefined,
                }
              : {
                  width: isExpanded ? '520px' : '380px',
                  maxWidth: 'calc(100vw - 48px)',
                  height: isMinimized ? '64px' : isExpanded ? '640px' : '500px',
                  maxHeight: 'calc(100vh - 128px)',
                }),
          }}
        >
          {/* Header */}
          <div
            data-testid="full-widget-header"
            className={`flex items-center justify-between text-white ${
              isMobile ? 'rounded-none' : 'rounded-t-2xl'
            } flex-shrink-0 relative overflow-hidden`}
            style={{
              background: `linear-gradient(to right, ${widgetAccentColor}, ${widgetAccentColorStrong})`,
              ...headerPaddingStyle,
            }}
          >
            {/* Sessions Header (cross-fade) */}
            <div
              className={`flex items-center justify-between w-full transition-opacity duration-200 ease-out ${
                showSessions
                  ? 'opacity-100 pointer-events-auto'
                  : 'opacity-0 pointer-events-none absolute inset-0'
              }`}
              style={!showSessions ? headerPaddingStyle : undefined}
            >
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={handleBackFromSessions}
                  className={`${isMobile ? 'p-2.5' : 'p-1.5'} hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95`}
                  title={t('common.back') || 'Back'}
                  aria-label="Back"
                >
                  <ChevronLeft size={isMobile ? 22 : 18} />
                </button>
                <h3
                  className={`font-bold ${isMobile ? 'text-base' : 'text-sm'}`}
                  style={{ color: widgetHeaderTextColor }}
                >
                  {t('chat.conversations') || 'Messages'}
                </h3>
              </div>
              <div className="flex items-center space-x-1">
                <button
                  type="button"
                  onClick={handleStartNewChat}
                  className={`${isMobile ? 'p-2.5' : 'p-1.5'} hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95`}
                  title={t('chat.newConversation') || 'New conversation'}
                >
                  <Plus size={isMobile ? 22 : 18} />
                </button>
                {!isMobile && (
                  <button
                    type="button"
                    onClick={toggleResize}
                    className="p-1.5 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95 flex-shrink-0"
                    title={isExpanded ? (t('common.collapse') || 'Compact view') : (t('common.expand') || 'Expanded view')}
                    aria-label={isExpanded ? 'Compact view' : 'Expanded view'}
                    data-testid="full-sessions-resize-button"
                  >
                    {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                  </button>
                )}
                {!isMobile && (
                  <button
                    type="button"
                    onClick={minimizeChat}
                    className="p-1.5 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95"
                    title={t('common.minimize') || 'Minimize'}
                    aria-label="Minimize"
                  >
                    <Minus size={16} />
                  </button>
                )}
                <button
                  type="button"
                  onClick={toggleChat}
                  className={`${isMobile ? 'p-2.5' : 'p-1.5'} hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95`}
                  title={t('common.close') || 'Close'}
                  aria-label="Close"
                  data-testid="full-sessions-close-button"
                >
                  {isMobile ? <ChevronDown size={24} /> : <X size={16} />}
                </button>
              </div>
            </div>

            {/* Active Chat Header (cross-fade) */}
            <div
              className={`flex items-center justify-between w-full transition-opacity duration-200 ease-out ${
                !showSessions
                  ? 'opacity-100 pointer-events-auto'
                  : 'opacity-0 pointer-events-none absolute inset-0'
              }`}
              style={showSessions ? headerPaddingStyle : undefined}
            >
              <div className="flex items-center space-x-2.5 min-w-0">
                {!isFromAgent && (
                  <button
                    type="button"
                    onClick={handleOpenSessions}
                    className={`${isMobile ? 'p-2.5 -ml-1' : 'p-1.5 -ml-1'} hover:bg-white hover:bg-opacity-20 rounded-full transition-colors flex-shrink-0 active:scale-95`}
                    title={t('chat.conversations') || 'Messages'}
                    aria-label="Messages"
                  >
                    <ChevronLeft size={isMobile ? 22 : 18} />
                  </button>
                )}
                <div
                  className={`${
                    isMobile ? 'w-10 h-10' : 'w-8 h-8'
                  } bg-white bg-opacity-20 rounded-full flex items-center justify-center flex-shrink-0`}
                >
                  <MessageCircle size={isMobile ? 22 : 18} />
                </div>
                <div className="min-w-0">
                  <h3
                    className={`font-semibold truncate ${isMobile ? 'text-base' : 'text-sm'}`}
                    style={{ color: widgetHeaderTextColor }}
                  >
                    {displayTitle}
                  </h3>
                  <p
                    className={`truncate ${isMobile ? 'text-xs opacity-95' : 'text-xs opacity-90'}`}
                    style={{ color: widgetHeaderTextColor }}
                  >
                    {displaySubtitle}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-1 flex-shrink-0">
                {!isFromAgent && (
                  <>
                    <button
                      type="button"
                      onClick={handleStartNewChat}
                      className={`${isMobile ? 'p-2.5' : 'p-1.5'} hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95`}
                      title={t('chat.newConversation') || 'New conversation'}
                    >
                      <Plus size={isMobile ? 22 : 18} />
                    </button>
                    <button
                      type="button"
                      onClick={handleOpenSessions}
                      className={`${isMobile ? 'p-2.5' : 'p-1.5'} hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95`}
                      title={t('chat.conversations') || 'Conversations'}
                    >
                      <History size={isMobile ? 22 : 18} />
                    </button>
                  </>
                )}
                {!isMobile && (
                  <button
                    type="button"
                    onClick={toggleResize}
                    className="p-1.5 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95 flex-shrink-0"
                    title={isExpanded ? (t('common.collapse') || 'Compact view') : (t('common.expand') || 'Expanded view')}
                    aria-label={isExpanded ? 'Compact view' : 'Expanded view'}
                    data-testid="full-widget-resize-button"
                  >
                    {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                  </button>
                )}
                {!isMobile && (
                  <button
                    type="button"
                    onClick={minimizeChat}
                    className="p-1.5 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95"
                    title={t('common.minimize') || 'Minimize'}
                    aria-label="Minimize"
                  >
                    <Minus size={16} />
                  </button>
                )}
                <button
                  type="button"
                  onClick={toggleChat}
                  className={`${isMobile ? 'p-2.5' : 'p-1.5'} hover:bg-white hover:bg-opacity-20 rounded-full transition-colors active:scale-95`}
                  title={t('common.close') || 'Close'}
                  aria-label="Close"
                  data-testid="full-widget-close-button"
                >
                  {isMobile ? <ChevronDown size={24} /> : <X size={16} />}
                </button>
              </div>
            </div>
          </div>

          {/* Safari ITP / Incognito Warning Banner */}
          {!isMinimized && renderStorageWarning()}

          {/* Messages Container: Sliding Two-Pane Viewport */}
          {!isMinimized && (
            <div
              className="relative flex-1 min-h-0 overflow-hidden w-full"
              style={{ backgroundColor: widgetBackgroundColor }}
            >
              {/* Left Pane: Sessions View */}
              <div
                className={`absolute inset-0 w-full h-full flex flex-col min-h-0 overflow-hidden transition-transform duration-250 ease-out ${
                  showSessions
                    ? 'translate-x-0 pointer-events-auto z-10'
                    : '-translate-x-full pointer-events-none z-0'
                }`}
                style={{
                  transitionTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
                  willChange: 'transform',
                }}
                aria-hidden={!showSessions}
              >
                {renderSessionsView()}
              </div>

              {/* Right Pane: Active Chat */}
              <div
                className={`absolute inset-0 w-full h-full flex flex-col min-h-0 overflow-hidden transition-transform duration-250 ease-out ${
                  !showSessions
                    ? 'translate-x-0 pointer-events-auto z-10'
                    : 'translate-x-full pointer-events-none z-0'
                }`}
                style={{
                  transitionTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
                  willChange: 'transform',
                }}
                aria-hidden={showSessions}
              >
                <div className="flex flex-col flex-1 min-h-0 h-full" style={bodyContainerStyle}>
                  <div
                    ref={fullMessagesContainerRef}
                    className={`flex-1 overflow-y-auto overscroll-contain space-y-4 ${
                      isMobile ? 'p-3.5' : 'p-4'
                    }`}
                    onWheel={(e) => {
                      const element = e.currentTarget;
                      const isAtTop = element.scrollTop === 0;
                      const isAtBottom =
                        element.scrollTop + element.clientHeight >=
                        element.scrollHeight - 1;

                      // Allow scroll to pass through to parent when at boundaries
                      if (
                        (isAtTop && e.deltaY < 0) ||
                        (isAtBottom && e.deltaY > 0)
                      ) {
                        // Let the parent handle the scroll
                        window.parent.postMessage(
                          {
                            type: 'SCROLL_PASSTHROUGH',
                            deltaY: e.deltaY,
                          },
                          '*',
                        );
                      }
                    }}
                  >
                    {displayMessages?.map((message, index) => (
                      <div
                        key={index}
                        className={`flex ${message.role === MessageType.User ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`group px-4 rounded-2xl ${
                            isMobile ? 'py-3 max-w-[88%]' : 'py-2 max-w-[85%] md:max-w-[75%]'
                          } ${
                            message.role === MessageType.User
                              ? 'text-white rounded-br-md'
                              : 'rounded-bl-md'
                          }`}
                          style={
                            message.role === MessageType.User
                              ? { backgroundColor: widgetAccentColor }
                              : {
                                  backgroundColor: 'rgba(148, 163, 184, 0.14)',
                                  color: widgetTextColor,
                                }
                          }
                        >
                          {message.role === MessageType.User ? (
                            <p className="text-[15px] sm:text-sm leading-relaxed whitespace-pre-wrap">
                              {message.content}
                            </p>
                          ) : (
                            <div className="space-y-2">
                              <FloatingChatWidgetMarkdown
                                loading={false}
                                content={message.content}
                                reference={
                                  findReferenceByMessageId?.(message.id) ||
                                  message.reference || {
                                    doc_aggs: [],
                                    chunks: [],
                                    total: 0,
                                  }
                                }
                                clickDocumentButton={clickDocumentButton}
                              />
                              <div
                                className={`flex justify-end transition-opacity ${
                                  isMobile ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                                }`}
                                role="toolbar"
                              >
                                <CopyToClipboard
                                  text={removeThinkSection(message.content)}
                                  className="border-0"
                                  size="icon-xs"
                                />
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}

                    {/* Typing Indicator */}
                    {sendLoading && (
                      <div className="flex justify-start pl-4">
                        <div className="flex space-x-1">
                          <div
                            className="w-2 h-2 rounded-full animate-bounce"
                            style={{ backgroundColor: widgetAccentColor }}
                          ></div>
                          <div
                            className="w-2 h-2 rounded-full animate-bounce"
                            style={{
                              backgroundColor: widgetAccentColor,
                              animationDelay: '0.1s',
                            }}
                          ></div>
                          <div
                            className="w-2 h-2 rounded-full animate-bounce"
                            style={{
                              backgroundColor: widgetAccentColor,
                              animationDelay: '0.2s',
                            }}
                          ></div>
                        </div>
                      </div>
                    )}

                    <div ref={messagesEndRef} />
                  </div>

                  {/* Input Area */}
                  <div
                    data-testid="full-widget-input-area"
                    className="border-t border-gray-200 flex-shrink-0"
                    style={{
                      paddingTop: isMobile ? '12px' : '16px',
                      paddingBottom: isMobile
                        ? 'calc(12px + env(safe-area-inset-bottom, 0px))'
                        : '16px',
                      paddingLeft: isMobile
                        ? 'calc(14px + env(safe-area-inset-left, 0px))'
                        : '16px',
                      paddingRight: isMobile
                        ? 'calc(14px + env(safe-area-inset-right, 0px))'
                        : '16px',
                    }}
                  >
                    <div className="flex items-end space-x-2.5 sm:space-x-3">
                      <div className="flex-1">
                        <textarea
                          value={inputValue}
                          onChange={(e) => {
                            const newValue = e.target.value;
                            setInputValue(newValue);
                            // Also update the hook's state
                            handleInputChange(e);
                          }}
                          onKeyPress={handleKeyPress}
                          placeholder={t('chat.typeYourMessage')}
                          rows={1}
                          className="w-full resize-none border border-gray-300 rounded-2xl px-4 py-3 text-base sm:text-sm focus:outline-none focus:ring-2 focus:border-transparent"
                          style={inputStyle}
                          disabled={hasError || sendLoading}
                        />
                      </div>
                      <button
                        type="button"
                        onClick={handleSendMessage}
                        disabled={!inputValue.trim() || sendLoading}
                        className={`${
                          isMobile ? 'p-3.5' : 'p-3'
                        } text-white rounded-full disabled:opacity-50 disabled:cursor-not-allowed transition-transform active:scale-95 flex-shrink-0 flex items-center justify-center`}
                        style={{ backgroundColor: widgetAccentColor }}
                      >
                        <Send size={isMobile ? 20 : 18} />
                      </button>
                    </div>
                    {renderFooter()}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Floating Button */}
      {(!isMobile || !isOpen) && (
        <div className="fixed bottom-6 right-6 z-50">
          <button
            type="button"
            onClick={toggleChat}
            className="w-14 h-14 text-white rounded-full shadow-lg transition-transform duration-200 active:scale-95 hover:scale-105 flex items-center justify-center group"
            style={{ backgroundColor: widgetAccentColor }}
            title={isOpen ? (t('common.close') || 'Close') : (t('chat.chatSupport') || 'Open chat')}
            aria-label={isOpen ? 'Close' : 'Open chat'}
          >
            <div className="flex items-center justify-center transition-transform duration-200">
              {isOpen ? <X size={24} /> : <MessageCircle size={24} />}
            </div>
          </button>

          {/* Unread Badge */}
          {!isOpen && messageCount > 0 && (
            <div className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center animate-pulse">
              {messageCount > 9 ? '9+' : messageCount}
            </div>
          )}
        </div>
      )}
      <PdfSheet
        visible={visible}
        hideModal={hideModal}
        documentId={documentId}
        chunk={selectedChunk}
      />
    </div>
  );
};

export default FloatingChatWidget;
