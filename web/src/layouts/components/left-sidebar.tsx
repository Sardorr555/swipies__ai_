import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation } from 'react-router';
import {
  LucideBrain,
  LucideCpu,
  LucideDatabase,
  LucideFolderOpen,
  LucideHouse,
  LucideMessageSquareText,
  LucideSearch,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Routes } from '@/routes';

const PathMap = {
  [Routes.Datasets]: [Routes.Datasets, Routes.DatasetBase],
  [Routes.Chats]: [Routes.Chats, Routes.Chat],
  [Routes.Searches]: [Routes.Searches, Routes.Search],
  [Routes.Agents]: [Routes.Agents, Routes.AgentTemplates],
  [Routes.Memories]: [Routes.Memories, Routes.Memory, Routes.MemoryMessage],
  [Routes.Files]: [Routes.Files],
} as const;

const matchesPath = (pathname: string, candidate: string) =>
  pathname === candidate || pathname.startsWith(`${candidate}/`);

const menuItems = [
  { path: Routes.Root, name: 'header.home', icon: LucideHouse },
  { path: Routes.Datasets, name: 'header.dataset', icon: LucideDatabase },
  {
    path: Routes.Chats,
    name: 'header.chat',
    icon: LucideMessageSquareText,
    'data-testid': 'nav-chat',
  },
  {
    path: Routes.Searches,
    name: 'header.search',
    icon: LucideSearch,
    'data-testid': 'nav-search',
  },
  {
    path: Routes.Agents,
    name: 'header.flow',
    icon: LucideCpu,
    'data-testid': 'nav-agent',
  },
  { path: Routes.Memories, name: 'header.memories', icon: LucideBrain },
  { path: Routes.Files, name: 'header.fileManager', icon: LucideFolderOpen },
];

export function LeftSidebar({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  const { t } = useTranslation();
  const { pathname } = useLocation();

  const activePath = useMemo(() => {
    return (
      Object.keys(PathMap).find((x: string) =>
        PathMap[x as keyof typeof PathMap].some((y: string) =>
          matchesPath(pathname, y),
        ),
      ) || pathname
    );
  }, [pathname]);

  return (
    <aside
      className={cn(
        'w-[220px] flex flex-col h-full bg-bg-base border-r border-border-default/30 select-none shrink-0',
        className,
      )}
      {...props}
    >
      {/* Logo */}
      <div className="px-5 pt-6 pb-5">
        <div className="flex items-center gap-2.5">
          <div className="size-7 rounded-lg bg-accent-primary flex items-center justify-center shrink-0">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M7 1L12.196 4V10L7 13L1.804 10V4L7 1Z" fill="white" fillOpacity="0.9"/>
            </svg>
          </div>
          <span className="text-[15px] font-semibold text-text-primary tracking-tight leading-none">
            Swipies
          </span>
        </div>
      </div>

      {/* Nav label */}
      <div className="px-5 pb-2">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-text-secondary/50">
          Menu
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 space-y-0.5 overflow-y-auto">
        {menuItems.map(({ path, name, icon: Icon, ...itemProps }) => {
          const isActive = path === activePath;

          return (
            <Link
              key={path}
              to={path}
              className={cn(
                'group flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all duration-150 relative',
                isActive
                  ? 'text-text-primary bg-bg-card'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-card/60',
              )}
              {...(itemProps as any)}
            >
              {/* Active indicator bar */}
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-full bg-accent-primary" />
              )}

              <Icon
                className={cn(
                  'size-4 shrink-0 transition-colors duration-150',
                  isActive
                    ? 'text-accent-primary'
                    : 'text-text-secondary/70 group-hover:text-text-secondary',
                )}
              />

              <span className="truncate">{t(name)}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-5 border-t border-border-default/25">
        <p className="text-[10px] text-text-secondary/40 font-medium tracking-wide">
          Swipies AI
        </p>
      </div>
    </aside>
  );
}
