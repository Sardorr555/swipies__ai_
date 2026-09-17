import { PropsWithChildren } from 'react';
import { useSearchParams } from 'react-router';
import { useTranslation } from 'react-i18next';
import { RotateCcw, ExternalLink } from 'lucide-react';
import { RAGFlowAvatar } from './ragflow-avatar';
import { Button } from './ui/button';

type EmbedContainerProps = {
  title: string;
  avatar?: string;
  subtitle?: string;
  handleReset?(): void;
} & PropsWithChildren;

const normalizeHexColor = (value: string | null | undefined, fallback: string) => {
  const normalizedValue = value?.trim() ?? '';
  return /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(normalizedValue)
    ? normalizedValue
    : fallback;
};

export function EmbedContainer({
  title,
  avatar,
  subtitle,
  children,
  handleReset,
}: EmbedContainerProps) {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();

  const customTitle = searchParams.get('widget_title');
  const customSubtitle = searchParams.get('widget_subtitle');
  const accentColor = searchParams.get('widget_accent_color');
  const bgColor = searchParams.get('widget_background_color');
  const textColor = searchParams.get('widget_text_color');
  const headerTextColor = searchParams.get('widget_header_text_color');
  const footerTextColor = searchParams.get('widget_footer_text_color');

  const displayTitle = customTitle?.trim() || title || 'Chat Support';
  const displaySubtitle = customSubtitle?.trim() || subtitle || 'AI Assistant';

  const effectiveAccentColor = accentColor ? normalizeHexColor(accentColor, '#2563eb') : undefined;
  const effectiveBgColor = bgColor ? normalizeHexColor(bgColor, '#ffffff') : undefined;
  const effectiveTextColor = textColor ? normalizeHexColor(textColor, '#111827') : undefined;
  const effectiveHeaderTextColor = headerTextColor ? normalizeHexColor(headerTextColor, '#111827') : undefined;
  const effectiveFooterTextColor = footerTextColor ? normalizeHexColor(footerTextColor, '#6b7280') : undefined;

  return (
    <div
      className="w-full h-full min-h-screen h-[100dvh] flex flex-col bg-background text-foreground overflow-hidden select-text"
      style={{
        backgroundColor: effectiveBgColor,
        color: effectiveTextColor,
      }}
    >
      {/* Modern Header */}
      <header
        className="w-full border-b border-border/60 px-4 py-3 flex items-center justify-between flex-shrink-0 bg-background/80 backdrop-blur-md z-10 transition-colors"
        style={{
          color: effectiveHeaderTextColor,
          borderBottomColor: effectiveHeaderTextColor ? `${effectiveHeaderTextColor}22` : undefined,
        }}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="relative flex-shrink-0">
            <RAGFlowAvatar
              avatar={avatar}
              name={displayTitle}
              isPerson
              className="size-9 sm:size-10 rounded-full border border-border/50 shadow-sm"
            />
            <span
              className="absolute bottom-0 right-0 size-2.5 bg-emerald-500 rounded-full ring-2 ring-background"
              title="Online"
            />
          </div>
          <div className="min-w-0 flex flex-col">
            <h1 className="text-sm sm:text-base font-semibold truncate leading-tight">
              {displayTitle}
            </h1>
            <span className="text-xs text-muted-foreground truncate leading-tight mt-0.5">
              {displaySubtitle}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {handleReset && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              className="h-8 px-3 rounded-full text-xs font-medium border-border/70 hover:bg-muted/60 transition-colors flex items-center gap-1.5"
              title={t('chat.newConversation') || 'New conversation'}
            >
              <RotateCcw className="size-3.5" />
              <span className="hidden sm:inline">{t('chat.newConversation') || 'New chat'}</span>
            </Button>
          )}
        </div>
      </header>

      {/* Main Conversation Area */}
      <main className="flex-1 min-h-0 flex flex-col overflow-hidden relative w-full">
        {children}
      </main>

      {/* Permanent Verified Footer */}
      <footer
        className="w-full py-2.5 px-4 text-center border-t border-border/40 bg-background/70 backdrop-blur-sm flex-shrink-0 flex items-center justify-center gap-1.5 text-xs text-muted-foreground transition-colors"
        style={{
          color: effectiveFooterTextColor,
          borderTopColor: effectiveFooterTextColor ? `${effectiveFooterTextColor}18` : undefined,
        }}
      >
        <span>Powered by</span>
        <a
          href="https://swipies.app"
          target="_blank"
          rel="noopener noreferrer"
          className="font-semibold transition-opacity hover:opacity-80 underline-offset-2 hover:underline inline-flex items-center gap-1"
          style={{
            color: effectiveAccentColor || 'var(--primary, #2563eb)',
          }}
        >
          <span>Swipies.app</span>
          <ExternalLink className="size-3 opacity-70" />
        </a>
      </footer>
    </div>
  );
}
