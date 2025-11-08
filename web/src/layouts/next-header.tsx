import { RAGFlowAvatar } from '@/components/ragflow-avatar';
import { useTheme } from '@/components/theme-provider';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Segmented, SegmentedValue } from '@/components/ui/segmented';
import { LanguageList, LanguageMap, ThemeEnum } from '@/constants/common';
import { useChangeLanguage } from '@/hooks/logic-hooks';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import { useNavigateWithFromState } from '@/hooks/route-hook';
import { useFetchUserInfo } from '@/hooks/user-setting-hooks';
import { Routes } from '@/routes';
import { camelCase } from 'lodash';
import {
  ChevronDown,
  CircleHelp,
  Cpu,
  File,
  Github,
  House,
  Library,
  MessageSquareText,
  Moon,
  Search,
  Sun,
} from 'lucide-react';
import React, { useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'umi';
import { BellButton } from './bell-button';

const handleDocHelpCLick = () => {
  window.open('https://github.com/Sardorr555/swipies__ai_', 'target');
};

export function Header() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const navigate = useNavigateWithFromState();
  const { navigateToOldProfile } = useNavigatePage();

  const changeLanguage = useChangeLanguage();
  const { setTheme, theme } = useTheme();

  const {
    data: { language = 'English', avatar, nickname },
  } = useFetchUserInfo();

  const handleItemClick = (key: string) => () => {
    changeLanguage(key);
  };

  const items = LanguageList.map((x) => ({
    key: x,
    label: <span>{LanguageMap[x as keyof typeof LanguageMap]}</span>,
  }));

  const onThemeClick = React.useCallback(() => {
    setTheme(theme === ThemeEnum.Dark ? ThemeEnum.Light : ThemeEnum.Dark);
  }, [setTheme, theme]);

  const tagsData = useMemo(
    () => [
      { path: Routes.Root, name: t('header.Root'), icon: House },
      { path: Routes.Datasets, name: t('header.dataset'), icon: Library },
      { path: Routes.Chats, name: t('header.chat'), icon: MessageSquareText },
      { path: Routes.Searches, name: t('header.search'), icon: Search },
      { path: Routes.Agents, name: t('header.flow'), icon: Cpu },
      { path: Routes.Files, name: t('header.fileManager'), icon: File },
    ],
    [t],
  );

  const options = useMemo(() => {
    return tagsData.map((tag) => {
      const HeaderIcon = tag.icon;

      return {
        label:
          tag.path === Routes.Root ? (
            <HeaderIcon className="size-6"></HeaderIcon>
          ) : (
            <span>{tag.name}</span>
          ),
        value: tag.path,
      };
    });
  }, [tagsData]);

  // const currentPath = useMemo(() => {
  //   return (
  //     tagsData.find((x) => pathname.startsWith(x.path))?.path || Routes.Root
  //   );
  // }, [pathname, tagsData]);

  const handleChange = (path: SegmentedValue) => {
    navigate(path as Routes);
  };

  const handleLogoClick = useCallback(() => {
    navigate(Routes.Root);
  }, [navigate]);

  return (
    <section className="w-full px-4 py-3 md:px-5 md:py-4 lg:px-6 lg:pr-14 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 sm:gap-4">
      <div className="flex items-center gap-2 sm:gap-3 md:gap-4">
        <img
          src={'/logo.svg'}
          alt="logo"
          className="w-8 h-8 sm:w-9 sm:h-9 md:w-10 md:h-10 cursor-pointer"
          onClick={handleLogoClick}
        />
        <a
          className="flex items-center gap-1 sm:gap-1.5 text-text-secondary"
          target="_blank"
          href="https://github.com/Sardorr555/swipies__ai_.git"
          rel="noreferrer"
        >
          <Github className="w-3 h-3 sm:w-4 sm:h-4" />
          {/* <span className=" text-base">21.5k stars</span> */}
        </a>
      </div>
      <div className="w-full sm:w-auto flex-1 sm:flex-none">
        <Segmented
          options={options}
          value={pathname}
          onChange={handleChange}
          className="w-full sm:w-auto"
        ></Segmented>
      </div>
      <div className="flex items-center gap-2 sm:gap-3 md:gap-4 lg:gap-5 text-text-badge flex-wrap">
        <DropdownMenu>
          <DropdownMenuTrigger>
            <div className="flex items-center gap-1 text-sm sm:text-base">
              <span className="hidden sm:inline">{t(`common.${camelCase(language)}`)}</span>
              <span className="sm:hidden">{language.substring(0, 2).toUpperCase()}</span>
              <ChevronDown className="w-3 h-3 sm:w-4 sm:h-4" />
            </div>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            {items.map((x) => (
              <DropdownMenuItem key={x.key} onClick={handleItemClick(x.key)}>
                {x.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        <Button variant={'ghost'} onClick={handleDocHelpCLick} className="p-2 sm:p-2.5">
          <CircleHelp className="w-4 h-4 sm:w-5 sm:h-5" />
        </Button>
        <Button variant={'ghost'} onClick={onThemeClick} className="p-2 sm:p-2.5">
          {theme === 'light' ? <Sun className="w-4 h-4 sm:w-5 sm:h-5" /> : <Moon className="w-4 h-4 sm:w-5 sm:h-5" />}
        </Button>
        <BellButton></BellButton>
        <div className="relative">
          <RAGFlowAvatar
            name={nickname}
            avatar={avatar}
            className="w-7 h-7 sm:w-8 sm:h-8 cursor-pointer"
            onClick={navigateToOldProfile}
          ></RAGFlowAvatar>
          {/* Temporarily hidden */}
          {/* <Badge className="h-5 w-8 absolute font-normal p-0 justify-center -right-8 -top-2 text-bg-base bg-gradient-to-l from-[#42D7E7] to-[#478AF5]">
            Pro
          </Badge> */}
        </div>
      </div>
    </section>
  );
}
