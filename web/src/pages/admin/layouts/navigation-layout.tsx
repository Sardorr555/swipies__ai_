import { useContext, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { NavLink, Outlet, useNavigate } from 'react-router';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  LayoutDashboard,
  Coins,
  Gift,
  LucideMonitor,
  LucideServerCrash,
  LucideSquareUserRound,
  LucideUserCog,
  LucideUserStar,
  LucideZap,
  LucideBrain,
  Key,
  Bot,
  Megaphone,
  CreditCard,
  Sparkles,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { Routes } from '@/routes';
import { getSystemVersion, logout } from '@/services/admin-service';
import authorizationUtil from '@/utils/authorization-util';
import ThemeSwitch from '../../../components/theme-switch';
import { IS_ENTERPRISE } from '../utils';
import { CurrentUserInfoContext } from './root-layout';

interface NavGroup {
  title?: string;
  items: Array<{
    path: string;
    name: string;
    icon: React.ReactNode;
    badge?: string;
  }>;
}

const AdminNavigationLayout = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [, setCurrentUserInfo] = useContext(CurrentUserInfoContext);

  const { data: version } = useQuery({
    queryKey: ['admin/version'],
    queryFn: async () => (await getSystemVersion())?.data?.data?.version,
  });

  const navGroups: NavGroup[] = useMemo(
    () => [
      {
        title: 'CORE MANAGEMENT',
        items: [
          {
            path: Routes.AdminDashboard,
            name: 'Overview Dashboard',
            icon: <LayoutDashboard className="size-[1.1em] text-primary" />,
            badge: 'Live',
          },
          {
            path: Routes.AdminUserManagement,
            name: 'User Management',
            icon: <LucideUserCog className="size-[1.1em] text-blue-500" />,
          },
          {
            path: Routes.AdminPayments,
            name: 'Payments & Revenue',
            icon: <CreditCard className="size-[1.1em] text-emerald-500" />,
          },
          {
            path: Routes.AdminAds,
            name: 'Swipies Ads & Moderation',
            icon: <Megaphone className="size-[1.1em] text-purple-500" />,
          },
        ],
      },
      {
        title: 'SYSTEM & AI CONFIGURATION',
        items: [
          {
            path: Routes.AdminPricingSettings,
            name: 'Plans & Subscriptions',
            icon: <Coins className="size-[1.1em] text-amber-500" />,
          },
          {
            path: Routes.AdminAIManagement,
            name: 'AI Infrastructure & LLM',
            icon: <Bot className="size-[1.1em] text-indigo-500" />,
          },
          {
            path: Routes.AdminSandboxSettings,
            name: 'Sandbox Environment',
            icon: <LucideZap className="size-[1.1em] text-yellow-500" />,
          },
          {
            path: Routes.AdminServices,
            name: 'System Service Health',
            icon: <LucideServerCrash className="size-[1.1em] text-red-400" />,
          },
        ],
      },
      {
        title: 'EXTENSIONS & ENTERPRISE',
        items: [
          {
            path: Routes.AdminReferrals,
            name: 'Referral Program',
            icon: <Gift className="size-[1.1em] text-pink-500" />,
          },
          {
            path: Routes.AdminLicenses,
            name: 'License Management',
            icon: <Key className="size-[1.1em] text-cyan-500" />,
          },
          {
            path: Routes.AdminIntelligence,
            name: 'Enterprise Intelligence',
            icon: <LucideBrain className="size-[1.1em] text-teal-500" />,
          },
          ...(IS_ENTERPRISE
            ? [
                {
                  path: Routes.AdminWhitelist,
                  name: 'Registration Whitelist',
                  icon: <LucideUserStar className="size-[1.1em]" />,
                },
                {
                  path: Routes.AdminRoles,
                  name: 'Roles & Permissions',
                  icon: <LucideSquareUserRound className="size-[1.1em]" />,
                },
                {
                  path: Routes.AdminMonitoring,
                  name: 'System Monitoring',
                  icon: <LucideMonitor className="size-[1.1em]" />,
                },
              ]
            : []),
        ],
      },
    ],
    [],
  );

  const logoutMutation = useMutation({
    mutationKey: ['adminLogout'],
    mutationFn: async () => {
      await logout();
      authorizationUtil.removeAll();
      navigate('/admin/login', { replace: true });
      setCurrentUserInfo({
        userInfo: null,
        source: null,
      });
    },
    retry: false,
  });

  return (
    <main className="w-screen h-screen flex flex-row px-6 pt-6 pb-6 dark:*:focus-visible:ring-white overflow-hidden bg-background text-foreground">
      {/* Sidebar */}
      <aside className="w-72 mr-6 flex flex-col gap-4 shrink-0 h-full overflow-hidden bg-card/60 backdrop-blur-md rounded-2xl border border-border/60 p-4 shadow-sm">
        {/* Brand Header */}
        <div className="flex items-center justify-between pb-3 border-b border-border/40">
          <div className="flex items-center gap-3">
            <img className="size-8" src="/logo.svg" alt="logo" />
            <div>
              <span className="text-base font-black tracking-tight text-foreground block">
                Swipies Admin
              </span>
              <span className="text-[10px] uppercase tracking-wider font-semibold text-primary block">
                Control Hub 2.0
              </span>
            </div>
          </div>
          <Badge variant="outline" className="text-[10px] bg-primary/10 text-primary border-primary/20">
            PRO
          </Badge>
        </div>

        {/* Grouped Navigation */}
        <nav className="flex-1 overflow-y-auto pr-1 space-y-5 scrollbar-thin">
          {navGroups.map((group, gIdx) => (
            <div key={gIdx} className="space-y-1.5">
              {group.title && (
                <div className="text-[10px] font-bold tracking-wider uppercase text-muted-foreground/70 px-3 pt-1">
                  {group.title}
                </div>
              )}
              <ul className="space-y-1">
                {group.items.map((it) => (
                  <li key={it.path}>
                    <NavLink
                      to={it.path}
                      className={({ isActive }) =>
                        cn(
                          'px-3 py-2.5 rounded-xl',
                          'text-xs font-semibold w-full flex items-center justify-between text-muted-foreground',
                          'hover:bg-accent/60 hover:text-foreground',
                          'transition-all duration-200',
                          {
                            'bg-primary/15 text-primary font-bold shadow-xs': isActive,
                          },
                        )
                      }
                    >
                      <div className="flex items-center gap-2.5">
                        {it.icon}
                        <span>{it.name}</span>
                      </div>
                      {it.badge && (
                        <Badge variant="outline" className="text-[9px] px-1.5 py-0 bg-emerald-500/10 text-emerald-600 border-emerald-500/30">
                          {it.badge}
                        </Badge>
                      )}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        {/* Footer info & Logout */}
        <div className="mt-auto space-y-3 pt-3 border-t border-border/40">
          <div className="flex justify-between items-center px-1">
            <span className="leading-none text-[11px] font-mono text-muted-foreground">
              v{version || '1.0.0'}
            </span>

            <ThemeSwitch />
          </div>

          <Button
            size="sm"
            variant="outline"
            className="w-full text-xs font-semibold h-8 rounded-xl border-destructive/30 text-destructive hover:bg-destructive/10"
            onClick={() => logoutMutation.mutate()}
          >
            Logout
          </Button>
        </div>
      </aside>

      {/* Main Content Viewport */}
      <section className="flex-1 h-full min-w-0 overflow-y-auto pr-1">
        <Outlet />
      </section>
    </main>
  );
};

export default AdminNavigationLayout;
