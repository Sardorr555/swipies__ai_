import { RAGFlowAvatar } from '@/components/ragflow-avatar';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { BRAND } from '@/constants/branding';
import { useChangeLanguage } from '@/hooks/logic-hooks';
import {
  useFetchUserInfo,
  useListTenant,
  useFetchTenantInfo,
} from '@/hooks/use-user-setting-request';
import { cn } from '@/lib/utils';
import { TenantRole } from '@/pages/user-setting/constants';
import { Routes } from '@/routes';
import {
  LucideChevronDown,
  LucideCircleHelp,
  LucideLanguages,
  LucideZap,
} from 'lucide-react';
import React, { useMemo } from 'react';
import { Link, useLocation } from 'react-router';
import { BellButton } from './bell-button';
import { MobileNavbar } from './global-navbar';
import { MobileMenuFooter } from './mobile-menu-footer';
import ThemeButton from './theme-button';

import { supportedLanguages } from '@/locales/config';

export function Header({
  className,
  ...props
}: React.HTMLAttributes<HTMLElement>) {
  const changeLanguage = useChangeLanguage();

  const {
    data: { language = 'en', avatar, nickname },
  } = useFetchUserInfo();

  const { data: tenantData } = useListTenant();
  const { data: tenantInfo } = useFetchTenantInfo();
  const currentPlan = (tenantInfo?.plan_type || 'free').toLowerCase();

  const upgradeLabel = useMemo(() => {
    if (currentPlan === 'plus') return 'Plus';
    if (currentPlan === 'pro') return 'Pro';
    if (currentPlan === 'license') return 'License';
    if (currentPlan === 'enterprise') return 'Enterprise';
    return 'Upgrade';
  }, [currentPlan]);

  const hasNotification = useMemo(
    () => tenantData?.some((x) => x.role === TenantRole.Invite),
    [tenantData],
  );

  const currentLanguage = useMemo(
    () => supportedLanguages.find((x) => x.code === language),
    [language],
  );

  return (
    <header
      key="app-navbar"
      className={cn(
        'w-full min-w-0 flex items-center justify-between relative bg-bg-component/30 backdrop-blur-md border-b border-border-default/40 py-3 px-6 select-none',
        className,
      )}
      {...props}
    >
      {/* Left section: Hamburger menu on mobile/tablet (hidden on desktop) */}
      <div className="flex items-center md:hidden z-10">
        <MobileNavbar
          renderFooter={(close) => <MobileMenuFooter onClose={close} />}
        />
      </div>
      
      {/* Left placeholder/spacer on desktop to keep things balanced */}
      <div className="hidden md:block w-10 z-10" />

      {/* Center section: Logo and Branding (perfectly centered absolute box) */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center z-0">
        <Link
          to={Routes.Root}
          className="flex items-center gap-3 hover:opacity-90 transition-opacity"
        >
          <img
            src={'/logo.svg'}
            alt={`${BRAND.name} logo`}
            className="size-9 animate-fade-in"
          />
          <div className="flex flex-col text-left">
            <span className="text-lg font-bold tracking-tight text-text-primary leading-none">
              {BRAND.name}
            </span>
            <span className="text-[9px] text-text-secondary leading-none mt-0.5 font-medium">
              {BRAND.slogan}
            </span>
          </div>
        </Link>
      </div>

      {/* Right section: Global actions */}
      <div
        className="flex items-center gap-2 sm:gap-3 text-text-badge z-10 ml-auto"
        data-testid="auth-status"
      >
        <a
          className="p-2 text-text-secondary hover:text-text-primary focus-visible:text-text-primary shrink-0 transition-colors"
          target="_blank"
          href="https://t.me/albakiev01"
          rel="noreferrer noopener"
          aria-label="Telegram"
        >
          <svg viewBox="0 0 24 24" className="size-4.5" fill="currentColor">
            <path d="M20.665 3.717l-17.73 6.837c-1.21.486-1.203 1.161-.222 1.462l4.552 1.42 10.532-6.645c.498-.303.953-.14.578.192l-8.533 7.701-.33 4.955c.488 0 .702-.223.974-.488l2.338-2.275 4.866 3.59c.898.496 1.543.241 1.766-.83l3.195-15.059c.328-1.311-.497-1.903-1.357-1.517z" />
          </svg>
        </a>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="h-8 gap-1 px-2.5 text-xs text-text-secondary hover:text-text-primary"
              aria-label={currentLanguage?.displayName}
            >
              <LucideLanguages className="size-4" />
              <span className="hidden sm:inline">{currentLanguage?.displayName}</span>
              <LucideChevronDown className="size-3" />
            </Button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end">
            {supportedLanguages.map((x) => (
              <DropdownMenuItem
                key={x.code}
                onClick={() => changeLanguage(x.code)}
              >
                {x.displayName}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <Button
          asLink
          variant="ghost"
          size="icon"
          className="size-8 text-text-secondary hover:text-text-primary"
          to="https://docs.swipies.app/docs/category/user-guides"
          target="_blank"
          rel="noreferrer noopener"
        >
          <LucideCircleHelp className="size-4.5" />
        </Button>

        {hasNotification && <BellButton className="!size-8" />}

        <ThemeButton className="!size-8" />

        <Link
          to={Routes.UserSetting}
          className="relative flex size-8 shrink-0 items-center justify-center ms-1 hover:opacity-90 transition-opacity"
          data-testid="settings-entrypoint"
        >
          <RAGFlowAvatar
            name={nickname}
            avatar={avatar}
            isPerson
            className="size-7"
          />
        </Link>
      </div>
    </header>
  );
}
