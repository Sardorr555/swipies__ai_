import { AD_TRANSLATIONS, AdLanguage } from '../../pages/ads/translations';
import adService from '../../services/ad-service';

describe('Swipies Ads Localization & Settings Test Suite', () => {
  const languages: AdLanguage[] = ['ru', 'en', 'uz'];

  describe('AD_TRANSLATIONS Multi-Language Parity', () => {
    it('contains configurations for all supported languages: ru, en, uz', () => {
      expect(AD_TRANSLATIONS).toBeDefined();
      expect(AD_TRANSLATIONS.ru).toBeDefined();
      expect(AD_TRANSLATIONS.en).toBeDefined();
      expect(AD_TRANSLATIONS.uz).toBeDefined();
    });

    it('all languages have identical key sets to avoid missing translation strings', () => {
      const ruKeys = Object.keys(AD_TRANSLATIONS.ru).sort();
      const enKeys = Object.keys(AD_TRANSLATIONS.en).sort();
      const uzKeys = Object.keys(AD_TRANSLATIONS.uz).sort();

      expect(enKeys).toEqual(ruKeys);
      expect(uzKeys).toEqual(ruKeys);
    });

    it('validates non-empty translations for core header elements', () => {
      languages.forEach((lang) => {
        const dict = AD_TRANSLATIONS[lang];
        expect(dict.pageTitle).toBe('Swipies Ads');
        expect(dict.aiIntentBadge.length).toBeGreaterThan(3);
        expect(dict.pageSubtitle.length).toBeGreaterThan(15);
        expect(dict.availableBalance.length).toBeGreaterThan(3);
        expect(dict.topUpBtn.length).toBeGreaterThan(2);
        expect(dict.pixelBtn.length).toBeGreaterThan(3);
        expect(dict.newCampaignBtn.length).toBeGreaterThan(3);
        expect(dict.settingsBtn.length).toBeGreaterThan(3);
      });
    });

    it('validates all 15 tab trigger titles across ru, en, uz', () => {
      const tabKeys = [
        'tabCampaigns',
        'tabStudio',
        'tabInsights',
        'tabAutopilot',
        'tabAttribution',
        'tabAnalytics',
        'tabBilling',
        'tabAudiences',
        'tabTeam',
        'tabPublisher',
        'tabFraud',
        'tabAgency',
        'tabOmnichannel',
        'tabGuide',
        'tabSettings',
      ];

      languages.forEach((lang) => {
        const dict = AD_TRANSLATIONS[lang];
        tabKeys.forEach((k) => {
          expect(dict[k]).toBeDefined();
          expect(dict[k].length).toBeGreaterThan(1);
        });
      });
    });

    it('verifies settings tab translations in Russian', () => {
      const ru = AD_TRANSLATIONS.ru;
      expect(ru.settingsHeaderTitle).toBe('Настройки рекламодателя');
      expect(ru.companyNameLabel).toBe('Название компании / Бренда');
      expect(ru.dailySpendCeilingLabel).toContain('Дневной');
      expect(ru.autoPauseLowCtrLabel).toContain('CTR');
      expect(ru.telegramAlertsLabel).toContain('Telegram');
      expect(ru.saveChangesBtn).toBe('Сохранить настройки');
    });

    it('verifies settings tab translations in English', () => {
      const en = AD_TRANSLATIONS.en;
      expect(en.settingsHeaderTitle).toBe('Advertiser Settings');
      expect(en.companyNameLabel).toBe('Company / Brand Name');
      expect(en.dailySpendCeilingLabel).toContain('Daily Spend');
      expect(en.autoPauseLowCtrLabel).toContain('Auto-pause');
      expect(en.telegramAlertsLabel).toBe('Telegram Notifications');
      expect(en.saveChangesBtn).toBe('Save Settings');
    });

    it('verifies settings tab translations in Uzbek', () => {
      const uz = AD_TRANSLATIONS.uz;
      expect(uz.settingsHeaderTitle).toBe('Reklamachi sozlamalari');
      expect(uz.companyNameLabel).toBe('Kompaniya / Brend nomi');
      expect(uz.dailySpendCeilingLabel).toContain('Kunlik');
      expect(uz.autoPauseLowCtrLabel).toContain('CTR');
      expect(uz.telegramAlertsLabel).toBe('Telegram xabarnomalari');
      expect(uz.saveChangesBtn).toBe('Sozlamalarni saqlash');
    });
  });

  describe('AdService Advertiser Settings Methods', () => {
    it('exposes getAdvertiserSettings method', () => {
      expect(typeof adService.getAdvertiserSettings).toBe('function');
    });

    it('exposes updateAdvertiserSettings method', () => {
      expect(typeof adService.updateAdvertiserSettings).toBe('function');
    });
  });
});
