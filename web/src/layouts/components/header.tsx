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
import { LucideChevronDown, LucideCircleHelp, LucideZap } from 'lucide-react';
import React, { useMemo } from 'react';
import { Link, useLocation } from 'react-router';
import { BellButton } from './bell-button';
import GlobalNavbar from './global-navbar';
import ThemeButton from './theme-button';

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

  // const langItems = LanguageList.map((x) => ({
  //   key: x,
  //   label: <span>{LanguageMap[x as keyof typeof LanguageMap]}</span>,
  // }));

  return (
    <header
      key="app-navbar"
      className={cn(
        'w-full grid grid-cols-[1fr_auto_1fr] grid-rows-1 items-center gap-8',
        className,
      )}
      {...props}
    >
      <div className="inline-flex items-center">
        <Link
          to={Routes.Root}
          aria-current={pathname === Routes.Root ? 'page' : undefined}
          className="flex items-center gap-2 hover:opacity-90 transition-opacity"
        >
          <img
            src={'/logo.svg'}
            alt={`${BRAND.name} logo`}
            className="size-10"
          />
          <div className="flex flex-col text-left">
            <span className="text-xl font-bold tracking-tight text-text-primary leading-none">
              {BRAND.name}
            </span>
            <span className="text-[10px] text-text-secondary leading-none mt-0.5">
              {BRAND.slogan}
            </span>
          </div>
        </Link>
      </div>

      <GlobalNavbar />

      <div
        className="flex items-center justify-end gap-4 text-text-badge"
        data-testid="auth-status"
      >
        <Link
          to={Routes.Pricing}
          className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-semibold text-white rounded-full bg-gradient-to-r from-[#478AF5] to-[#42D7E7] hover:from-[#3a7ae0] hover:to-[#35c5d4] shadow-md hover:shadow-lg transition-all duration-200 hover:scale-105"
          data-testid="upgrade-button"
        >
          <LucideZap className="size-4" />
          Upgrade
        </Link>

        <a
          className="p-2 text-text-secondary hover:text-text-primary focus-visible:text-text-primary"
          target="_blank"
          href="https://t.me/albakiev01"
          rel="noreferrer noopener"
          aria-label="Telegram"
        >
          <svg viewBox="0 0 24 24" className="size-5" fill="currentColor">
            <path d="M20.665 3.717l-17.73 6.837c-1.21.486-1.203 1.161-.222 1.462l4.552 1.42 10.532-6.645c.498-.303.953-.14.578.192l-8.533 7.701-.33 4.955c.488 0 .702-.223.974-.488l2.338-2.275 4.866 3.59c.898.496 1.543.241 1.766-.83l3.195-15.059c.328-1.311-.497-1.903-1.357-1.517z" />
          </svg>
        </a>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button className="flex items-center gap-1" variant="ghost">
              {currentLanguage?.displayName}
              <LucideChevronDown className="size-[1em]" />
            </Button>
          </DropdownMenuTrigger>

          <DropdownMenuContent>
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
          to="https://ragflow.io/docs/dev/category/user-guides"
          target="_blank"
          rel="noreferrer noopener"
        >
          <LucideCircleHelp className="size-[1em]" />
        </Button>

        <ThemeButton />

        {hasNotification && <BellButton />}

        <Link
          to={Routes.UserSetting}
          className="relative ms-3"
          data-testid="settings-entrypoint"
        >
          <RAGFlowAvatar
            name={nickname}
            avatar={avatar}
            isPerson
            className="size-8"
          />
          {/* Temporarily hidden */}
          {/* <Badge className="h-5 w-8 absolute font-normal p-0 justify-center -right-8 -top-2 text-bg-base bg-gradient-to-l from-[#42D7E7] to-[#478AF5]">
            Pro
          </Badge> */}
        </Link>
      </div>
    </header>
  );
}
