import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { ArrowLeft, Megaphone, ExternalLink, Sparkles, ShieldCheck, Globe } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import ThemeSwitch from '@/components/theme-switch';
import authorizationUtil from '@/utils/authorization-util';
import { AD_TRANSLATIONS, AdLanguage, getActiveAdLanguage, setActiveAdLanguage } from './translations';
import SwipiesAdsPage from './index';

export default function StandaloneAdsApp() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Language state synchronized with Ads dashboard & global storage (defaults strictly to 'ru')
  const [currentLang, setCurrentLang] = useState<AdLanguage>(getActiveAdLanguage);

  const handleLanguageChange = (lang: AdLanguage) => {
    setCurrentLang(lang);
    setActiveAdLanguage(lang);
  };

  useEffect(() => {
    const checkLang = () => {
      const active = getActiveAdLanguage();
      setCurrentLang(active);
    };
    window.addEventListener('storage', checkLang);
    window.addEventListener('languagechange', checkLang);
    window.addEventListener('adlanguagechange', checkLang);
    return () => {
      window.removeEventListener('storage', checkLang);
      window.removeEventListener('languagechange', checkLang);
      window.removeEventListener('adlanguagechange', checkLang);
    };
  }, []);

  // Ensure document and root allow native vertical scrolling inside the flex container
  useEffect(() => {
    const rootEl = document.getElementById('root');
    if (rootEl) {
      rootEl.style.height = '100dvh';
      rootEl.style.maxHeight = '100dvh';
      rootEl.style.overflow = 'hidden';
    }
  }, []);

  const t = (key: string): string => {
    return AD_TRANSLATIONS[currentLang]?.[key] || AD_TRANSLATIONS['ru']?.[key] || key;
  };

  // Check and persist auth token from URL query if transferred across subdomains
  useEffect(() => {
    const auth = searchParams.get('auth');
    if (auth) {
      authorizationUtil.setAuthorization(auth);
      // Clean auth query from URL without page reload
      const newUrl = new URL(window.location.href);
      newUrl.searchParams.delete('auth');
      window.history.replaceState({}, '', newUrl.pathname + newUrl.search);
    }
  }, [searchParams]);

  const isAuthenticated = Boolean(authorizationUtil.getAuthorization());

  useEffect(() => {
    if (!isAuthenticated) {
      const currentUrl = encodeURIComponent(window.location.href);
      navigate(`/login?redirect=${currentUrl}`, { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // Main application URL resolver (to switch back to main Swipies AI platform)
  const mainAppUrl = useMemo(() => {
    if (typeof window === 'undefined') return '/';
    const host = window.location.hostname.toLowerCase();
    const token = authorizationUtil.getAuthorization();
    const authQuery = token ? `?auth=${encodeURIComponent(token)}` : '';

    if (host === 'localhost' || host === '127.0.0.1') {
      return `/${authQuery}`;
    }
    // Return to demo.swipies.app or app.swipies.app
    if (host.includes('demo') || host.includes('ads')) {
      return `${window.location.protocol}//demo.swipies.app/${authQuery}`;
    }
    return `${window.location.protocol}//app.swipies.app/${authQuery}`;
  }, []);

  if (!isAuthenticated) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">{t('redirectingToLogin')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen h-[100dvh] max-h-screen max-h-[100dvh] w-full bg-background flex flex-col overflow-hidden antialiased">
      {/* Standalone Top Bar */}
      <header className="shrink-0 z-40 flex h-14 w-full items-center justify-between border-b bg-card/95 px-3 sm:px-4 md:px-6 backdrop-blur-md">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <div className="flex items-center gap-2 font-bold tracking-tight text-foreground min-w-0">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600/10 text-blue-500 border border-blue-500/20 shrink-0">
              <Megaphone className="h-4 w-4" />
            </div>
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-base font-bold tracking-tight truncate">Swipies Ads</span>
              <Badge
                variant="outline"
                className="border-blue-500/30 bg-blue-500/10 text-blue-400 text-[11px] py-0.5 px-2 inline-flex items-center gap-1 font-medium shrink-0"
              >
                <Sparkles className="h-3 w-3 shrink-0" />
                <span>{t('standaloneBadge')}</span>
              </Badge>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          {/* Unified DB Badge */}
          <div className="hidden lg:flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/40 px-2.5 py-1 rounded-full border border-border/40 shrink-0">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
            <span>{t('unifiedDbBadge')}</span>
          </div>

          {/* Synchronized Header Language Switcher */}
          <div className="flex items-center gap-0.5 rounded-md border bg-muted/40 p-0.5 shrink-0">
            <Globe className="h-3.5 w-3.5 text-blue-500 ml-1 mr-0.5 shrink-0" />
            {(['ru', 'en', 'uz'] as const).map((lang) => (
              <button
                key={lang}
                type="button"
                onClick={() => handleLanguageChange(lang)}
                className={`px-1.5 py-0.5 rounded text-[11px] font-semibold uppercase transition-all ${
                  currentLang === lang
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
                }`}
              >
                {lang}
              </button>
            ))}
          </div>

          <div className="scale-90 shrink-0">
            <ThemeSwitch />
          </div>

          <Button
            variant="outline"
            size="sm"
            asChild
            className="text-xs h-8 border-border hover:bg-muted/70 transition-colors shrink-0"
          >
            <a href={mainAppUrl} className="flex items-center gap-1.5">
              <ArrowLeft className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">{t('backToMainApp')}</span>
              <span className="sm:hidden">{t('backToMainAppShort')}</span>
              <ExternalLink className="h-3 w-3 opacity-60 ml-0.5 shrink-0" />
            </a>
          </Button>
        </div>
      </header>

      {/* Main Ads Application Dashboard with full vertical scrolling */}
      <main
        id="ads-main-scroll"
        className="flex-1 min-h-0 w-full overflow-y-auto overflow-x-hidden overscroll-contain"
        style={{
          WebkitOverflowScrolling: 'touch',
          scrollbarWidth: 'thin',
        }}
      >
        <div className="w-full max-w-[1920px] mx-auto min-h-full">
          <SwipiesAdsPage currentLang={currentLang} onLanguageChange={handleLanguageChange} />
        </div>
      </main>
    </div>
  );
}

