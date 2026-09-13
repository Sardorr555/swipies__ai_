import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation } from 'react-router';
import {
  ChevronLeft,
  ChevronRight,
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

export const SIDEBAR_WIDTH_KEY = 'swipies_left_sidebar_width';
export const SIDEBAR_COLLAPSED_KEY = 'swipies_left_sidebar_collapsed';

export const MIN_SIDEBAR_WIDTH = 180;
export const MAX_SIDEBAR_WIDTH = 460;
export const DEFAULT_SIDEBAR_WIDTH = 220;
export const COLLAPSED_SIDEBAR_WIDTH = 64;
export const COLLAPSE_TRIGGER_WIDTH = 125;

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

  const [width, setWidth] = useState<number>(() => {
    if (typeof window === 'undefined') return DEFAULT_SIDEBAR_WIDTH;
    const saved = localStorage.getItem(SIDEBAR_WIDTH_KEY);
    const parsed = saved ? parseInt(saved, 10) : DEFAULT_SIDEBAR_WIDTH;
    return !isNaN(parsed) && parsed >= MIN_SIDEBAR_WIDTH && parsed <= MAX_SIDEBAR_WIDTH
      ? parsed
      : DEFAULT_SIDEBAR_WIDTH;
  });

  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true';
  });

  const [isDragging, setIsDragging] = useState<boolean>(false);
  const lastExpandedWidthRef = useRef<number>(width);

  // Sync lastExpandedWidthRef and persist width
  useEffect(() => {
    if (!isCollapsed && width >= MIN_SIDEBAR_WIDTH) {
      lastExpandedWidthRef.current = width;
      localStorage.setItem(SIDEBAR_WIDTH_KEY, String(width));
    }
  }, [width, isCollapsed]);

  // Persist collapsed state
  useEffect(() => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(isCollapsed));
  }, [isCollapsed]);

  const toggleCollapse = useCallback(() => {
    setIsCollapsed((prev) => {
      const next = !prev;
      if (!next) {
        setWidth(lastExpandedWidthRef.current || DEFAULT_SIDEBAR_WIDTH);
      }
      return next;
    });
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  // Handle mouse drag resizing
  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const clientX = e.clientX;
      if (clientX < COLLAPSE_TRIGGER_WIDTH) {
        setIsCollapsed(true);
      } else {
        const clamped = Math.min(Math.max(clientX, MIN_SIDEBAR_WIDTH), MAX_SIDEBAR_WIDTH);
        setIsCollapsed(false);
        setWidth(clamped);
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging]);

  const activePath = useMemo(() => {
    return (
      Object.keys(PathMap).find((x: string) =>
        PathMap[x as keyof typeof PathMap].some((y: string) =>
          matchesPath(pathname, y),
        ),
      ) || pathname
    );
  }, [pathname]);

  const currentWidth = isCollapsed ? COLLAPSED_SIDEBAR_WIDTH : width;

  return (
    <TooltipProvider delayDuration={150}>
      <aside
        style={{ width: `${currentWidth}px` }}
        className={cn(
          'flex flex-col h-full bg-bg-base border-r border-border-default/30 select-none shrink-0 relative z-20',
          !isDragging && 'transition-[width] duration-200 ease-out',
          className,
        )}
        {...props}
      >
        {/* Header / Logo */}
        {!isCollapsed ? (
          <div className="px-4 pt-5 pb-4 flex items-center justify-between gap-2">
            <Link to={Routes.Root} className="flex items-center gap-2.5 min-w-0">
              <img src="/logo.svg" className="size-7 shrink-0" alt="Swipies Logo" />
              <span className="text-[15px] font-semibold text-text-primary tracking-tight leading-none truncate">
                Swipies
              </span>
            </Link>
            <button
              type="button"
              onClick={toggleCollapse}
              title="Свернуть боковую панель"
              aria-label="Свернуть боковую панель"
              className="p-1 rounded-md text-text-secondary hover:text-text-primary hover:bg-bg-card transition-colors shrink-0"
            >
              <ChevronLeft className="size-4" />
            </button>
          </div>
        ) : (
          <div className="pt-5 pb-4 flex flex-col items-center gap-2.5">
            <Link to={Routes.Root} title="Swipies AI" className="flex items-center justify-center">
              <img src="/logo.svg" className="size-7 shrink-0" alt="Swipies Logo" />
            </Link>
            <button
              type="button"
              onClick={toggleCollapse}
              title="Развернуть боковую панель"
              aria-label="Развернуть боковую панель"
              className="p-1 rounded-md text-text-secondary hover:text-text-primary hover:bg-bg-card transition-colors"
            >
              <ChevronRight className="size-4" />
            </button>
          </div>
        )}

        {/* Nav section label (visible only when expanded) */}
        {!isCollapsed && (
          <div className="px-4 pb-2">
            <span className="text-[10px] font-semibold uppercase tracking-widest text-text-secondary/50">
              Menu
            </span>
          </div>
        )}

        {/* Navigation items */}
        <nav
          className={cn(
            'flex-1 space-y-1 overflow-y-auto overflow-x-hidden',
            isCollapsed ? 'px-2' : 'px-3',
          )}
        >
          {menuItems.map(({ path, name, icon: Icon, ...itemProps }) => {
            const isActive = path === activePath;
            const labelText = t(name);

            if (isCollapsed) {
              return (
                <Tooltip key={path}>
                  <TooltipTrigger asChild>
                    <Link
                      to={path}
                      className={cn(
                        'group flex items-center justify-center size-10 mx-auto rounded-lg text-[13px] font-medium transition-all duration-150 relative',
                        isActive
                          ? 'text-text-primary bg-bg-card'
                          : 'text-text-secondary hover:text-text-primary hover:bg-bg-card/60',
                      )}
                      {...(itemProps as any)}
                    >
                      {/* Active indicator */}
                      {isActive && (
                        <span className="absolute left-0.5 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-full bg-accent-primary" />
                      )}

                      <Icon
                        className={cn(
                          'size-4 shrink-0 transition-colors duration-150',
                          isActive
                            ? 'text-accent-primary'
                            : 'text-text-secondary/70 group-hover:text-text-secondary',
                        )}
                      />
                      <span className="sr-only">{labelText}</span>
                    </Link>
                  </TooltipTrigger>
                  <TooltipContent side="right" sideOffset={10} className="font-medium text-xs">
                    {labelText}
                  </TooltipContent>
                </Tooltip>
              );
            }

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

                <span className="truncate">{labelText}</span>
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        {!isCollapsed ? (
          <div className="px-4 py-4 border-t border-border-default/25">
            <p className="text-[10px] text-text-secondary/40 font-medium tracking-wide">
              Swipies AI
            </p>
          </div>
        ) : (
          <div className="py-3.5 border-t border-border-default/25 flex items-center justify-center">
            <span className="text-[9px] text-text-secondary/40 font-semibold tracking-wider uppercase">
              AI
            </span>
          </div>
        )}

        {/* Draggable resize handle on the right edge */}
        <div
          role="separator"
          aria-orientation="vertical"
          tabIndex={0}
          onMouseDown={handleMouseDown}
          onDoubleClick={toggleCollapse}
          title={
            isCollapsed
              ? 'Дважды кликните, чтобы развернуть, или потяните вправо'
              : 'Потяните, чтобы изменить размер, или дважды кликните, чтобы свернуть'
          }
          className={cn(
            'absolute top-0 -right-1.5 bottom-0 w-3 cursor-col-resize z-30 flex items-center justify-center group',
            isDragging && 'cursor-col-resize',
          )}
        >
          {/* Subtle line indicator */}
          <div
            className={cn(
              'w-[2px] h-full transition-colors duration-150',
              isDragging
                ? 'bg-blue-500 shadow-sm'
                : 'bg-transparent group-hover:bg-blue-500/60',
            )}
          />
          {/* Subtle grab pill in the middle on hover */}
          <div
            className={cn(
              'absolute w-1 h-6 rounded-full transition-opacity duration-150 pointer-events-none',
              isDragging
                ? 'bg-blue-500 opacity-100'
                : 'bg-border-default/80 opacity-0 group-hover:opacity-100',
            )}
          />
        </div>
      </aside>
    </TooltipProvider>
  );
}
