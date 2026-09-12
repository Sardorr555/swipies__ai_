import React, { useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { ArrowLeft, Megaphone, ExternalLink, Sparkles, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import ThemeSwitch from '@/components/theme-switch';
import authorizationUtil from '@/utils/authorization-util';
import SwipiesAdsPage from './index';

export default function StandaloneAdsApp() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

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
          <p className="text-sm text-muted-foreground">Перенаправление на страницу входа...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full bg-background flex flex-col antialiased">
      {/* Standalone Top Bar */}
      <header className="sticky top-0 z-40 flex h-14 w-full items-center justify-between border-b bg-card/95 px-4 md:px-6 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 font-bold tracking-tight text-foreground">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600/10 text-blue-500 border border-blue-500/20">
              <Megaphone className="h-4 w-4" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="text-base font-semibold">Swipies Ads</span>
                <Badge variant="outline" className="border-blue-500/30 bg-blue-500/10 text-blue-400 text-[11px] py-0 px-1.5 hidden sm:inline-flex">
                  <Sparkles className="mr-1 h-3 w-3" /> Standalone Service
                </Badge>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/40 px-2.5 py-1 rounded-full border border-border/40">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
            <span>Единая база данных и авторизация</span>
          </div>

          <div className="scale-90">
            <ThemeSwitch />
          </div>

          <Button
            variant="outline"
            size="sm"
            asChild
            className="text-xs h-8 border-border hover:bg-muted/70 transition-colors"
          >
            <a href={mainAppUrl} className="flex items-center gap-1.5">
              <ArrowLeft className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Вернуться в Swipies AI</span>
              <span className="sm:hidden">В Swipies AI</span>
              <ExternalLink className="h-3 w-3 opacity-60 ml-0.5" />
            </a>
          </Button>
        </div>
      </header>

      {/* Main Ads Application Dashboard */}
      <main className="flex-1 w-full max-w-[1920px] mx-auto overflow-y-auto">
        <SwipiesAdsPage />
      </main>
    </div>
  );
}
