import React from 'react';
import {
  Settings,
  Save,
  Building2,
  CheckCircle2,
  Check,
  Copy,
  Target,
  ShieldCheck,
  BellRing,
  Send,
  FileText,
  Webhook,
  Radio,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AdvertiserSettingsData,
  NotificationSettingsData,
} from '@/services/ad-service';
import { AdLanguage, translateAdText } from '../translations';

export interface SettingsTabProps {
  advSettings: AdvertiserSettingsData;
  onUpdateAdvSettings: (settings: AdvertiserSettingsData) => void;
  notifSettings: NotificationSettingsData | null;
  onUpdateNotifSettings: (
    settings: NotificationSettingsData | null | ((prev: NotificationSettingsData | null) => NotificationSettingsData | null),
  ) => void;
  isSavingAdvSettings: boolean;
  onSaveAdvSettings: () => void;
  copiedPixelSuccess: boolean;
  onCopyPixelId: () => void;
  onToggleDefaultRegion?: (code: string) => void;
  onToggleDefaultModel?: (model: string) => void;
  currentLang: AdLanguage;
  onLanguageChange: (lang: AdLanguage) => void;
  testingNotifChannel: string | null;
  onSendTestNotification: (channel: string) => void;
  t?: (keyOrText: string, fallback?: string) => string;
}

export const SettingsTab: React.FC<SettingsTabProps> = ({
  advSettings,
  onUpdateAdvSettings,
  notifSettings,
  onUpdateNotifSettings,
  isSavingAdvSettings,
  onSaveAdvSettings,
  copiedPixelSuccess,
  onCopyPixelId,
  onToggleDefaultRegion,
  onToggleDefaultModel,
  currentLang,
  onLanguageChange,
  testingNotifChannel,
  onSendTestNotification,
  t: customT,
}) => {
  const t = (keyOrText: string, fallback?: string): string => {
    if (customT) return customT(keyOrText, fallback);
    return translateAdText(keyOrText, currentLang, fallback);
  };

  const toggleDefaultRegion = (code: string) => {
    if (onToggleDefaultRegion) {
      onToggleDefaultRegion(code);
      return;
    }
    const current = advSettings?.default_regions || [];
    const updated = current.includes(code)
      ? current.filter((r) => r !== code)
      : [...current, code];
    onUpdateAdvSettings({ ...advSettings, default_regions: updated.length ? updated : [code] });
  };

  const toggleDefaultModel = (model: string) => {
    if (onToggleDefaultModel) {
      onToggleDefaultModel(model);
      return;
    }
    const current = advSettings?.default_models || [];
    const updated = current.includes(model)
      ? current.filter((m) => m !== model)
      : [...current, model];
    onUpdateAdvSettings({ ...advSettings, default_models: updated.length ? updated : [model] });
  };

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <Card className="bg-gradient-to-r from-blue-500/10 via-indigo-500/5 to-transparent border-blue-500/20">
        <CardHeader className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 mt-0.5">
              <Settings className="h-6 w-6" />
            </div>
            <div>
              <CardTitle className="text-xl font-bold">{t('settingsHeaderTitle')}</CardTitle>
              <CardDescription className="text-sm mt-1">
                {t('settingsHeaderSubtitle')}
              </CardDescription>
            </div>
          </div>
          <Button
            onClick={onSaveAdvSettings}
            disabled={isSavingAdvSettings}
            aria-label={isSavingAdvSettings ? t('savingChangesBtn') : t('saveChangesBtn')}
            className="bg-blue-600 hover:bg-blue-700 text-white shrink-0 shadow-sm"
          >
            <Save className={`mr-2 h-4 w-4 ${isSavingAdvSettings ? 'animate-spin' : ''}`} />
            {isSavingAdvSettings ? t('savingChangesBtn') : t('saveChangesBtn')}
          </Button>
        </CardHeader>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Card 1: Advertiser Profile */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-blue-500" />
              <CardTitle className="text-base">{t('profileSectionTitle')}</CardTitle>
            </div>
            <CardDescription className="text-xs">
              {t('profileSectionDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">{t('companyNameLabel')}</label>
              <Input
                placeholder="Swipies AI Corp"
                value={advSettings?.company_name || ''}
                onChange={(e) => onUpdateAdvSettings({ ...advSettings, company_name: e.target.value })}
                className="h-9 text-xs"
                aria-label={t('companyNameLabel')}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">{t('contactEmailLabel')}</label>
              <Input
                placeholder="advertiser@example.com"
                type="email"
                value={advSettings?.contact_email || ''}
                onChange={(e) => onUpdateAdvSettings({ ...advSettings, contact_email: e.target.value })}
                className="h-9 text-xs"
                aria-label={t('contactEmailLabel')}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">{t('websiteUrlLabel')}</label>
              <Input
                placeholder="https://mybrand.com"
                value={advSettings?.website_url || ''}
                onChange={(e) => onUpdateAdvSettings({ ...advSettings, website_url: e.target.value })}
                className="h-9 text-xs"
                aria-label={t('websiteUrlLabel')}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">{t('billingCurrencyLabel')}</label>
                <Select
                  value={advSettings?.currency || 'USD'}
                  onValueChange={(val) => onUpdateAdvSettings({ ...advSettings, currency: val })}
                >
                  <SelectTrigger className="h-9 text-xs" aria-label={t('billingCurrencyLabel')}>
                    <SelectValue placeholder="USD" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USD">USD ($ - US Dollar)</SelectItem>
                    <SelectItem value="UZS">UZS (So'm - O'zbekiston)</SelectItem>
                    <SelectItem value="RUB">RUB (₽ - Российский рубль)</SelectItem>
                    <SelectItem value="EUR">EUR (€ - Euro)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">{t('accountStatusLabel')}</label>
                <div className="h-9 flex items-center">
                  <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 text-xs">
                    <CheckCircle2 className="mr-1 h-3.5 w-3.5" /> {t('accountActiveBadge')}
                  </Badge>
                </div>
              </div>
            </div>

            <div className="space-y-1.5 pt-1 border-t">
              <label className="text-xs font-medium text-foreground">{t('pixelIdLabel')}</label>
              <div className="flex items-center gap-2">
                <Input
                  readOnly
                  value={advSettings?.pixel_id || 'px_swipies_live'}
                  className="h-9 text-xs font-mono bg-muted/40"
                  aria-label={t('pixelIdLabel')}
                />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={onCopyPixelId}
                  className="h-9 shrink-0 gap-1 text-xs"
                  aria-label={t('copyPixelBtn')}
                >
                  {copiedPixelSuccess ? (
                    <Check className="h-3.5 w-3.5 text-emerald-600" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                  {t('copyPixelBtn')}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Card 2: Default Targeting Preferences */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Target className="h-5 w-5 text-purple-500" />
              <CardTitle className="text-base">{t('defaultsSectionTitle')}</CardTitle>
            </div>
            <CardDescription className="text-xs">
              {t('defaultsSectionDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">{t('defaultLangLabel')}</label>
                <Select
                  value={advSettings?.language || currentLang}
                  onValueChange={(val) => {
                    onLanguageChange(val as AdLanguage);
                  }}
                >
                  <SelectTrigger className="h-9 text-xs" aria-label={t('defaultLangLabel')}>
                    <SelectValue placeholder="Русский" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ru">Русский (RU)</SelectItem>
                    <SelectItem value="en">English (EN)</SelectItem>
                    <SelectItem value="uz">O'zbekcha (UZ)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">{t('timezoneLabel')}</label>
                <Select
                  value={advSettings?.timezone || 'Asia/Tashkent'}
                  onValueChange={(val) => onUpdateAdvSettings({ ...advSettings, timezone: val })}
                >
                  <SelectTrigger className="h-9 text-xs" aria-label={t('timezoneLabel')}>
                    <SelectValue placeholder="Asia/Tashkent" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Asia/Tashkent">Asia/Tashkent (UTC+5)</SelectItem>
                    <SelectItem value="Europe/Moscow">Europe/Moscow (UTC+3)</SelectItem>
                    <SelectItem value="UTC">UTC (UTC+0)</SelectItem>
                    <SelectItem value="America/New_York">America/New_York (EST)</SelectItem>
                    <SelectItem value="Asia/Almaty">Asia/Almaty (UTC+5)</SelectItem>
                    <SelectItem value="Asia/Dubai">Asia/Dubai (UTC+4)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2 pt-1">
              <label className="text-xs font-medium text-foreground block">
                {t('defaultRegionsLabel')}
              </label>
              <div className="flex flex-wrap gap-1.5">
                {[
                  { code: 'UZ', label: '🇺🇿 Uzbekistan' },
                  { code: 'RU', label: '🇷🇺 Russia' },
                  { code: 'KZ', label: '🇰🇿 Kazakhstan' },
                  { code: 'US', label: '🇺🇸 United States' },
                  { code: 'EU', label: '🇪🇺 European Union' },
                  { code: 'AE', label: '🇦🇪 UAE' },
                  { code: 'TR', label: '🇹🇷 Turkey' },
                ].map((reg) => {
                  const isSelected = (advSettings?.default_regions || []).includes(reg.code);
                  return (
                    <button
                      key={reg.code}
                      type="button"
                      onClick={() => toggleDefaultRegion(reg.code)}
                      className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all cursor-pointer border ${
                        isSelected
                          ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                          : 'bg-muted/40 text-muted-foreground border-border hover:bg-muted/70 hover:text-foreground'
                      }`}
                    >
                      {reg.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="space-y-2 pt-2 border-t">
              <label className="text-xs font-medium text-foreground block">
                {t('defaultModelsLabel')}
              </label>
              <div className="flex flex-wrap gap-1.5">
                {[
                  { id: 'gpt-4o', label: 'GPT-4o' },
                  { id: 'claude-3-5-sonnet', label: 'Claude 3.5 Sonnet' },
                  { id: 'deepseek-v3', label: 'DeepSeek V3' },
                  { id: 'llama-3-70b', label: 'Llama 3 (70B)' },
                  { id: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
                ].map((mod) => {
                  const isSelected = (advSettings?.default_models || []).includes(mod.id);
                  return (
                    <button
                      key={mod.id}
                      type="button"
                      onClick={() => toggleDefaultModel(mod.id)}
                      className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all cursor-pointer border ${
                        isSelected
                          ? 'bg-purple-600 text-white border-purple-600 shadow-xs'
                          : 'bg-muted/40 text-muted-foreground border-border hover:bg-muted/70 hover:text-foreground'
                      }`}
                    >
                      {mod.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Card 3: Safety Caps & Spend Controls */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-emerald-500" />
              <CardTitle className="text-base">{t('safetySectionTitle')}</CardTitle>
            </div>
            <CardDescription className="text-xs">
              {t('safetySectionDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-foreground">{t('dailySpendCeilingLabel')}</label>
                <span className="text-[11px] font-mono text-emerald-600 font-semibold">
                  ${advSettings?.daily_spend_ceiling ?? 50} / day
                </span>
              </div>
              <Input
                type="number"
                min="1"
                step="10"
                value={advSettings?.daily_spend_ceiling ?? 50}
                onChange={(e) =>
                  onUpdateAdvSettings({ ...advSettings, daily_spend_ceiling: parseFloat(e.target.value) || 0 })
                }
                className="h-9 text-xs"
                aria-label={t('dailySpendCeilingLabel')}
              />
              <p className="text-[11px] text-muted-foreground">{t('dailySpendCeilingDesc')}</p>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">{t('frequencyCapLabel')}</label>
              <Input
                type="number"
                min="1"
                max="20"
                value={advSettings?.default_frequency_cap ?? 3}
                onChange={(e) =>
                  onUpdateAdvSettings({ ...advSettings, default_frequency_cap: parseInt(e.target.value) || 1 })
                }
                className="h-9 text-xs"
                aria-label={t('frequencyCapLabel')}
              />
            </div>

            <div className="rounded-lg border p-3 bg-muted/20 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-foreground">{t('autoPauseLowCtrLabel')}</div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">
                    {t('safetySectionDesc')}
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={advSettings?.auto_pause_low_ctr || false}
                  onChange={(e) =>
                    onUpdateAdvSettings({ ...advSettings, auto_pause_low_ctr: e.target.checked })
                  }
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  aria-label={t('autoPauseLowCtrLabel')}
                />
              </div>

              {advSettings?.auto_pause_low_ctr && (
                <div className="pt-2 border-t space-y-1.5">
                  <label className="text-[11px] text-muted-foreground">{t('lowCtrThresholdLabel')}</label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0.05"
                    max="10"
                    value={advSettings?.low_ctr_threshold ?? 0.5}
                    onChange={(e) =>
                      onUpdateAdvSettings({ ...advSettings, low_ctr_threshold: parseFloat(e.target.value) || 0 })
                    }
                    className="h-8 text-xs font-mono"
                    aria-label={t('lowCtrThresholdLabel')}
                  />
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Card 4: Notification Channels & Alerts */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <BellRing className="h-5 w-5 text-amber-500" />
              <CardTitle className="text-base">{t('notifSectionTitle')}</CardTitle>
            </div>
            <CardDescription className="text-xs">
              {t('notifSectionDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Telegram Alert */}
            <div className="rounded-lg border p-3 bg-muted/20 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold flex items-center gap-1.5">
                  <Send className="h-3.5 w-3.5 text-sky-500" /> {t('telegramAlertsLabel')}
                </span>
                <input
                  type="checkbox"
                  checked={notifSettings?.telegram_alerts_enabled || false}
                  onChange={(e) =>
                    onUpdateNotifSettings(
                      notifSettings ? { ...notifSettings, telegram_alerts_enabled: e.target.checked } : null,
                    )
                  }
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  aria-label={t('telegramAlertsLabel')}
                />
              </div>
              <Input
                placeholder="123456789"
                value={notifSettings?.telegram_chat_id || ''}
                onChange={(e) =>
                  onUpdateNotifSettings(
                    notifSettings ? { ...notifSettings, telegram_chat_id: e.target.value } : null,
                  )
                }
                className="h-8 text-xs font-mono"
                aria-label={t('telegramAlertsLabel')}
              />
            </div>

            {/* Email Alert */}
            <div className="rounded-lg border p-3 bg-muted/20 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5 text-blue-500" /> {t('emailAlertsLabel')}
                </span>
                <input
                  type="checkbox"
                  checked={notifSettings?.email_alerts_enabled || false}
                  onChange={(e) =>
                    onUpdateNotifSettings(
                      notifSettings ? { ...notifSettings, email_alerts_enabled: e.target.checked } : null,
                    )
                  }
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  aria-label={t('emailAlertsLabel')}
                />
              </div>
              <Input
                placeholder="alerts@company.com"
                value={notifSettings?.email_target || ''}
                onChange={(e) =>
                  onUpdateNotifSettings(
                    notifSettings ? { ...notifSettings, email_target: e.target.value } : null,
                  )
                }
                className="h-8 text-xs"
                aria-label={t('emailAlertsLabel')}
              />
            </div>

            {/* Webhook Alert */}
            <div className="rounded-lg border p-3 bg-muted/20 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold flex items-center gap-1.5">
                  <Webhook className="h-3.5 w-3.5 text-purple-500" /> {t('webhookAlertsLabel')}
                </span>
                <input
                  type="checkbox"
                  checked={Boolean(notifSettings?.webhook_url)}
                  onChange={(e) => {
                    if (!e.target.checked) {
                      onUpdateNotifSettings(notifSettings ? { ...notifSettings, webhook_url: '' } : null);
                    }
                  }}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  aria-label={t('webhookAlertsLabel')}
                />
              </div>
              <Input
                placeholder="https://api.mybrand.com/swipies-webhook"
                value={notifSettings?.webhook_url || ''}
                onChange={(e) =>
                  onUpdateNotifSettings(
                    notifSettings ? { ...notifSettings, webhook_url: e.target.value } : null,
                  )
                }
                className="h-8 text-xs font-mono"
                aria-label={t('webhookAlertsLabel')}
              />
            </div>

            {/* Test Alert Button */}
            <div className="pt-2 flex items-center justify-between">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={testingNotifChannel !== null}
                onClick={() => onSendTestNotification('all')}
                className="text-xs gap-1.5"
                aria-label={t('sendTestAlertBtn')}
              >
                <Radio className={`h-3.5 w-3.5 ${testingNotifChannel ? 'animate-pulse text-amber-500' : ''}`} />
                {t('sendTestAlertBtn')}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Bottom Action Card */}
      <div className="flex items-center justify-end gap-3 pt-2">
        <Button
          onClick={onSaveAdvSettings}
          disabled={isSavingAdvSettings}
          aria-label={isSavingAdvSettings ? t('savingChangesBtn') : t('saveChangesBtn')}
          className="bg-blue-600 hover:bg-blue-700 text-white shadow-sm px-6"
        >
          <Save className={`mr-2 h-4 w-4 ${isSavingAdvSettings ? 'animate-spin' : ''}`} />
          {isSavingAdvSettings ? t('savingChangesBtn') : t('saveChangesBtn')}
        </Button>
      </div>
    </div>
  );
};

export default SettingsTab;
