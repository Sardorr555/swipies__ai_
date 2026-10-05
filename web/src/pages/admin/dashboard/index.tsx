import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import {
  Users,
  UserCheck,
  UserX,
  CreditCard,
  DollarSign,
  TrendingUp,
  Activity,
  Calendar,
  RefreshCw,
  ArrowUpRight,
  ShieldCheck,
  Sparkles,
  Zap,
  Gift,
  Coins,
  Megaphone,
  Bot,
  Layers,
  ArrowRight,
  ChevronRight,
  CheckCircle2,
  Clock,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Routes } from '@/routes';
import { getDashboardOverview } from '@/services/admin-service';

const PLAN_COLORS: Record<string, string> = {
  free: '#94a3b8',
  standard: '#3b82f6',
  plus: '#06b6d4',
  pro: '#8b5cf6',
  enterprise: '#f59e0b',
  ads_deposit: '#10b981',
  deposit: '#10b981',
  other: '#64748b',
};

const CHANNEL_COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899', '#06b6d4'];

const formatUZS = (val?: number | null) => {
  if (val === undefined || val === null) return '0 UZS';
  return `${Number(val).toLocaleString('uz-UZ')} UZS`;
};

const formatUSD = (val?: number | null) => {
  if (val === undefined || val === null) return '$0.00';
  return `$${Number(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

export default function AdminDashboardOverview() {
  const navigate = useNavigate();
  const [revenuePeriod, setRevenuePeriod] = useState<'daily' | 'weekly' | 'monthly'>('daily');

  const {
    data: overviewRes,
    isLoading,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: ['admin/dashboard/overview'],
    queryFn: async () => {
      const res = await getDashboardOverview();
      return res?.data?.data || res?.data || res;
    },
    refetchInterval: 30000,
  });

  const data = overviewRes as AdminService.DashboardOverviewData | undefined;

  const userStats = data?.user_stats;
  const revenueStats = data?.revenue_stats;
  const subStats = data?.subscription_stats;
  const recentUsers = data?.recent_users || [];
  const recentPayments = data?.recent_payments || [];

  // Prepare Plan Breakdown Data for Pie Chart
  const planChartData = useMemo(() => {
    if (!subStats?.plan_breakdown) return [];
    return Object.entries(subStats.plan_breakdown).map(([plan, item]) => ({
      name: plan.toUpperCase(),
      count: item.count,
      revenue: item.revenue_uzs,
      paid_count: item.paid_count,
    }));
  }, [subStats]);

  // Prepare Login Channels Data for Pie Chart
  const channelChartData = useMemo(() => {
    if (!userStats?.login_channels) return [];
    return Object.entries(userStats.login_channels).map(([channel, count]) => ({
      name: channel.toUpperCase(),
      value: count,
    }));
  }, [userStats]);

  // Revenue chart data depending on active period
  const activeRevenueChartData = useMemo(() => {
    if (!revenueStats) return [];
    if (revenuePeriod === 'weekly') {
      return revenueStats.weekly_revenue_trend || [];
    }
    if (revenuePeriod === 'monthly') {
      return revenueStats.monthly_revenue_trend || [];
    }
    return (revenueStats.daily_revenue_trend || []).slice(-14);
  }, [revenueStats, revenuePeriod]);

  const activeXKey = revenuePeriod === 'weekly' ? 'week' : revenuePeriod === 'monthly' ? 'month' : 'date';

  return (
    <div className="space-y-6 pb-12">
      {/* 1. Header & Top Control Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-primary/10 via-primary/5 to-transparent border border-primary/20 backdrop-blur-sm shadow-sm">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-semibold uppercase tracking-wider text-primary">
              Live Operations & Analytics Hub
            </span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-foreground sm:text-3xl">
            Swipies AI — Core Analytics & System Telemetry
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time analytics for user acquisition, platform activity, subscription plans, and revenue streams
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="h-9 gap-2 shadow-sm font-medium"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin text-primary' : ''}`} />
            {isFetching ? 'Refreshing...' : 'Refresh'}
          </Button>

          <Button
            size="sm"
            onClick={() => navigate(Routes.AdminPayments)}
            className="h-9 gap-2 bg-primary text-primary-foreground font-semibold shadow-md shadow-primary/20 hover:shadow-lg transition-all"
          >
            <CreditCard className="h-4 w-4" />
            Payments & Transactions
          </Button>
        </div>
      </div>

      {/* 2. Top Metric KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Users Card */}
        <Card className="relative overflow-hidden border border-border/60 hover:border-primary/40 transition-all shadow-sm group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/10 rounded-full blur-2xl group-hover:bg-blue-500/20 transition-all" />
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              Total Registered Users
            </CardTitle>
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400">
              <Users className="h-5 w-5" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-black tracking-tight text-foreground">
              {isLoading ? '...' : (userStats?.total_users ?? 0).toLocaleString()}
            </div>
            <div className="flex items-center gap-2 mt-2 text-xs">
              <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 font-medium">
                <UserCheck className="h-3 w-3 mr-1" /> {userStats?.active_users ?? 0} active
              </Badge>
              <Badge variant="outline" className="bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/20 font-medium">
                <UserX className="h-3 w-3 mr-1" /> {userStats?.inactive_users ?? 0} inactive
              </Badge>
            </div>
            <div className="mt-3 pt-3 border-t border-border/40 text-[11px] text-muted-foreground flex justify-between">
              <span>Today: <b>+{userStats?.new_users_today ?? 0}</b></span>
              <span>7 Days: <b>+{userStats?.new_users_this_week ?? 0}</b></span>
              <span>30 Days: <b>+{userStats?.new_users_this_month ?? 0}</b></span>
            </div>
          </CardContent>
        </Card>

        {/* Total Revenue Card */}
        <Card className="relative overflow-hidden border border-border/60 hover:border-emerald-500/40 transition-all shadow-sm group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/10 rounded-full blur-2xl group-hover:bg-emerald-500/20 transition-all" />
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              Total Gross Revenue
            </CardTitle>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <DollarSign className="h-5 w-5" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-black tracking-tight text-foreground truncate" title={formatUZS(revenueStats?.total_revenue_uzs)}>
              {isLoading ? '...' : formatUZS(revenueStats?.total_revenue_uzs)}
            </div>
            <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 mt-1 flex items-center gap-1">
              <TrendingUp className="h-3.5 w-3.5" />
              {formatUSD(revenueStats?.total_revenue_usd)} USD Equivalent
            </div>
            <div className="mt-3 pt-3 border-t border-border/40 text-[11px] text-muted-foreground flex justify-between">
              <span>Today: <b>{formatUZS(revenueStats?.revenue_today_uzs)}</b></span>
              <span>This Month: <b>{formatUZS(revenueStats?.revenue_this_month_uzs)}</b></span>
            </div>
          </CardContent>
        </Card>

        {/* Paying Users & Conversion Card */}
        <Card className="relative overflow-hidden border border-border/60 hover:border-purple-500/40 transition-all shadow-sm group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/10 rounded-full blur-2xl group-hover:bg-purple-500/20 transition-all" />
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              Paying Customers
            </CardTitle>
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400">
              <CreditCard className="h-5 w-5" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-black tracking-tight text-foreground">
              {isLoading ? '...' : (revenueStats?.paying_users_count ?? 0).toLocaleString()}
            </div>
            <div className="flex items-center gap-2 mt-2 text-xs">
              <Badge variant="outline" className="bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20 font-medium">
                Conversion: {revenueStats?.conversion_rate_pct ?? 0}%
              </Badge>
              <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20 font-medium">
                {revenueStats?.paid_transactions_count ?? 0} paid orders
              </Badge>
            </div>
            <div className="mt-3 pt-3 border-t border-border/40 text-[11px] text-muted-foreground flex justify-between">
              <span>Average Revenue Per Paying User (ARPPU):</span>
              <span className="font-bold text-foreground">{formatUZS(revenueStats?.arppu_uzs)}</span>
            </div>
          </CardContent>
        </Card>

        {/* User Activity & Connections Card */}
        <Card className="relative overflow-hidden border border-border/60 hover:border-amber-500/40 transition-all shadow-sm group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/10 rounded-full blur-2xl group-hover:bg-amber-500/20 transition-all" />
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              Active Users & Engagement
            </CardTitle>
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400">
              <Activity className="h-5 w-5" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-black tracking-tight text-foreground">
              {isLoading ? '...' : (userStats?.active_today ?? 0).toLocaleString()}
              <span className="text-xs font-normal text-muted-foreground ml-1.5">Active Today (DAU)</span>
            </div>
            <div className="flex items-center gap-2 mt-2 text-xs">
              <Badge variant="outline" className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20 font-medium">
                Weekly: {userStats?.active_7d ?? 0} (WAU)
              </Badge>
              <Badge variant="outline" className="bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20 font-medium">
                Monthly: {userStats?.active_30d ?? 0} (MAU)
              </Badge>
            </div>
            <div className="mt-3 pt-3 border-t border-border/40 text-[11px] text-muted-foreground flex justify-between items-center">
              <span>Superadmins: <b>{userStats?.superuser_count ?? 0}</b></span>
              <span className="text-primary hover:underline cursor-pointer flex items-center gap-0.5" onClick={() => navigate(Routes.AdminUserManagement)}>
                Manage <ChevronRight className="h-3 w-3" />
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 3. Main Visual Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: User Growth & Revenue Trends */}
        <div className="lg:col-span-2 space-y-6">
          {/* Revenue Trends Chart Card */}
          <Card className="border border-border/60 shadow-sm">
            <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2">
              <div>
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-emerald-500" />
                  Revenue Inflow & Financial Trends
                </CardTitle>
                <CardDescription className="text-xs">
                  Inspect daily, weekly, and monthly gross revenue dynamics
                </CardDescription>
              </div>

              <div className="flex items-center gap-1 bg-muted/60 p-1 rounded-xl border border-border/40">
                <Button
                  size="sm"
                  variant={revenuePeriod === 'daily' ? 'default' : 'ghost'}
                  onClick={() => setRevenuePeriod('daily')}
                  className="h-7 text-xs px-3 rounded-lg font-medium"
                >
                  Daily (14d)
                </Button>
                <Button
                  size="sm"
                  variant={revenuePeriod === 'weekly' ? 'default' : 'ghost'}
                  onClick={() => setRevenuePeriod('weekly')}
                  className="h-7 text-xs px-3 rounded-lg font-medium"
                >
                  Weekly (8w)
                </Button>
                <Button
                  size="sm"
                  variant={revenuePeriod === 'monthly' ? 'default' : 'ghost'}
                  onClick={() => setRevenuePeriod('monthly')}
                  className="h-7 text-xs px-3 rounded-lg font-medium"
                >
                  Monthly (6m)
                </Button>
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={activeRevenueChartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="revenueBarGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.9} />
                        <stop offset="100%" stopColor="#059669" stopOpacity={0.4} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.15} vertical={false} />
                    <XAxis dataKey={activeXKey} tick={{ fontSize: 11 }} />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      tickFormatter={(v) => v >= 1000000 ? `${(v / 1000000).toFixed(1)}M` : v >= 1000 ? `${(v / 1000).toFixed(0)}K` : v}
                    />
                    <Tooltip
                      formatter={(val: any) => [formatUZS(val), 'Revenue']}
                      labelFormatter={(label) => `Period: ${label}`}
                      contentStyle={{ borderRadius: '12px', background: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: '12px' }}
                    />
                    <Bar dataKey="revenue_uzs" fill="url(#revenueBarGrad)" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* User Registrations Trend Card */}
          <Card className="border border-border/60 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <Users className="h-4 w-4 text-blue-500" />
                New User Registration Trajectory (30 Days)
              </CardTitle>
              <CardDescription className="text-xs">
                Daily new user accounts registered on Swipies AI
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={userStats?.daily_registration_trend || []} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="userGrowthGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.15} vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                    <Tooltip
                      formatter={(val: any) => [`${val} users`, 'New Registrations']}
                      labelFormatter={(label) => `Date: ${label}`}
                      contentStyle={{ borderRadius: '12px', background: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: '12px' }}
                    />
                    <Area type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2.5} fill="url(#userGrowthGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right 1 Col: Distribution & Channels */}
        <div className="space-y-6">
          {/* Subscription & Plans Breakdown Card */}
          <Card className="border border-border/60 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <Coins className="h-4 w-4 text-purple-500" />
                Plan & Subscription Distribution
              </CardTitle>
              <CardDescription className="text-xs">
                Active user breakdown across subscription tiers
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-48 w-full flex items-center justify-center">
                {planChartData.length === 0 ? (
                  <div className="text-xs text-muted-foreground">No data available</div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={planChartData}
                        dataKey="count"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={45}
                        outerRadius={70}
                        paddingAngle={3}
                      >
                        {planChartData.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={PLAN_COLORS[entry.name.toLowerCase()] || CHANNEL_COLORS[index % CHANNEL_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(val: any, name: any, props: any) => [
                          `${val} users (${formatUZS(props?.payload?.revenue)})`,
                          name,
                        ]}
                        contentStyle={{ borderRadius: '12px', background: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: '12px' }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>

              <div className="space-y-2 mt-2 pt-2 border-t border-border/40 text-xs">
                {planChartData.map((item, idx) => (
                  <div key={item.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: PLAN_COLORS[item.name.toLowerCase()] || CHANNEL_COLORS[idx % CHANNEL_COLORS.length] }}
                      />
                      <span className="font-semibold">{item.name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-muted-foreground">{item.count} users</span>
                      <span className="font-medium text-foreground">{formatUZS(item.revenue)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Login Channels Breakdown Card */}
          <Card className="border border-border/60 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-500" />
                Authentication Channels & Providers
              </CardTitle>
              <CardDescription className="text-xs">
                Distribution of user signup & authentication methods
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 pt-2">
                {channelChartData.map((ch, idx) => {
                  const total = userStats?.total_users || 1;
                  const pct = Math.round((ch.value / total) * 100);
                  return (
                    <div key={ch.name} className="space-y-1">
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-foreground">{ch.name}</span>
                        <span className="text-muted-foreground">{ch.value} ({pct}%)</span>
                      </div>
                      <div className="h-2 w-full bg-muted/60 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${pct}%`,
                            backgroundColor: CHANNEL_COLORS[idx % CHANNEL_COLORS.length],
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Quick Navigation Action Box */}
              <div className="mt-6 p-4 rounded-xl bg-muted/40 border border-border/60 space-y-3">
                <div className="text-xs font-bold text-foreground">Quick Admin Shortcuts</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <Button
                    variant="outline"
                    size="sm"
                    className="justify-start h-8 text-[11px] font-medium"
                    onClick={() => navigate(Routes.AdminUserManagement)}
                  >
                    <Users className="h-3.5 w-3.5 mr-1 text-blue-500" /> Users
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="justify-start h-8 text-[11px] font-medium"
                    onClick={() => navigate(Routes.AdminPayments)}
                  >
                    <CreditCard className="h-3.5 w-3.5 mr-1 text-emerald-500" /> Payments
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="justify-start h-8 text-[11px] font-medium"
                    onClick={() => navigate(Routes.AdminAds)}
                  >
                    <Megaphone className="h-3.5 w-3.5 mr-1 text-purple-500" /> Swipies Ads
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="justify-start h-8 text-[11px] font-medium"
                    onClick={() => navigate(Routes.AdminPricingSettings)}
                  >
                    <Coins className="h-3.5 w-3.5 mr-1 text-amber-500" /> Pricing Plans
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 4. Recent Activities Tables Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Registered Users Table */}
        <Card className="border border-border/60 shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <Users className="h-4 w-4 text-primary" />
                Recently Registered Users
              </CardTitle>
              <CardDescription className="text-xs">
                Latest 10 registered user accounts and timestamps
              </CardDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs font-semibold text-primary hover:bg-primary/10 gap-1"
              onClick={() => navigate(Routes.AdminUserManagement)}
            >
              View All <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-muted/50 border-y border-border/40 text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">
                  <tr>
                    <th className="px-4 py-2.5">User</th>
                    <th className="px-4 py-2.5">Registered At</th>
                    <th className="px-4 py-2.5">Plan</th>
                    <th className="px-4 py-2.5 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30">
                  {recentUsers.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                        No user records found
                      </td>
                    </tr>
                  ) : (
                    recentUsers.map((u) => (
                      <tr key={u.id} className="hover:bg-muted/30 transition-colors">
                        <td className="px-4 py-3">
                          <div className="font-bold text-foreground">{u.nickname || 'User'}</div>
                          <div className="text-[11px] text-muted-foreground font-mono truncate max-w-[180px]">
                            {u.email}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                          {u.create_date || '—'}
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant="outline" className="text-[10px] uppercase font-bold">
                            {u.plan_type}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Badge
                            variant="outline"
                            className={
                              u.is_active
                                ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
                                : 'bg-red-500/10 text-red-500 border-red-500/30'
                            }
                          >
                            {u.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Recent Payments Table */}
        <Card className="border border-border/60 shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <CreditCard className="h-4 w-4 text-emerald-500" />
                Recent Payment Transactions
              </CardTitle>
              <CardDescription className="text-xs">
                Latest orders and subscription payments
              </CardDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs font-semibold text-primary hover:bg-primary/10 gap-1"
              onClick={() => navigate(Routes.AdminPayments)}
            >
              View All <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-muted/50 border-y border-border/40 text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">
                  <tr>
                    <th className="px-4 py-2.5">User / Plan</th>
                    <th className="px-4 py-2.5">Amount</th>
                    <th className="px-4 py-2.5">Date</th>
                    <th className="px-4 py-2.5 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30">
                  {recentPayments.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                        No payment transactions found
                      </td>
                    </tr>
                  ) : (
                    recentPayments.map((p) => (
                      <tr key={p.id} className="hover:bg-muted/30 transition-colors">
                        <td className="px-4 py-3">
                          <div className="font-semibold text-foreground truncate max-w-[180px]">
                            {p.user_email || p.user_id}
                          </div>
                          <div className="text-[10px] uppercase font-bold text-muted-foreground">
                            {p.plan_type}
                          </div>
                        </td>
                        <td className="px-4 py-3 font-bold text-foreground whitespace-nowrap">
                          {formatUZS(p.amount_uzs)}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                          {p.create_date || '—'}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Badge
                            variant="outline"
                            className={
                              p.status === 'PAID'
                                ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
                                : p.status === 'PENDING'
                                ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30'
                                : 'bg-red-500/10 text-red-500 border-red-500/30'
                            }
                          >
                            {p.status}
                          </Badge>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
