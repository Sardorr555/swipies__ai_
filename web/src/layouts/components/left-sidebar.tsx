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

export function LeftSidebar({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
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
        'w-[240px] flex flex-col h-full bg-bg-component border-r border-border-default/40 select-none shrink-0',
        className
      )}
      {...props}
    >
      {/* Sidebar Header */}
      <div className="flex items-center gap-3 px-6 py-[22px] border-b border-border-default/40">
        <div className="flex items-center justify-center size-8 bg-accent-primary/10 rounded-lg text-accent-primary font-bold text-lg">
          S
        </div>
        <span className="font-bold text-lg text-text-primary tracking-tight">Navigation</span>
      </div>

      {/* Navigation Links */}
      <nav className="flex-grow py-6 px-4 space-y-1.5 overflow-y-auto">
        {menuItems.map(({ path, name, icon: Icon, ...itemProps }) => {
          const isActive = path === activePath;

          return (
            <Link
              key={path}
              to={path}
              className={cn(
                'flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 group relative',
                isActive
                  ? 'bg-accent-primary text-white shadow-md shadow-accent-primary/25'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-card'
              )}
              {...(itemProps as any)}
            >
              <Icon
                className={cn(
                  'size-[18px] transition-transform duration-200 group-hover:scale-110',
                  isActive ? 'text-white' : 'text-text-secondary group-hover:text-text-primary'
                )}
              />
              <span className="truncate">{t(name)}</span>

              {/* Subtle hover line/dot */}
              {isActive && (
                <div className="absolute right-3 w-1.5 h-1.5 rounded-full bg-white" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Sidebar Footer */}
      <div className="p-4 border-t border-border-default/40">
        <p className="text-[10px] text-text-secondary text-center font-semibold text-accent-primary">
          Swipies AI Commercial Edition
        </p>
      </div>
    </aside>
  );
}
