import CopyToClipboard from '@/components/copy-to-clipboard';
import { SelectWithSearch } from '@/components/originui/select-with-search';
import { Button, ButtonLoading } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { SharedFrom } from '@/constants/chat';
import {
  LanguageAbbreviation,
  LanguageAbbreviationMap,
  ThemeEnum,
} from '@/constants/common';
import { IModalProps } from '@/interfaces/common';
import { Routes } from '@/routes';
import { zodResolver } from '@hookform/resolvers/zod';
import { isEmpty, trim } from 'lodash';
import {
  Code,
  ExternalLink,
  Lock,
  MessageSquare,
  Monitor,
  Palette,
  Sparkles,
} from 'lucide-react';
import { memo, useCallback, useMemo } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import {
  oneDark,
  oneLight,
} from 'react-syntax-highlighter/dist/esm/styles/prism';
import { z } from 'zod';
import { RAGFlowFormItem } from '../ragflow-form';
import { SwitchFormField } from '../switch-fom-field';
import { useIsDarkTheme } from '../theme-provider';
import { Input } from '../ui/input';
import { defaultWidgetSettings, WidgetSettings } from './constant';

export { defaultWidgetSettings } from './constant';
export type { WidgetSettings } from './constant';

const FormSchema = z.object({
  visibleAvatar: z.boolean(),
  published: z.boolean(),
  locale: z.string(),
  embedType: z.enum(['fullscreen', 'widget']),
  enableStreaming: z.boolean(),
  muteWidget: z.boolean(),
  theme: z.enum([ThemeEnum.Light, ThemeEnum.Dark]),
  userId: z.string().optional(),
  widgetTitle: z.string(),
  widgetSubtitle: z.string(),
  widgetFooterText: z.string(),
  widgetFooterLink: z.string(),
  widgetAccentColor: z.string(),
  widgetBackgroundColor: z.string(),
  widgetTextColor: z.string(),
  widgetHeaderTextColor: z.string(),
  widgetFooterTextColor: z.string(),
  iframeWidth: z.string().optional(),
  iframeHeight: z.string().optional(),
  iframeRadius: z.string().optional(),
  widgetSizePreset: z.string().optional(),
});

type IProps = IModalProps<any> & {
  token: string;
  from: SharedFrom;
  beta: string;
  isAgent: boolean;
  initialWidgetSettings?: Partial<WidgetSettings>;
  onSaveWidgetSettings?: (settings: WidgetSettings) => Promise<unknown>;
  savingWidgetSettings?: boolean;
};

const normalizeHexColor = (value: string | undefined, fallback: string) => {
  const normalizedValue = value?.trim() ?? '';
  return /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(normalizedValue)
    ? normalizedValue
    : fallback;
};

const COLOR_PRESETS = [
  {
    name: 'Swipies Blue',
    accent: '#2563eb',
    bg: '#ffffff',
    text: '#111827',
    headerText: '#ffffff',
    footerText: '#6b7280',
    colorPreview: '#2563eb',
  },
  {
    name: 'Slate Dark',
    accent: '#3b82f6',
    bg: '#0f172a',
    text: '#f8fafc',
    headerText: '#f8fafc',
    footerText: '#94a3b8',
    colorPreview: '#0f172a',
  },
  {
    name: 'Emerald Fresh',
    accent: '#059669',
    bg: '#ffffff',
    text: '#064e3b',
    headerText: '#ffffff',
    footerText: '#047857',
    colorPreview: '#059669',
  },
  {
    name: 'Royal Violet',
    accent: '#7c3aed',
    bg: '#ffffff',
    text: '#1e1b4b',
    headerText: '#ffffff',
    footerText: '#6b7280',
    colorPreview: '#7c3aed',
  },
  {
    name: 'Crimson Rose',
    accent: '#e11d48',
    bg: '#ffffff',
    text: '#1e1b4b',
    headerText: '#ffffff',
    footerText: '#6b7280',
    colorPreview: '#e11d48',
  },
  {
    name: 'Amber Warmth',
    accent: '#d97706',
    bg: '#ffffff',
    text: '#111827',
    headerText: '#ffffff',
    footerText: '#6b7280',
    colorPreview: '#d97706',
  },
];

/**
 * Builds the embed code preview and customization UI for shared chat and agent widgets.
 */
function EmbedDialog({
  hideModal,
  token = '',
  from,
  beta = '',
  isAgent,
  initialWidgetSettings,
  onSaveWidgetSettings,
  savingWidgetSettings,
  visible,
}: IProps) {
  const { t } = useTranslation();
  const isDarkTheme = useIsDarkTheme();

  const form = useForm<z.infer<typeof FormSchema>>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      visibleAvatar: false,
      published: false,
      locale: '',
      embedType: 'fullscreen' as const,
      theme: ThemeEnum.Light,
      ...defaultWidgetSettings,
      ...initialWidgetSettings,
      widgetFooterText: 'Powered by Swipies.app',
      widgetFooterLink: 'https://swipies.app',
    },
  });

  const values = useWatch({ control: form.control });

  const languageOptions = useMemo(() => {
    return Object.values(LanguageAbbreviation).map((x) => ({
      label: LanguageAbbreviationMap[x],
      value: x,
    }));
  }, []);

  const generateIframeSrc = useCallback(() => {
    const {
      visibleAvatar,
      published,
      locale,
      embedType,
      enableStreaming,
      muteWidget,
      theme,
      userId,
      widgetTitle,
      widgetSubtitle,
      widgetAccentColor,
      widgetBackgroundColor,
      widgetTextColor,
      widgetHeaderTextColor,
      widgetFooterTextColor,
    } = values;

    const baseRoute =
      embedType === 'widget'
        ? Routes.ChatWidget
        : from === SharedFrom.Agent
          ? Routes.AgentShare
          : Routes.ChatShare;

    const src = new URL(`${location.origin}${baseRoute}`);
    src.searchParams.append('shared_id', token);
    src.searchParams.append('from', from);
    src.searchParams.append('auth', beta);

    if (published) {
      src.searchParams.append('release', 'true');
    }
    if (visibleAvatar) {
      src.searchParams.append('visible_avatar', '1');
    }
    if (locale) {
      src.searchParams.append('locale', locale);
    }

    if (embedType === 'widget') {
      src.searchParams.append('mode', 'master');
      src.searchParams.append('streaming', String(enableStreaming));
      src.searchParams.append('muted', String(muteWidget));
      if (!isEmpty(trim(widgetTitle))) {
        src.searchParams.append('widget_title', widgetTitle ?? '');
      }
      if (!isEmpty(trim(widgetSubtitle))) {
        src.searchParams.append('widget_subtitle', widgetSubtitle ?? '');
      }
      src.searchParams.append('widget_footer', 'Powered by Swipies.app');
      src.searchParams.append('widget_footer_link', 'https://swipies.app');
      src.searchParams.append(
        'widget_accent_color',
        normalizeHexColor(widgetAccentColor, '#2563eb'),
      );
      src.searchParams.append(
        'widget_background_color',
        normalizeHexColor(widgetBackgroundColor, '#ffffff'),
      );
      src.searchParams.append(
        'widget_text_color',
        normalizeHexColor(widgetTextColor, '#111827'),
      );
      src.searchParams.append(
        'widget_header_text_color',
        normalizeHexColor(widgetHeaderTextColor, '#ffffff'),
      );
      src.searchParams.append(
        'widget_footer_text_color',
        normalizeHexColor(widgetFooterTextColor, '#6b7280'),
      );
    } else {
      // Fullscreen chat / traditional iframe embed parameters
      src.searchParams.append('widget_footer', 'Powered by Swipies.app');
      src.searchParams.append('widget_footer_link', 'https://swipies.app');
      if (theme) {
        src.searchParams.append('theme', theme);
      }
      if (!isEmpty(trim(widgetTitle))) {
        src.searchParams.append('widget_title', widgetTitle ?? '');
      }
      if (!isEmpty(trim(widgetSubtitle))) {
        src.searchParams.append('widget_subtitle', widgetSubtitle ?? '');
      }
      src.searchParams.append(
        'widget_accent_color',
        normalizeHexColor(widgetAccentColor, '#2563eb'),
      );
      src.searchParams.append(
        'widget_background_color',
        normalizeHexColor(widgetBackgroundColor, '#ffffff'),
      );
      src.searchParams.append(
        'widget_text_color',
        normalizeHexColor(widgetTextColor, '#111827'),
      );
      src.searchParams.append(
        'widget_header_text_color',
        normalizeHexColor(widgetHeaderTextColor, '#ffffff'),
      );
      src.searchParams.append(
        'widget_footer_text_color',
        normalizeHexColor(widgetFooterTextColor, '#6b7280'),
      );
    }

    if (!isEmpty(trim(userId))) {
      src.searchParams.append('userId', userId!);
    }

    return src.toString();
  }, [beta, from, token, values]);

  const text = useMemo(() => {
    const iframeSrc = generateIframeSrc();
    const { embedType } = values;

    if (embedType === 'widget') {
      const preset = values.widgetSizePreset || 'standard';
      let winWidth = '380px';
      let winHeight = '500px';
      if (preset === 'compact') {
        winWidth = '340px';
        winHeight = '450px';
      } else if (preset === 'large') {
        winWidth = '420px';
        winHeight = '580px';
      }

      return `<iframe
  id="chat-btn"
  src="${iframeSrc}"
  style="position:fixed;bottom:0;right:0;width:100px;height:100px;border:none;background:transparent;z-index:9999"
  frameborder="0"
  allow="microphone;camera"
></iframe>
<script>
window.addEventListener('message',e=>{
  if(e.origin!=='${location.origin}'&&e.origin!=='${location.origin.replace(/:\d+/, ':9222')}')return;
  if(e.data.type==='CREATE_CHAT_WINDOW'){
    if(document.getElementById('chat-win'))return;
    const i=document.createElement('iframe');
    i.id='chat-win';i.src=e.data.src;
    const isMob=Boolean(e.data.isMobile)||(typeof window!=='undefined'&&window.innerWidth<=640)||/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    i.style.cssText=isMob
      ?'position:fixed;top:0;left:0;right:0;bottom:0;width:100%;height:100%;height:100dvh;border:none;background:transparent;z-index:999999;display:none;border-radius:0'
      :'position:fixed;bottom:104px;right:24px;width:${winWidth};max-width:calc(100vw - 48px);height:${winHeight};max-height:calc(100vh - 128px);border:none;background:transparent;z-index:9998;display:none';
    i.frameBorder='0';i.allow='microphone;camera';
    document.body.appendChild(i);
  }else if(e.data.type==='TOGGLE_CHAT'){
    const w=document.getElementById('chat-win');
    if(w){
      w.style.display=e.data.isOpen?'block':'none';
      if(!e.data.isOpen&&window.__chat_prev_overflow!==undefined){
        document.body.style.overflow=window.__chat_prev_overflow;
        delete window.__chat_prev_overflow;
      }
    }
    const b=document.getElementById('chat-btn')||document.querySelector('iframe[src*="mode=master"]');
    if(b&&b.contentWindow&&b.contentWindow!==e.source){
      b.contentWindow.postMessage(e.data,'*');
    }
    if(w&&w.contentWindow&&w.contentWindow!==e.source){
      w.contentWindow.postMessage(e.data,'*');
    }
  }else if(e.data.type==='SET_FULLSCREEN'){
    const w=document.getElementById('chat-win');
    if(e.data.isFullscreen){
      if(window.__chat_prev_overflow===undefined){
        window.__chat_prev_overflow=document.body.style.overflow||'';
      }
      document.body.style.overflow='hidden';
      if(w){
        w.style.top='0';w.style.left='0';w.style.right='0';w.style.bottom='0';
        w.style.width='100%';w.style.height='100%';w.style.height='100dvh';
        w.style.maxWidth='';w.style.maxHeight='';
        w.style.borderRadius='0';w.style.zIndex='999999';
      }
    }else{
      if(window.__chat_prev_overflow!==undefined){
        document.body.style.overflow=window.__chat_prev_overflow;
        delete window.__chat_prev_overflow;
      }
      if(w){
        w.style.top='';w.style.left='';w.style.bottom='104px';w.style.right='24px';
        w.style.width='${winWidth}';w.style.height='${winHeight}';
        w.style.maxWidth='calc(100vw - 48px)';w.style.maxHeight='calc(100vh - 128px)';
        w.style.borderRadius='';w.style.zIndex='9998';
      }
    }
  }else if(e.data.type==='RESIZE_CHAT_WINDOW'){
    const isMob=Boolean(e.data.isMobile)||(typeof window!=='undefined'&&window.innerWidth<=640)||/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    if(isMob)return;
    const w=document.getElementById('chat-win');
    if(w&&window.__chat_prev_overflow===undefined){
      if(e.data.width)w.style.width=e.data.width;
      if(e.data.height)w.style.height=e.data.height;
      if(e.data.maxWidth)w.style.maxWidth=e.data.maxWidth;
      if(e.data.maxHeight)w.style.maxHeight=e.data.maxHeight;
      if(e.data.bottom)w.style.bottom=e.data.bottom;
      if(e.data.right)w.style.right=e.data.right;
    }
  }else if(e.data.type==='SCROLL_PASSTHROUGH')window.scrollBy(0,e.data.deltaY);
});
</script>
`;
    } else {
      const width = values.iframeWidth || '100%';
      const height = values.iframeHeight || '650px';
      const radius = values.iframeRadius || '12px';
      return `<iframe
  src="${iframeSrc}"
  style="width: ${width}; height: ${height}; min-height: 500px; border-radius: ${radius}; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 4px 20px rgba(0,0,0,0.05);"
  frameborder="0"
  allow="microphone;camera"
></iframe>
`;
    }
  }, [generateIframeSrc, values]);

  const handleOpenInNewTab = useCallback(() => {
    const iframeSrc = generateIframeSrc();
    window.open(iframeSrc, '_blank');
  }, [generateIframeSrc]);

  const handleSaveWidgetSettings = useCallback(async () => {
    if (!onSaveWidgetSettings) {
      return;
    }

    await onSaveWidgetSettings({
      enableStreaming: values.enableStreaming,
      muteWidget: values.muteWidget,
      widgetTitle: values.widgetTitle,
      widgetSubtitle: values.widgetSubtitle,
      widgetFooterText: 'Powered by Swipies.app',
      widgetFooterLink: 'https://swipies.app',
      widgetAccentColor: normalizeHexColor(values.widgetAccentColor, '#2563eb'),
      widgetBackgroundColor: normalizeHexColor(
        values.widgetBackgroundColor,
        '#ffffff',
      ),
      widgetTextColor: normalizeHexColor(values.widgetTextColor, '#111827'),
      widgetHeaderTextColor: normalizeHexColor(
        values.widgetHeaderTextColor,
        '#ffffff',
      ),
      widgetFooterTextColor: normalizeHexColor(
        values.widgetFooterTextColor,
        '#6b7280',
      ),
      iframeWidth: values.iframeWidth,
      iframeHeight: values.iframeHeight,
      iframeRadius: values.iframeRadius,
      widgetSizePreset: values.widgetSizePreset,
    });
  }, [onSaveWidgetSettings, values]);

  const applyColorPreset = useCallback(
    (preset: (typeof COLOR_PRESETS)[0]) => {
      form.setValue('widgetAccentColor', preset.accent, { shouldDirty: true });
      form.setValue('widgetBackgroundColor', preset.bg, { shouldDirty: true });
      form.setValue('widgetTextColor', preset.text, { shouldDirty: true });
      form.setValue('widgetHeaderTextColor', preset.headerText, {
        shouldDirty: true,
      });
      form.setValue('widgetFooterTextColor', preset.footerText, {
        shouldDirty: true,
      });
    },
    [form],
  );

  return (
    <Dialog open={visible} onOpenChange={hideModal}>
      <DialogContent className="sm:max-w-4xl max-h-[90vh] flex flex-col p-6 overflow-hidden">
        <DialogHeader className="flex-shrink-0 pb-2">
          <DialogTitle className="text-xl font-bold flex items-center gap-2">
            <Sparkles className="size-5 text-primary" />
            {t('common.embedIntoSite')}
          </DialogTitle>
        </DialogHeader>

        <section className="w-full flex-1 overflow-y-auto pr-1 space-y-6 text-sm text-text-secondary">
          <Form {...form}>
            <form className="space-y-6">
              <Tabs defaultValue="embed" className="w-full">
                <TabsList className="grid w-full grid-cols-2 mb-4">
                  <TabsTrigger
                    value="embed"
                    className="flex items-center gap-2 font-medium"
                  >
                    <Code className="size-4" />
                    Embed Setup & Code
                  </TabsTrigger>
                  <TabsTrigger
                    value="widget"
                    className="flex items-center gap-2 font-medium"
                  >
                    <Palette className="size-4" />
                    Customization & Colors
                  </TabsTrigger>
                </TabsList>

                {/* Tab 1: Embed Setup & Code */}
                <TabsContent value="embed" className="space-y-5">
                  <FormField
                    control={form.control}
                    name="embedType"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-semibold text-foreground">
                          {t('chat.embedType')}
                        </FormLabel>
                        <FormControl>
                          <RadioGroup
                            onValueChange={field.onChange}
                            value={field.value}
                            className="grid grid-cols-1 sm:grid-cols-2 gap-3"
                          >
                            <Label
                              htmlFor="fullscreen"
                              className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
                                field.value === 'fullscreen'
                                  ? 'border-primary bg-primary/5 shadow-sm'
                                  : 'border-border hover:border-border/80'
                              }`}
                            >
                              <RadioGroupItem
                                value="fullscreen"
                                id="fullscreen"
                                className="mt-1"
                              />
                              <div className="space-y-1">
                                <div className="font-semibold text-foreground flex items-center gap-1.5">
                                  <Monitor className="size-4 text-primary" />
                                  {t('chat.fullscreenChat')}
                                </div>
                                <div className="text-xs text-muted-foreground leading-normal">
                                  Full-height embed container with header,
                                  messages, and footer.
                                </div>
                              </div>
                            </Label>

                            <Label
                              htmlFor="widget"
                              className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
                                field.value === 'widget'
                                  ? 'border-primary bg-primary/5 shadow-sm'
                                  : 'border-border hover:border-border/80'
                              }`}
                            >
                              <RadioGroupItem
                                value="widget"
                                id="widget"
                                className="mt-1"
                              />
                              <div className="space-y-1">
                                <div className="font-semibold text-foreground flex items-center gap-1.5">
                                  <MessageSquare className="size-4 text-primary" />
                                  {t('chat.floatingWidget')}
                                </div>
                                <div className="text-xs text-muted-foreground leading-normal">
                                  Floating launcher bubble with expandable chat
                                  window.
                                </div>
                              </div>
                            </Label>
                          </RadioGroup>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Sizing controls based on embed type */}
                  {values.embedType === 'fullscreen' ? (
                    <div className="rounded-xl border border-border/70 bg-card p-4 space-y-3">
                      <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        Iframe Dimensions & Sizing
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <RAGFlowFormItem name="iframeWidth" label="Width">
                          <Input placeholder="100% (e.g. 100%, 800px)" />
                        </RAGFlowFormItem>
                        <RAGFlowFormItem name="iframeHeight" label="Height">
                          <Input placeholder="650px (e.g. 650px, 100%)" />
                        </RAGFlowFormItem>
                        <RAGFlowFormItem
                          name="iframeRadius"
                          label="Border radius"
                        >
                          <Input placeholder="12px (e.g. 12px, 0px)" />
                        </RAGFlowFormItem>
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-xl border border-border/70 bg-card p-4 space-y-3">
                      <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        Floating Widget Size Preset
                      </div>
                      <FormField
                        control={form.control}
                        name="widgetSizePreset"
                        render={({ field }) => (
                          <div className="grid grid-cols-3 gap-2">
                            {[
                              {
                                id: 'compact',
                                name: 'Compact',
                                desc: '340 × 450 px',
                              },
                              {
                                id: 'standard',
                                name: 'Standard',
                                desc: '380 × 500 px',
                              },
                              {
                                id: 'large',
                                name: 'Spacious',
                                desc: '420 × 580 px',
                              },
                            ].map((p) => (
                              <button
                                key={p.id}
                                type="button"
                                onClick={() => field.onChange(p.id)}
                                className={`p-2.5 rounded-lg border text-left transition-all ${
                                  field.value === p.id ||
                                  (!field.value && p.id === 'standard')
                                    ? 'border-primary bg-primary/10 text-primary font-medium'
                                    : 'border-border/60 hover:bg-muted/50 text-foreground'
                                }`}
                              >
                                <div className="text-xs font-semibold">
                                  {p.name}
                                </div>
                                <div className="text-[11px] text-muted-foreground">
                                  {p.desc}
                                </div>
                              </button>
                            ))}
                          </div>
                        )}
                      />
                    </div>
                  )}

                  {/* Theme & Switches */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
                    {values.embedType === 'fullscreen' && (
                      <FormField
                        control={form.control}
                        name="theme"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>{t('chat.theme')}</FormLabel>
                            <FormControl>
                              <RadioGroup
                                onValueChange={field.onChange}
                                value={field.value}
                                className="flex flex-row space-x-4 pt-1"
                              >
                                <div className="flex items-center space-x-2">
                                  <RadioGroupItem
                                    value={ThemeEnum.Light}
                                    id="light"
                                  />
                                  <Label
                                    htmlFor="light"
                                    className="text-sm cursor-pointer"
                                  >
                                    {t('chat.light')}
                                  </Label>
                                </div>
                                <div className="flex items-center space-x-2">
                                  <RadioGroupItem
                                    value={ThemeEnum.Dark}
                                    id="dark"
                                  />
                                  <Label
                                    htmlFor="dark"
                                    className="text-sm cursor-pointer"
                                  >
                                    {t('chat.dark')}
                                  </Label>
                                </div>
                              </RadioGroup>
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    )}

                    <SwitchFormField
                      name="visibleAvatar"
                      label={t('chat.avatarHidden')}
                    />

                    {isAgent && (
                      <SwitchFormField
                        name="published"
                        label={t('chat.published')}
                        tooltip={t('chat.publishedTooltip')}
                      />
                    )}

                    {values.embedType === 'widget' && (
                      <>
                        <SwitchFormField
                          name="enableStreaming"
                          label={t('chat.enableStreaming')}
                        />
                        <SwitchFormField
                          name="muteWidget"
                          label={t('chat.muteWidget')}
                        />
                      </>
                    )}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <RAGFlowFormItem name="locale" label={t('chat.locale')}>
                      <SelectWithSearch options={languageOptions} />
                    </RAGFlowFormItem>
                    {isAgent && (
                      <RAGFlowFormItem name="userId" label={t('flow.userId')}>
                        <Input />
                      </RAGFlowFormItem>
                    )}
                  </div>
                </TabsContent>

                {/* Tab 2: Customization & Colors */}
                <TabsContent value="widget" className="space-y-5">
                  {/* Permanent Verified Branding Card (Locked) */}
                  <div className="rounded-xl border border-border/80 bg-muted/30 p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="p-1.5 rounded-md bg-primary/10 text-primary">
                          <Lock className="size-4" />
                        </div>
                        <span className="font-semibold text-sm text-foreground">
                          Permanent Branding Attribution
                        </span>
                      </div>
                      <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold border border-emerald-500/20">
                        Permanent • Verified
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      <div className="bg-background rounded-lg p-2.5 border border-border/50">
                        <span className="text-muted-foreground block mb-0.5 font-medium">
                          Footer Text
                        </span>
                        <span className="font-semibold text-foreground text-sm">
                          Powered by Swipies.app
                        </span>
                      </div>
                      <div className="bg-background rounded-lg p-2.5 border border-border/50">
                        <span className="text-muted-foreground block mb-0.5 font-medium">
                          Footer Redirect Link
                        </span>
                        <a
                          href="https://swipies.app"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-semibold text-primary hover:underline flex items-center gap-1 text-sm truncate"
                        >
                          <span>https://swipies.app</span>
                          <ExternalLink className="size-3 flex-shrink-0" />
                        </a>
                      </div>
                    </div>

                    <p className="text-[11px] text-muted-foreground leading-relaxed">
                      All embedded widgets and shared chats are permanently
                      powered by Swipies.app. Attribution links are locked to
                      ensure verified platform integrity.
                    </p>
                  </div>

                  {/* Header Title & Subtitle */}
                  <div className="grid gap-4 sm:grid-cols-2">
                    <RAGFlowFormItem name="widgetTitle" label="Widget title">
                      <Input placeholder="Chat Support" />
                    </RAGFlowFormItem>
                    <RAGFlowFormItem name="widgetSubtitle" label="Subtitle">
                      <Input placeholder="We typically reply instantly" />
                    </RAGFlowFormItem>
                  </div>

                  {/* Quick Color Theme Presets */}
                  <div className="space-y-2 pt-1">
                    <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Quick Color Presets
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
                      {COLOR_PRESETS.map((preset) => (
                        <button
                          key={preset.name}
                          type="button"
                          onClick={() => applyColorPreset(preset)}
                          className="flex items-center gap-2 p-2 rounded-lg border border-border/70 hover:border-primary bg-card hover:bg-muted/40 transition-all text-left"
                        >
                          <span
                            className="size-3.5 rounded-full flex-shrink-0 shadow-sm border border-white/20"
                            style={{ backgroundColor: preset.colorPreview }}
                          />
                          <span className="text-xs font-medium text-foreground truncate">
                            {preset.name}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Detailed Color Pickers */}
                  <div className="space-y-3 pt-1">
                    <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Custom Color Palette
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                      <FormField
                        control={form.control}
                        name="widgetAccentColor"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-xs font-medium">
                              Widget accent color
                            </FormLabel>
                            <FormControl>
                              <div className="flex items-center gap-2">
                                <Input
                                  type="color"
                                  value={normalizeHexColor(
                                    field.value,
                                    '#2563eb',
                                  )}
                                  onChange={field.onChange}
                                  className="h-9 w-12 p-0.5 cursor-pointer rounded-md border"
                                />
                                <Input
                                  {...field}
                                  className="font-mono text-xs"
                                />
                              </div>
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="widgetBackgroundColor"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-xs font-medium">
                              Background color
                            </FormLabel>
                            <FormControl>
                              <div className="flex items-center gap-2">
                                <Input
                                  type="color"
                                  value={normalizeHexColor(
                                    field.value,
                                    '#ffffff',
                                  )}
                                  onChange={field.onChange}
                                  className="h-9 w-12 p-0.5 cursor-pointer rounded-md border"
                                />
                                <Input
                                  {...field}
                                  className="font-mono text-xs"
                                />
                              </div>
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="widgetTextColor"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-xs font-medium">
                              Text color
                            </FormLabel>
                            <FormControl>
                              <div className="flex items-center gap-2">
                                <Input
                                  type="color"
                                  value={normalizeHexColor(
                                    field.value,
                                    '#111827',
                                  )}
                                  onChange={field.onChange}
                                  className="h-9 w-12 p-0.5 cursor-pointer rounded-md border"
                                />
                                <Input
                                  {...field}
                                  className="font-mono text-xs"
                                />
                              </div>
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="widgetHeaderTextColor"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-xs font-medium">
                              Header text color
                            </FormLabel>
                            <FormControl>
                              <div className="flex items-center gap-2">
                                <Input
                                  type="color"
                                  value={normalizeHexColor(
                                    field.value,
                                    '#ffffff',
                                  )}
                                  onChange={field.onChange}
                                  className="h-9 w-12 p-0.5 cursor-pointer rounded-md border"
                                />
                                <Input
                                  {...field}
                                  className="font-mono text-xs"
                                />
                              </div>
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="widgetFooterTextColor"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-xs font-medium">
                              Footer text color
                            </FormLabel>
                            <FormControl>
                              <div className="flex items-center gap-2">
                                <Input
                                  type="color"
                                  value={normalizeHexColor(
                                    field.value,
                                    '#6b7280',
                                  )}
                                  onChange={field.onChange}
                                  className="h-9 w-12 p-0.5 cursor-pointer rounded-md border"
                                />
                                <Input
                                  {...field}
                                  className="font-mono text-xs"
                                />
                              </div>
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </form>
          </Form>

          {/* Embed Code Snippet */}
          <div className="space-y-2 pt-2 border-t border-border/50">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-sm text-foreground">
                {t('search.embedCode')}
              </span>
              <span className="text-xs text-muted-foreground">
                Copy and paste this snippet into your HTML website
              </span>
            </div>
            <div className="relative rounded-xl overflow-hidden border border-border/80">
              <CopyToClipboard
                text={text}
                className="absolute right-3 top-3 z-10 border border-border bg-background/90 backdrop-blur-sm shadow-sm"
              />
              <SyntaxHighlighter
                className="max-h-[220px] overflow-auto scrollbar-auto pr-14 text-xs font-mono"
                language="html"
                style={isDarkTheme ? oneDark : oneLight}
              >
                {text}
              </SyntaxHighlighter>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3 pt-1">
            {isAgent && onSaveWidgetSettings && (
              <ButtonLoading
                onClick={handleSaveWidgetSettings}
                loading={savingWidgetSettings}
                className="flex-1"
                variant="default"
              >
                {t('flow.save')} widget settings
              </ButtonLoading>
            )}
            <Button
              onClick={handleOpenInNewTab}
              className={isAgent && onSaveWidgetSettings ? 'flex-1' : 'w-full'}
              variant="secondary"
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              {t('common.openInNewTab')}
            </Button>
          </div>

          {/* Chat ID Badge & API Documentation */}
          <div className="rounded-xl border border-border/70 bg-card p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                {t(isAgent ? 'flow' : 'chat', { keyPrefix: 'header' })} ID
              </span>
              <a
                className="cursor-pointer text-xs text-primary hover:underline inline-flex items-center gap-1"
                href={
                  isAgent
                    ? 'https://docs.swipies.app/docs/http_api_reference#create-session-with-agent'
                    : 'https://docs.swipies.app/docs/http_api_reference#create-session-with-chat-assistant'
                }
                target="_blank"
                rel="noreferrer"
              >
                <span>{t(`${isAgent ? 'flow' : 'chat'}.howUseId`)}</span>
                <ExternalLink className="size-3" />
              </a>
            </div>
            <div className="bg-muted/50 rounded-lg flex items-center justify-between p-2.5 font-mono text-xs text-foreground border border-border/40">
              <span className="truncate mr-2">{token}</span>
              <CopyToClipboard text={token} />
            </div>
          </div>
        </section>
      </DialogContent>
    </Dialog>
  );
}

export default memo(EmbedDialog);
