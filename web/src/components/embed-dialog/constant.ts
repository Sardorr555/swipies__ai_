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
  widgetFooterTextColor: '#111827',
};
