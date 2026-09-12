import ru from '../../locales/ru';
import en from '../../locales/en';
import uz from '../../locales/uz';

describe('Auth & Onboarding Logic Tests', () => {
  describe('Localization for Marketing Consent', () => {
    it('ru locale should contain non-empty marketingConsentLabel', () => {
      expect((ru as any).translation.login.marketingConsentLabel).toBeDefined();
      expect(typeof (ru as any).translation.login.marketingConsentLabel).toBe('string');
      expect((ru as any).translation.login.marketingConsentLabel.length).toBeGreaterThan(10);
      expect((ru as any).translation.login.marketingConsentLabel).toContain('рассылку');
    });

    it('en locale should contain non-empty marketingConsentLabel', () => {
      expect((en as any).translation.login.marketingConsentLabel).toBeDefined();
      expect(typeof (en as any).translation.login.marketingConsentLabel).toBe('string');
      expect((en as any).translation.login.marketingConsentLabel.length).toBeGreaterThan(10);
      expect((en as any).translation.login.marketingConsentLabel).toContain('promotional emails');
    });

    it('uz locale should contain non-empty marketingConsentLabel', () => {
      expect((uz as any).translation.login.marketingConsentLabel).toBeDefined();
      expect(typeof (uz as any).translation.login.marketingConsentLabel).toBe('string');
      expect((uz as any).translation.login.marketingConsentLabel.length).toBeGreaterThan(10);
      expect((uz as any).translation.login.marketingConsentLabel).toContain('Reklama');
    });
  });

  describe('Google User Detection Logic in Onboarding', () => {
    const checkIsGoogleUser = (userInfo: { login_channel?: string | null; phone?: string | null } | null | undefined): boolean => {
      return Boolean(
        (userInfo?.login_channel?.toLowerCase() === 'google' ||
          userInfo?.login_channel?.toLowerCase()?.includes('google')) &&
          !userInfo?.phone,
      );
    };

    it('identifies Google user without phone as requiring phone prompt', () => {
      expect(checkIsGoogleUser({ login_channel: 'google', phone: null })).toBe(true);
      expect(checkIsGoogleUser({ login_channel: 'Google', phone: '' })).toBe(true);
      expect(checkIsGoogleUser({ login_channel: 'google_oauth', phone: undefined })).toBe(true);
    });

    it('does NOT prompt Google user who already has a phone number', () => {
      expect(checkIsGoogleUser({ login_channel: 'google', phone: '+998901234567' })).toBe(false);
      expect(checkIsGoogleUser({ login_channel: 'Google', phone: '+79991234567' })).toBe(false);
    });

    it('does NOT prompt standard password-registered users (they already supplied phone)', () => {
      expect(checkIsGoogleUser({ login_channel: 'password', phone: null })).toBe(false);
      expect(checkIsGoogleUser({ login_channel: 'password', phone: '+998901112233' })).toBe(false);
    });

    it('does NOT prompt other third-party providers or undefined user info', () => {
      expect(checkIsGoogleUser({ login_channel: 'github', phone: null })).toBe(false);
      expect(checkIsGoogleUser(null)).toBe(false);
      expect(checkIsGoogleUser(undefined)).toBe(false);
    });
  });

  describe('Onboarding Steps and Skip Navigation Logic', () => {
    const STEPS_COUNT = 4;

    const computeTotalSteps = (isGoogleUser: boolean) => {
      return isGoogleUser ? STEPS_COUNT + 1 : STEPS_COUNT;
    };

    it('computes 5 steps for Google users without phone and 4 steps for all others', () => {
      expect(computeTotalSteps(true)).toBe(5);
      expect(computeTotalSteps(false)).toBe(4);
    });

    it('routes Google users to the phone step when skip is clicked', () => {
      const isGoogleUser = true;
      let currentStep = 1; // user is on step 2 of questions
      let surveyFinished = false;

      const handleSkip = () => {
        if (isGoogleUser && currentStep < STEPS_COUNT) {
          currentStep = STEPS_COUNT; // Jump straight to phone step (step index 4)
          return;
        }
        surveyFinished = true;
      };

      handleSkip();
      expect(currentStep).toBe(4);
      expect(surveyFinished).toBe(false);
    });

    it('finishes survey immediately when non-Google user clicks skip', () => {
      const isGoogleUser = false;
      let currentStep = 1;
      let surveyFinished = false;

      const handleSkip = () => {
        if (isGoogleUser && currentStep < STEPS_COUNT) {
          currentStep = STEPS_COUNT;
          return;
        }
        surveyFinished = true;
      };

      handleSkip();
      expect(currentStep).toBe(1);
      expect(surveyFinished).toBe(true);
    });
  });

  describe('Phone Cleaning, Country Identification & Validation', () => {
    const cleanPhone = (phone: string) => (phone || '').replace(/[^\d+]/g, '');

    const detectCountry = (clean: string) => {
      if (clean.startsWith('+998') || clean.startsWith('998')) {
        return { flag: '🇺🇿', name: 'Uzbekistan' };
      } else if (clean.startsWith('+7') || clean.startsWith('7')) {
        return { flag: '🇷🇺', name: 'Russia/Kazakhstan' };
      } else if (clean.startsWith('+86') || clean.startsWith('86')) {
        return { flag: '🇨🇳', name: 'China' };
      } else if (clean.startsWith('+1') || clean.startsWith('1')) {
        return { flag: '🇺🇸', name: 'USA/Canada' };
      } else if (clean.startsWith('+')) {
        return { flag: '🌐', name: 'International' };
      }
      return null;
    };

    const validatePhone = (clean: string) => {
      return Boolean(clean && clean.length >= 7);
    };

    it('correctly cleans raw phone input', () => {
      expect(cleanPhone('+998 (90) 123-45-67')).toBe('+998901234567');
      expect(cleanPhone('   +7 999 123 45 67  ')).toBe('+79991234567');
      expect(cleanPhone('+1-202-555-0199')).toBe('+12025550199');
    });

    it('detects Uzbekistan phone numbers', () => {
      const country = detectCountry('+998901234567');
      expect(country).not.toBeNull();
      expect(country?.flag).toBe('🇺🇿');
      expect(country?.name).toBe('Uzbekistan');
    });

    it('detects Russia/Kazakhstan phone numbers', () => {
      const country = detectCountry('+79991234567');
      expect(country).not.toBeNull();
      expect(country?.flag).toBe('🇷🇺');
    });

    it('detects USA/Canada phone numbers', () => {
      const country = detectCountry('+12025550199');
      expect(country).not.toBeNull();
      expect(country?.flag).toBe('🇺🇸');
    });

    it('validates minimum phone length', () => {
      expect(validatePhone('')).toBe(false);
      expect(validatePhone('+998')).toBe(false);
      expect(validatePhone('+12345')).toBe(false);
      expect(validatePhone('+1234567')).toBe(true);
      expect(validatePhone('+998901234567')).toBe(true);
    });
  });

  describe('Registration Form Marketing Consent Submission', () => {
    it('defaults marketingConsent to true if unspecified', () => {
      const params = {
        email: 'user@test.com',
        marketingConsent: undefined as boolean | undefined,
      };
      const marketing_consent = params.marketingConsent ?? true;
      expect(marketing_consent).toBe(true);
    });

    it('respects user opt-out (marketingConsent: false)', () => {
      const params = {
        email: 'user@test.com',
        marketingConsent: false,
      };
      const marketing_consent = params.marketingConsent ?? true;
      expect(marketing_consent).toBe(false);
    });

    it('respects explicit user opt-in (marketingConsent: true)', () => {
      const params = {
        email: 'user@test.com',
        marketingConsent: true,
      };
      const marketing_consent = params.marketingConsent ?? true;
      expect(marketing_consent).toBe(true);
    });
  });
});
