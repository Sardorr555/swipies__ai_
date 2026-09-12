import { AD_TRANSLATIONS, AdLanguage, translateAdText } from '../../pages/ads/translations';
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

    it('verifies campaigns table headers and card translations across ru, en, uz', () => {
      expect(AD_TRANSLATIONS.ru.campaignsCardTitle).toBe('Ваши рекламные кампании');
      expect(AD_TRANSLATIONS.en.campaignsCardTitle).toBe('Your Advertising Campaigns');
      expect(AD_TRANSLATIONS.uz.campaignsCardTitle).toBe('Sizning reklama kampaniyalaringiz');

      expect(AD_TRANSLATIONS.ru.thCampaignProduct).toBe('Кампания / Продукт');
      expect(AD_TRANSLATIONS.en.thCampaignProduct).toBe('Campaign / Product');
      expect(AD_TRANSLATIONS.uz.thCampaignProduct).toBe('Kampaniya / Mahsulot');

      expect(AD_TRANSLATIONS.ru.thStatus).toBe('Статус');
      expect(AD_TRANSLATIONS.en.thStatus).toBe('Status');
      expect(AD_TRANSLATIONS.uz.thStatus).toBe('Holati');

      expect(AD_TRANSLATIONS.ru.statusActive).toBe('Активна');
      expect(AD_TRANSLATIONS.en.statusActive).toBe('Active');
      expect(AD_TRANSLATIONS.uz.statusActive).toBe('Faol');
    });

    it('verifies standalone top bar texts across ru, en, uz', () => {
      expect(AD_TRANSLATIONS.ru.standaloneBadge).toBe('Автономный сервис');
      expect(AD_TRANSLATIONS.en.standaloneBadge).toBe('Standalone Service');
      expect(AD_TRANSLATIONS.uz.standaloneBadge).toBe('Mustaqil xizmat');

      expect(AD_TRANSLATIONS.ru.unifiedDbBadge).toContain('Единая база');
      expect(AD_TRANSLATIONS.en.unifiedDbBadge).toContain('Unified database');
      expect(AD_TRANSLATIONS.uz.unifiedDbBadge).toContain('Yagona');

      expect(AD_TRANSLATIONS.ru.backToMainApp).toContain('Swipies AI');
      expect(AD_TRANSLATIONS.en.backToMainApp).toBe('Back to Swipies AI');
      expect(AD_TRANSLATIONS.uz.backToMainApp).toContain('Swipies AI');
    });

    it('verifies translateAdText translates keys and phrases correctly', () => {
      // Key lookup
      expect(translateAdText('tabCampaigns', 'ru')).toBe('Кампании');
      expect(translateAdText('tabCampaigns', 'en')).toBe('Campaigns');
      expect(translateAdText('tabCampaigns', 'uz')).toBe('Kampaniyalar');

      // Phrase dictionary lookup
      expect(translateAdText('Экспорт CSV', 'en')).toBe('Export CSV');
      expect(translateAdText('Экспорт CSV', 'uz')).toBe('CSV eksport');
      expect(translateAdText('Экспорт CSV', 'ru')).toBe('Экспорт CSV');

      expect(translateAdText('Узнать больше', 'en')).toBe('Learn More');
      expect(translateAdText('Узнать больше', 'uz')).toBe('Batafsil bilish');
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
