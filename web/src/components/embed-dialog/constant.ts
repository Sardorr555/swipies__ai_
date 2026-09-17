export interface WidgetSettings {
  enableStreaming: boolean;
  muteWidget: boolean;
  widgetTitle: string;
  widgetSubtitle: string;
  widgetFooterText: string;
  widgetFooterLink: string;
  widgetAccentColor: string;
  widgetBackgroundColor: string;
  widgetTextColor: string;
  widgetHeaderTextColor: string;
  widgetFooterTextColor: string;
  iframeWidth?: string;
  iframeHeight?: string;
  iframeRadius?: string;
  widgetSizePreset?: string;
}

export const defaultWidgetSettings: WidgetSettings = {
  enableStreaming: true,
  muteWidget: false,
  widgetTitle: '',
  widgetSubtitle: '',
  widgetFooterText: 'Powered by Swipies.app',
  widgetFooterLink: 'https://swipies.app',
  widgetAccentColor: '#2563eb',
  widgetBackgroundColor: '#ffffff',
  widgetTextColor: '#111827',
  widgetHeaderTextColor: '#ffffff',
  widgetFooterTextColor: '#6b7280',
  iframeWidth: '100%',
  iframeHeight: '650px',
  iframeRadius: '12px',
  widgetSizePreset: 'standard',
};
