import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  Users,
  Clock,
  MousePointerClick,
  Layers,
  Flame,
  RefreshCw,
  Search,
  MessageSquare,
  Database,
  Workflow,
  Link2,
  FolderOpen,
  Settings,
  Megaphone,
  ShieldCheck,
  TrendingUp,
  Box,
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
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  getUserActivityOverview,
  getUserActivityModules,
  getUserActivityClicks,
  getUserActivityUsers,
  getUserActivityTimeline,
  getUserActivityEvents,
  getUserActivityFeatures,
} from '@/services/admin-service';

const MODULE_COLORS: Record<string, string> = {
  chat: '#3b82f6', // blue
  datasets: '#10b981', // emerald
  agent_canvas: '#8b5cf6', // purple
  crm: '#f59e0b', // amber
  search: '#06b6d4', // cyan
  files_skills: '#ec4899', // pink
  settings: '#64748b', // slate
  ads: '#d946ef', // fuchsia
  admin: '#ef4444', // red
  other: '#94a3b8', // gray
};

const getModuleIcon = (module: string) => {
  switch (module) {
    case 'chat':
      return <MessageSquare className="size-4 text-blue-500" />;
    case 'datasets':
      return <Database className="size-4 text-emerald-500" />;
    case 'agent_canvas':
      return <Workflow className="size-4 text-purple-500" />;
    case 'crm':
      return <Link2 className="size-4 text-amber-500" />;
    case 'search':
      return <Search className="size-4 text-cyan-500" />;
    case 'files_skills':
      return <FolderOpen className="size-4 text-pink-500" />;
    case 'settings':
      return <Settings className="size-4 text-slate-500" />;
    case 'ads':
      return <Megaphone className="size-4 text-fuchsia-500" />;
    case 'admin':
      return <ShieldCheck className="size-4 text-red-500" />;
    default:
      return <Layers className="size-4 text-muted-foreground" />;
  }
};

const formatSeconds = (sec?: number) => {
  if (!sec || sec <= 0) return '0 soniya';
  if (sec < 60) return `${Math.round(sec)} soniya`;
  const mins = Math.floor(sec / 60);
  const remainingSec = Math.round(sec % 60);
  if (mins < 60) return `${mins} daq ${remainingSec} son`;
  const hours = Math.floor(mins / 60);
  const remainingMins = mins % 60;
  return `${hours} soat ${remainingMins} daq`;
};

export default function AdminUserActivityPage() {
  const [days, setDays] = useState<number>(7);
  const [userSearch, setUserSearch] = useState<string>('');
  const [selectedModuleFilter, setSelectedModuleFilter] = useState<string>('all');
  const [selectedEventFilter, setSelectedEventFilter] = useState<string>('all');

  // 1. Overview Query
  const {
    data: overviewRes,
    isLoading: isOverviewLoading,
    refetch: refetchOverview,
  } = useQuery({
    queryKey: ['admin/user-activity/overview', days],
    queryFn: async () => (await getUserActivityOverview(days))?.data?.data,
    refetchInterval: 30000,
  });

  // 2. Modules Breakdown Query
  const { data: modulesRes, refetch: refetchModules } = useQuery({
    queryKey: ['admin/user-activity/modules', days],
    queryFn: async () => (await getUserActivityModules(days))?.data?.data || [],
    refetchInterval: 30000,
  });

  // 3. Top Clicks Query
  const { data: clicksRes, refetch: refetchClicks } = useQuery({
    queryKey: ['admin/user-activity/clicks', days],
    queryFn: async () => (await getUserActivityClicks(days, 30))?.data?.data || [],
    refetchInterval: 30000,
  });

  // 4. Users Leaderboard Query
  const { data: usersRes, refetch: refetchUsers } = useQuery({
    queryKey: ['admin/user-activity/users', days, userSearch],
    queryFn: async () => (await getUserActivityUsers({ days, search: userSearch, page: 1, page_size: 20 }))?.data?.data,
    refetchInterval: 30000,
  });

  // 5. Timeline Query
  const { data: timelineRes, refetch: refetchTimeline } = useQuery({
    queryKey: ['admin/user-activity/timeline', days],
    queryFn: async () => (await getUserActivityTimeline(days))?.data?.data || [],
    refetchInterval: 30000,
  });

  // 6. Raw Events Query
  const { data: eventsRes, refetch: refetchEvents } = useQuery({
    queryKey: ['admin/user-activity/events', selectedModuleFilter, selectedEventFilter],
    queryFn: async () =>
      (
        await getUserActivityEvents({
          page: 1,
          page_size: 30,
          module: selectedModuleFilter !== 'all' ? selectedModuleFilter : undefined,
          event_type: selectedEventFilter !== 'all' ? selectedEventFilter : undefined,
        })
      )?.data?.data?.items || [],
    refetchInterval: 15000,
  });

  // 7. Features Matrix Query
  const { data: featuresRes, refetch: refetchFeatures } = useQuery({
    queryKey: ['admin/user-activity/features', days],
    queryFn: async () => (await getUserActivityFeatures(days))?.data?.data || [],
    refetchInterval: 30000,
  });

  const handleRefreshAll = () => {
    refetchOverview();
    refetchModules();
    refetchClicks();
    refetchUsers();
    refetchTimeline();
    refetchEvents();
    refetchFeatures();
  };

  const overview = overviewRes || {};
  const modulesList = modulesRes || [];
  const clicksList = clicksRes || [];
  const usersList = usersRes?.items || [];
  const timelineList = timelineRes || [];
  const rawEventsList = eventsRes || [];
  const featuresList = featuresRes || [];

  // Pie chart data for module time share
  const pieChartData = useMemo(() => {
    return (modulesRes || []).map((m: any) => ({
      name: m.module_name || m.module,
      value: m.total_time_minutes || 0,
      share: m.share_percentage || 0,
      color: MODULE_COLORS[m.module] || '#94a3b8',
    }));
  }, [modulesRes]);

  // Top clicks for bar chart
  const topClicksChartData = useMemo(() => {
    return (clicksRes || []).slice(0, 8).map((c: any) => ({
      name: c.label.length > 18 ? c.label.substring(0, 16) + '...' : c.label,
      clicks: c.click_count,
      users: c.unique_users,
    }));
  }, [clicksRes]);

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto pr-2 space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-border/60">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Foydalanuvchilar Faoliyati & Telemetriya
            </h1>
            <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/30 text-xs">
              Live Monitoring
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Foydalanuvchilar qaysi bo‘limlarni ko‘proq ishlatayotgani, qancha vaqt o‘tkazayotgani va qanday tugmalarni bosayotganini real vaqtda tahlil qilish.
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex items-center gap-2 self-start md:self-auto">
          <div className="bg-muted/70 p-1 rounded-xl flex items-center border border-border/50 text-xs">
            <button
              onClick={() => setDays(1)}
              className={`px-3 py-1.5 rounded-lg transition-all font-medium ${days === 1 ? 'bg-background shadow-xs text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            >
              Bugun
            </button>
            <button
              onClick={() => setDays(7)}
              className={`px-3 py-1.5 rounded-lg transition-all font-medium ${days === 7 ? 'bg-background shadow-xs text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            >
              7 kun
            </button>
            <button
              onClick={() => setDays(30)}
              className={`px-3 py-1.5 rounded-lg transition-all font-medium ${days === 30 ? 'bg-background shadow-xs text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            >
              30 kun
            </button>
            <button
              onClick={() => setDays(365)}
              className={`px-3 py-1.5 rounded-lg transition-all font-medium ${days === 365 ? 'bg-background shadow-xs text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            >
              Barchasi
            </button>
          </div>

          <Button variant="outline" size="sm" onClick={handleRefreshAll} className="gap-2">
            <RefreshCw className={`size-3.5 ${isOverviewLoading ? 'animate-spin' : ''}`} />
            Yangilash
          </Button>
        </div>
      </div>

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Active Users */}
        <Card className="bg-card/70 border-border/60 shadow-xs relative overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Aktiv Foydalanuvchilar
            </CardTitle>
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500">
              <Users className="size-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {overview.active_users_period || 0}
            </div>
            <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground">
              <Badge variant="secondary" className="px-1.5 py-0 text-[10px] bg-blue-500/15 text-blue-500">
                DAU: {overview.dau || 0}
              </Badge>
              <span>tanlangan davrda</span>
            </div>
          </CardContent>
        </Card>

        {/* Card 2: Total Clicks & Actions */}
        <Card className="bg-card/70 border-border/60 shadow-xs relative overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Jami Kliklar & Harakatlar
            </CardTitle>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500">
              <MousePointerClick className="size-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {(overview.total_actions || 0).toLocaleString()}
            </div>
            <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground">
              <span className="text-emerald-500 font-medium">
                {(overview.total_clicks || 0).toLocaleString()} ta klik
              </span>
              <span>• {(overview.total_page_views || 0).toLocaleString()} ta sahifa</span>
            </div>
          </CardContent>
        </Card>

        {/* Card 3: Avg Time on Platform */}
        <Card className="bg-card/70 border-border/60 shadow-xs relative overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              O‘rtacha Vaqt / Foydalanuvchi
            </CardTitle>
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-500">
              <Clock className="size-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {formatSeconds(overview.avg_time_per_user_seconds)}
            </div>
            <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground">
              <span>Jami platforma vaqti:</span>
              <span className="font-medium text-foreground">{overview.total_time_spent_hours || 0} soat</span>
            </div>
          </CardContent>
        </Card>

        {/* Card 4: Top Platform Module */}
        <Card className="bg-card/70 border-border/60 shadow-xs relative overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Eng Faol Bo‘lim
            </CardTitle>
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-500">
              <Flame className="size-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground truncate">
              {overview.top_module_name || 'AI Chat'}
            </div>
            <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground">
              <Badge variant="secondary" className="px-1.5 py-0 text-[10px] bg-purple-500/15 text-purple-500">
                Top #1
              </Badge>
              <span>eng ko‘p vaqt sarflangan</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabbed Analytics Section */}
      <Tabs defaultValue="modules" className="space-y-4">
        <TabsList className="bg-muted/60 p-1 border border-border/50 rounded-xl">
          <TabsTrigger value="modules" className="gap-2">
            <Layers className="size-4" />
            Bo‘limlar & Vaqt
          </TabsTrigger>
          <TabsTrigger value="clicks" className="gap-2">
            <MousePointerClick className="size-4" />
            Kliklar & Tugmalar
          </TabsTrigger>
          <TabsTrigger value="users" className="gap-2">
            <Users className="size-4" />
            Foydalanuvchilar
          </TabsTrigger>
          <TabsTrigger value="timeline" className="gap-2">
            <TrendingUp className="size-4" />
            Soatlik Dinamika
          </TabsTrigger>
          <TabsTrigger value="features" className="gap-2">
            <Box className="size-4" />
            Funksiyalar & Fichalar
          </TabsTrigger>
          <TabsTrigger value="events" className="gap-2">
            <Activity className="size-4" />
            Jonli Voqealar
          </TabsTrigger>
        </TabsList>

        {/* ========================================================= */}
        {/* TAB 1: MODULES & TIME BREAKDOWN */}
        {/* ========================================================= */}
        <TabsContent value="modules" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Donut Chart */}
            <Card className="bg-card/70 border-border/60 lg:col-span-1">
              <CardHeader>
                <CardTitle className="text-base font-semibold">Vaqt Taqsimoti (Share %)</CardTitle>
                <CardDescription>Foydalanuvchilar diqqatining bo‘limlar bo‘yicha foiz ulushi</CardDescription>
              </CardHeader>
              <CardContent className="h-64 flex items-center justify-center">
                {pieChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieChartData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={80}
                        paddingAngle={3}
                      >
                        {pieChartData.map((entry: any, index: number) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(val: any, name: any, item: any) => [
                          `${val} daqiqa (${item.payload.share}%)`,
                          name,
                        ]}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-sm text-muted-foreground">Ma’lumotlar mavjud emas</p>
                )}
              </CardContent>
            </Card>

            {/* Modules Table */}
            <Card className="bg-card/70 border-border/60 lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-base font-semibold">Platforma Bo‘limlari Reytingi</CardTitle>
                <CardDescription>Qaysi bo‘limga qancha tashrif buyurilgani va o‘tkazilgan vaqt</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-muted/40 text-muted-foreground text-xs uppercase font-medium border-y border-border/40">
                      <tr>
                        <th className="px-4 py-3">Bo‘lim</th>
                        <th className="px-4 py-3">Tashriflar</th>
                        <th className="px-4 py-3">Jami Vaqt</th>
                        <th className="px-4 py-3">O‘rtacha Tashrif</th>
                        <th className="px-4 py-3">Kliklar</th>
                        <th className="px-4 py-3 text-right">Ulush</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/30">
                      {modulesList.length > 0 ? (
                        modulesList.map((m: any) => (
                          <tr key={m.module} className="hover:bg-muted/30 transition-colors">
                            <td className="px-4 py-3 flex items-center gap-2.5 font-medium text-foreground">
                              {getModuleIcon(m.module)}
                              <span>{m.module_name}</span>
                            </td>
                            <td className="px-4 py-3 text-muted-foreground">{m.page_views.toLocaleString()}</td>
                            <td className="px-4 py-3 font-semibold text-foreground">{formatSeconds(m.total_time_seconds)}</td>
                            <td className="px-4 py-3 text-muted-foreground">{formatSeconds(m.avg_dwell_seconds)}</td>
                            <td className="px-4 py-3 text-muted-foreground">{m.clicks.toLocaleString()}</td>
                            <td className="px-4 py-3 text-right">
                              <Badge variant="outline" className="text-xs font-semibold">
                                {m.share_percentage}%
                              </Badge>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={6} className="text-center py-8 text-muted-foreground">
                            Ma’lumotlar topilmadi
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ========================================================= */}
        {/* TAB 2: TOP CLICKS & ELEMENT INTERACTIONS */}
        {/* ========================================================= */}
        <TabsContent value="clicks" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Top Clicks Bar Chart */}
            <Card className="bg-card/70 border-border/60 lg:col-span-1">
              <CardHeader>
                <CardTitle className="text-base font-semibold">Top 8 Tugmalar & Bosishlar</CardTitle>
                <CardDescription>Eng ko‘p bosilgan interaktiv elementlar</CardDescription>
              </CardHeader>
              <CardContent className="h-72">
                {topClicksChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={topClicksChartData} layout="vertical" margin={{ left: 10, right: 10, top: 10, bottom: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                      <XAxis type="number" tick={{ fontSize: 11 }} />
                      <YAxis dataKey="name" type="category" width={110} tick={{ fontSize: 10 }} />
                      <Tooltip />
                      <Bar dataKey="clicks" name="Kliklar" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                    Kliklar hali qayd etilmagan
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Detailed Top Clicks Table */}
            <Card className="bg-card/70 border-border/60 lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-base font-semibold">Interaktiv Elementlar Reytingi</CardTitle>
                <CardDescription>Foydalanuvchilar qaysi tugma, havola yoki boshqaruv elementini bosmoqda</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-muted/40 text-muted-foreground text-xs uppercase font-medium border-y border-border/40">
                      <tr>
                        <th className="px-4 py-3">#</th>
                        <th className="px-4 py-3">Element / Tugma Matni</th>
                        <th className="px-4 py-3">Bo‘lim</th>
                        <th className="px-4 py-3">Turi</th>
                        <th className="px-4 py-3">Sahifa Yo‘li</th>
                        <th className="px-4 py-3 text-right">Kliklar</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/30">
                      {clicksList.length > 0 ? (
                        clicksList.map((c: any, index: number) => (
                          <tr key={`${c.label}-${index}`} className="hover:bg-muted/30 transition-colors">
                            <td className="px-4 py-3 text-muted-foreground font-mono text-xs">{index + 1}</td>
                            <td className="px-4 py-3 font-medium text-foreground">
                              <span className="bg-muted/60 px-2 py-0.5 rounded-md border border-border/40 font-mono text-xs">
                                {c.label}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-muted-foreground flex items-center gap-1.5">
                              {getModuleIcon(c.module)}
                              <span>{c.module_name}</span>
                            </td>
                            <td className="px-4 py-3">
                              <Badge variant="outline" className="text-[11px] uppercase">
                                {c.element_tag || 'button'}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-muted-foreground font-mono text-xs">{c.page_route}</td>
                            <td className="px-4 py-3 text-right font-bold text-primary">
                              {c.click_count.toLocaleString()}
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={6} className="text-center py-8 text-muted-foreground">
                            Kliklar ma’lumoti mavjud emas
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ========================================================= */}
        {/* TAB 3: USER ENGAGEMENT LEADERBOARD */}
        {/* ========================================================= */}
        <TabsContent value="users" className="space-y-4">
          <Card className="bg-card/70 border-border/60">
            <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <CardTitle className="text-base font-semibold">Foydalanuvchilar Faolligi Jadvali</CardTitle>
                <CardDescription>Qaysi foydalanuvchi platformada qancha vaqt o‘tkazmoqda va qanday harakatlar qilmoqda</CardDescription>
              </div>
              <div className="w-full sm:w-64">
                <Input
                  placeholder="Email bo‘yicha qidiruv..."
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  className="bg-muted/40"
                />
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-muted/40 text-muted-foreground text-xs uppercase font-medium border-y border-border/40">
                    <tr>
                      <th className="px-4 py-3">Foydalanuvchi</th>
                      <th className="px-4 py-3">Sevimli Bo‘limi</th>
                      <th className="px-4 py-3">Jami Vaqt</th>
                      <th className="px-4 py-3">Jami Harakatlar</th>
                      <th className="px-4 py-3">Kliklar</th>
                      <th className="px-4 py-3 text-right">Oxirgi Faollik</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/30">
                    {usersList.length > 0 ? (
                      usersList.map((u: any) => (
                        <tr key={u.user_id} className="hover:bg-muted/30 transition-colors">
                          <td className="px-4 py-3">
                            <div className="font-medium text-foreground">{u.nickname || u.email}</div>
                            <div className="text-xs text-muted-foreground font-mono">{u.email}</div>
                          </td>
                          <td className="px-4 py-3 flex items-center gap-1.5 font-medium">
                            {getModuleIcon(u.favorite_module)}
                            <span>{u.favorite_module_name}</span>
                          </td>
                          <td className="px-4 py-3 font-semibold text-foreground">
                            {formatSeconds(u.total_time_seconds)}
                          </td>
                          <td className="px-4 py-3 text-muted-foreground">
                            {u.total_actions.toLocaleString()} ta
                          </td>
                          <td className="px-4 py-3 text-muted-foreground">
                            {u.total_clicks.toLocaleString()} ta
                          </td>
                          <td className="px-4 py-3 text-right text-xs text-muted-foreground font-mono">
                            {u.last_active_timestamp ? new Date(u.last_active_timestamp).toLocaleString('uz-UZ') : '—'}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={6} className="text-center py-8 text-muted-foreground">
                          Foydalanuvchilar topilmadi
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ========================================================= */}
        {/* TAB 4: 24-HOUR ACTIVITY TIMELINE */}
        {/* ========================================================= */}
        <TabsContent value="timeline" className="space-y-4">
          <Card className="bg-card/70 border-border/60">
            <CardHeader>
              <CardTitle className="text-base font-semibold">24 Soatlik Faollik Dinamikasi</CardTitle>
              <CardDescription>Kun davomida foydalanuvchilarning platformadan foydalanish soatlari</CardDescription>
            </CardHeader>
            <CardContent className="h-80">
              {timelineList.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={timelineList} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorActions" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="colorUsers" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                    <XAxis dataKey="hour" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    <Area type="monotone" dataKey="actions" name="Harakatlar & Kliklar" stroke="#10b981" fillOpacity={1} fill="url(#colorActions)" />
                    <Area type="monotone" dataKey="users" name="Aktiv Foydalanuvchilar" stroke="#3b82f6" fillOpacity={1} fill="url(#colorUsers)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                  Dinamika ma’lumotlari mavjud emas
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ========================================================= */}
        {/* TAB 5: RAW LIVE EVENT STREAM */}
        {/* ========================================================= */}
        <TabsContent value="events" className="space-y-4">
          <Card className="bg-card/70 border-border/60">
            <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <CardTitle className="text-base font-semibold">Jonli Faoliyat Voqealari</CardTitle>
                <CardDescription>Real vaqt rejimida yozilayotgan xom telemetriya loglari</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <select
                  value={selectedModuleFilter}
                  onChange={(e) => setSelectedModuleFilter(e.target.value)}
                  className="bg-muted text-xs border border-border/60 rounded-lg px-2.5 py-1.5"
                >
                  <option value="all">Barcha bo‘limlar</option>
                  <option value="chat">Chat</option>
                  <option value="datasets">Bilimlar bazasi</option>
                  <option value="agent_canvas">Agent Canvas</option>
                  <option value="crm">CRM</option>
                  <option value="search">Qidiruv</option>
                  <option value="files_skills">Fayllar</option>
                  <option value="settings">Sozlamalar</option>
                </select>

                <select
                  value={selectedEventFilter}
                  onChange={(e) => setSelectedEventFilter(e.target.value)}
                  className="bg-muted text-xs border border-border/60 rounded-lg px-2.5 py-1.5"
                >
                  <option value="all">Barcha turlar</option>
                  <option value="click">Faqat kliklar</option>
                  <option value="page_view">Faqat sahifalar</option>
                  <option value="action">Harakatlar</option>
                </select>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto max-h-[500px]">
                <table className="w-full text-xs text-left">
                  <thead className="bg-muted/40 text-muted-foreground uppercase font-medium border-y border-border/40 sticky top-0 backdrop-blur-md">
                    <tr>
                      <th className="px-4 py-2.5">Vaqt</th>
                      <th className="px-4 py-2.5">Turi</th>
                      <th className="px-4 py-2.5">Bo‘lim</th>
                      <th className="px-4 py-2.5">Harakat / Element</th>
                      <th className="px-4 py-2.5">Sahifa Yo‘li</th>
                      <th className="px-4 py-2.5">Davomiylik</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/20">
                    {rawEventsList.length > 0 ? (
                      rawEventsList.map((e: any) => (
                        <tr key={e.id} className="hover:bg-muted/30 transition-colors font-mono">
                          <td className="px-4 py-2 text-muted-foreground whitespace-nowrap">
                            {new Date(e.timestamp).toLocaleTimeString('uz-UZ')}
                          </td>
                          <td className="px-4 py-2">
                            <Badge
                              variant="outline"
                              className={`text-[10px] uppercase ${
                                e.event_type === 'click'
                                  ? 'border-blue-500/40 text-blue-500'
                                  : e.event_type === 'page_view'
                                    ? 'border-emerald-500/40 text-emerald-500'
                                    : 'border-purple-500/40 text-purple-500'
                              }`}
                            >
                              {e.event_type}
                            </Badge>
                          </td>
                          <td className="px-4 py-2 font-sans font-medium text-foreground flex items-center gap-1.5">
                            {getModuleIcon(e.module)}
                            <span>{e.module_name || e.module}</span>
                          </td>
                          <td className="px-4 py-2 font-sans text-foreground">
                            {e.element_label ? (
                              <span className="font-semibold text-primary">{e.element_label}</span>
                            ) : (
                              e.action_name
                            )}
                          </td>
                          <td className="px-4 py-2 text-muted-foreground truncate max-w-xs">{e.page_route}</td>
                          <td className="px-4 py-2 text-muted-foreground whitespace-nowrap">
                            {e.duration_seconds > 0 ? `${e.duration_seconds}s` : '—'}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={6} className="text-center py-8 text-muted-foreground font-sans">
                          Voqealar mavjud emas
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ========================================================= */}
        {/* TAB 5: FEATURES & FUNCTIONS MATRIX */}
        {/* ========================================================= */}
        <TabsContent value="features" className="space-y-6">
          <Card className="bg-card/70 border-border/60">
            <CardHeader>
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div>
                  <CardTitle className="text-base font-semibold">Funksiyalar va Fichalar Ishlatilishi (Feature Adoption)</CardTitle>
                  <CardDescription>
                    Qaysi AI imkoniyatlari, hujjat yuklash yoki CRM funksiyalari ko‘proq chaqirilayotgani
                  </CardDescription>
                </div>
                <Badge variant="secondary" className="w-fit text-xs">
                  Jami fitchalar: {featuresList.length}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg border border-border/60 overflow-hidden">
                <table className="w-full text-xs text-left">
                  <thead className="bg-muted/60 text-muted-foreground uppercase text-[10px] tracking-wider border-b border-border/60">
                    <tr>
                      <th className="px-4 py-3">#</th>
                      <th className="px-4 py-3">Funksiya / Imkoniyat</th>
                      <th className="px-4 py-3">Platforma Moduli</th>
                      <th className="px-4 py-3">API Endpoint</th>
                      <th className="px-4 py-3 text-right">Chaqiruvlar Soni</th>
                      <th className="px-4 py-3 text-right">Noyob Foydalanuvchilar</th>
                      <th className="px-4 py-3 text-right">Oxirgi Foydalanilgan</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40 font-mono">
                    {featuresList.length > 0 ? (
                      featuresList.map((f: any, idx: number) => (
                        <tr key={idx} className="hover:bg-muted/30 transition-colors">
                          <td className="px-4 py-2 text-muted-foreground">{idx + 1}</td>
                          <td className="px-4 py-2 font-sans font-semibold text-foreground">
                            {f.feature_name}
                          </td>
                          <td className="px-4 py-2 font-sans">
                            <Badge variant="outline" className="text-[11px] gap-1 py-0">
                              {getModuleIcon(f.module)}
                              <span>{f.module_name || f.module}</span>
                            </Badge>
                          </td>
                          <td className="px-4 py-2 text-muted-foreground text-[11px] truncate max-w-xs">
                            {f.endpoint || '—'}
                          </td>
                          <td className="px-4 py-2 text-right font-bold text-primary">
                            {Number(f.invocations).toLocaleString()}
                          </td>
                          <td className="px-4 py-2 text-right text-foreground font-sans">
                            {f.unique_users} ta user
                          </td>
                          <td className="px-4 py-2 text-right text-muted-foreground text-[11px] font-sans">
                            {f.last_used ? new Date(f.last_used).toLocaleDateString() : '—'}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={7} className="text-center py-8 text-muted-foreground font-sans">
                          Hozircha funksiyalar chaqiruvi qayd etilmadi
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
