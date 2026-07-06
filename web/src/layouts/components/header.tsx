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
import { DesktopNavbar, MobileNavbar } from './global-navbar';
import { MobileMenuFooter } from './mobile-menu-footer';
import ThemeButton from './theme-button';
import { useHeaderNavLayout } from './use-header-nav-layout';

import { supportedLanguages } from '@/locales/config';

export function Header({
  className,
  ...props
}: React.HTMLAttributes<HTMLElement>) {
  const { pathname } = useLocation();
  const changeLanguage = useChangeLanguage();

  const {
    data: { language = 'en', avatar, nickname },
  } = useFetchUserInfo();

  const { data: tenantData } = useListTenant();
  const hasNotification = useMemo(
    () => tenantData?.some((x) => x.role === TenantRole.Invite),
    [tenantData],
  );

  const currentLanguage = supportedLanguages.find((x) => x.code === language);

  const {
    headerRef,
    logoRef,
    expandedRightMeasureRef,
    navMeasureRef,
    isCompact,
  } = useHeaderNavLayout(`${hasNotification}-${language}`);

  return (
    <>
      <header
        ref={headerRef}
        key="app-navbar"
        className={cn(
          'w-full min-w-0 flex items-center gap-2 sm:gap-4',
          className,
        )}
        {...props}
      >
        <div className="inline-flex shrink-0 items-center gap-2">
          {isCompact && (
            <MobileNavbar
              renderFooter={(close) => <MobileMenuFooter onClose={close} />}
            />
          )}
          <div ref={logoRef} className="inline-flex shrink-0 items-center">
            <Link
              to={Routes.Root}
              aria-current={pathname === Routes.Root ? 'page' : undefined}
              className="flex items-center gap-2 hover:opacity-90 transition-opacity"
            >
              <img
                src={'/logo.svg'}
                alt={`${BRAND.name} logo`}
                className="size-10 animate-fade-in"
              />
              {!isCompact && (
                <div className="flex flex-col text-left">
                  <span className="text-xl font-bold tracking-tight text-text-primary leading-none">
                    {BRAND.name}
                  </span>
                  <span className="text-[10px] text-text-secondary leading-none mt-0.5">
                    {BRAND.slogan}
                  </span>
                </div>
              )}
            </Link>
          </div>
        </div>

        {!isCompact && (
          <div className="flex min-w-0 flex-1 justify-center overflow-hidden">
            <DesktopNavbar />
          </div>
        )}

        {isCompact && <div className="flex-1" aria-hidden />}

        <div
          className={cn(
            'flex shrink-0 items-center justify-end text-text-badge',
            isCompact ? 'gap-0.5' : 'gap-4',
          )}
          data-testid="auth-status"
        >
          {!isCompact && (
            <>
              <Link
                to={Routes.Pricing}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-semibold text-white rounded-full bg-gradient-to-r from-[#478AF5] to-[#42D7E7] hover:from-[#3a7ae0] hover:to-[#35c5d4] shadow-md hover:shadow-lg transition-all duration-200 hover:scale-105"
                data-testid="upgrade-button"
              >
                <LucideZap className="size-4" />
                Upgrade
              </Link>

              <a
                className="p-2 text-text-secondary hover:text-text-primary focus-visible:text-text-primary shrink-0"
                target="_blank"
                href="https://t.me/albakiev01"
                rel="noreferrer noopener"
                aria-label="Telegram"
              >
                <svg viewBox="0 0 24 24" className="size-5" fill="currentColor">
                  <path d="M20.665 3.717l-17.73 6.837c-1.21.486-1.203 1.161-.222 1.462l4.552 1.42 10.532-6.645c.498-.303.953-.14.578.192l-8.533 7.701-.33 4.955c.488 0 .702-.223.974-.488l2.338-2.275 4.866 3.59c.898.496 1.543.241 1.766-.83l3.195-15.059c.328-1.311-.497-1.903-1.357-1.517z" />
                </svg>
              </a>
            </>
          )}

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className={cn(
                  'size-10 shrink-0 px-0',
                  !isCompact && 'size-auto gap-1 px-4',
                )}
                aria-label={currentLanguage?.displayName}
              >
                {isCompact && <LucideLanguages className="size-5" />}
                {!isCompact && (
                  <>
                    {currentLanguage?.displayName}
                    <LucideChevronDown className="size-[1em]" />
                  </>
                )}
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

          {!isCompact && (
            <>
              <Button
                asLink
                variant="ghost"
                size="icon"
                className="size-8"
                to="https://ragflow.io/docs/dev/category/user-guides"
                target="_blank"
                rel="noreferrer noopener"
              >
                <LucideCircleHelp className="size-[1em]" />
              </Button>

              {hasNotification && <BellButton className="!size-8" />}
            </>
          )}

          <ThemeButton className={cn(!isCompact && '!size-8')} />

          <Link
            to={Routes.UserSetting}
            className={cn(
              'relative flex size-10 shrink-0 items-center justify-center',
              !isCompact && 'ms-3',
            )}
            data-testid="settings-entrypoint"
          >
            <RAGFlowAvatar
              name={nickname}
              avatar={avatar}
              isPerson
              className="size-8"
            />
          </Link>
        </div>
      </header>

      <div
        className="pointer-events-none invisible fixed -left-[9999px] top-0"
        aria-hidden
      >
        <div ref={navMeasureRef}>
          <DesktopNavbar />
        </div>
        <div
          ref={expandedRightMeasureRef}
          className="inline-flex shrink-0 items-center justify-end gap-4 text-text-badge"
        >
          <Link
            to={Routes.Pricing}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-semibold text-white rounded-full bg-gradient-to-r from-[#478AF5] to-[#42D7E7]"
          >
            <LucideZap className="size-4" />
            Upgrade
          </Link>
          <a
            className="p-2 text-text-secondary hover:text-text-primary"
            target="_blank"
            href="https://t.me/albakiev01"
            rel="noreferrer noopener"
          >
            <svg viewBox="0 0 24 24" className="size-5" fill="currentColor">
              <path d="M20.665 3.717l-17.73 6.837c-1.21.486-1.203 1.161-.222 1.462l4.552 1.42 10.532-6.645c.498-.303.953-.14.578.192l-8.533 7.701-.33 4.955c.488 0 .702-.223.974-.488l2.338-2.275 4.866 3.59c.898.496 1.543.241 1.766-.83l3.195-15.059c.328-1.311-.497-1.903-1.357-1.517z" />
            </svg>
          </a>

          <Button variant="ghost" className="size-auto gap-1 px-4">
            {currentLanguage?.displayName}
            <LucideChevronDown className="size-[1em]" />
          </Button>
          <Button variant="ghost" size="icon" className="size-8">
            <LucideCircleHelp className="size-[1em]" />
          </Button>
          <ThemeButton className="!size-8" />
          {hasNotification && <BellButton className="!size-8" />}
          <div className="relative ms-3 flex size-10 shrink-0 items-center justify-center">
            <RAGFlowAvatar
              name={nickname}
              avatar={avatar}
              isPerson
              className="size-8"
            />
          </div>
        </div>
      </div>
    </>
  );
}
