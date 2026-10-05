import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertCircle,
  BarChart3,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Copy,
  DollarSign,
  ExternalLink,
  Eye,
  Globe,
  Layers,
  Megaphone,
  MousePointer,
  Plus,
  RefreshCw,
  Save,
  Shield,
  ShieldAlert,
  Sparkles,
  Tag,
  Ticket,
  Trash2,
  UserCheck,
  Users,
  XCircle,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import message from '@/components/ui/message';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import adService, {
  AdminAdsOverview,
  AdminAdsSettings,
  AdminTimelineData,
  PromoCodeItem,
} from '@/services/ad-service';

export default function AdminAdsPage() {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<AdminAdsOverview | null>(null);
  const [moderationQueue, setModerationQueue] = useState<any[]>([]);
  const [promoCodes, setPromoCodes] = useState<PromoCodeItem[]>([]);
  const [settings, setSettings] = useState<AdminAdsSettings | null>(null);
  const [adminTimeline, setAdminTimeline] = useState<AdminTimelineData | null>(null);
  const [timelineDays, setTimelineDays] = useState<number>(14);
  const [activeTab, setActiveTab] = useState('moderation');

  // Offer expand state & Details modal state
  const [expandedOffers, setExpandedOffers] = useState<Record<string, boolean>>({});
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [selectedDetailsCampaign, setSelectedDetailsCampaign] = useState<any | null>(null);

  const toggleOfferExpand = (id: string) => {
    setExpandedOffers((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleOpenDetails = (cmp: any) => {
    setSelectedDetailsCampaign(cmp);
    setIsDetailsModalOpen(true);
  };

  const handleCopy = (text: string, label: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    message.success(`${label} nusxalandi!`);
  };

  // Reject modal state
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
  const [selectedRejectCampaign, setSelectedRejectCampaign] = useState<any | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  // Promo modal state
  const [isPromoModalOpen, setIsPromoModalOpen] = useState(false);
  const [newPromoForm, setNewPromoForm] = useState({
    code: '',
    discount_type: 'percent',
    discount_value: 20,
    applies_to: 'all',
    plan_id: 'all',
    max_uses: 100,
    expires_days: 30,
  });

  const fetchAdminTimeline = async (days: number = timelineDays) => {
    try {
      const res = await adService.getAdminOverviewTimeline(days);
      if (res.data?.data) {
        setAdminTimeline(res.data.data);
      }
    } catch (err: any) {
      console.error('Failed to load admin timeline', err);
    }
  };

  const fetchAdminData = async () => {
    setLoading(true);
    try {
      const [ovRes, modRes, setRes, promoRes, timeRes] = await Promise.all([
        adService.getAdminOverview(),
        adService.getAdminModerationQueue(),
        adService.getAdminSettings(),
        adService.adminListPromoCodes(),
        adService.getAdminOverviewTimeline(timelineDays),
      ]);

      if (ovRes.data?.data) setOverview(ovRes.data.data);
      if (modRes.data?.data) setModerationQueue(modRes.data.data);
      if (setRes.data?.data) setSettings(setRes.data.data);
      if (promoRes.data?.data) setPromoCodes(promoRes.data.data);
      if (timeRes.data?.data) setAdminTimeline(timeRes.data.data);
    } catch (err: any) {
      message.error(err.message || 'Failed to load ads admin data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePromo = async () => {
    if (!newPromoForm.code.trim()) {
      message.error('Please specify promo code');
      return;
    }
    try {
      await adService.adminCreatePromoCode({
        code: newPromoForm.code.trim().toUpperCase(),
        discount_type: newPromoForm.discount_type,
        discount_value: parseFloat(String(newPromoForm.discount_value)),
        applies_to: newPromoForm.applies_to,
        plan_id: newPromoForm.plan_id === 'all' ? undefined : newPromoForm.plan_id,
        max_uses: parseInt(String(newPromoForm.max_uses)),
        expires_days: parseInt(String(newPromoForm.expires_days)),
      });
      message.success('Promo code created successfully!');
      setIsPromoModalOpen(false);
      setNewPromoForm({
        code: '',
        discount_type: 'percent',
        discount_value: 20,
        applies_to: 'all',
        plan_id: 'all',
        max_uses: 100,
        expires_days: 30,
      });
      fetchAdminData();
    } catch (err: any) {
      message.error(err.message || 'Failed to create promo code');
    }
  };

  const handleTogglePromo = async (promoId: string) => {
    try {
      await adService.adminTogglePromoCode(promoId);
      message.success('Promo code status updated');
      fetchAdminData();
    } catch (err: any) {
      message.error(err.message || 'Failed to update status');
    }
  };

  const handleDeletePromo = async (promoId: string) => {
    try {
      await adService.adminDeletePromoCode(promoId);
      message.success('Promo code deleted');
      fetchAdminData();
    } catch (err: any) {
      message.error(err.message || 'Failed to delete promo code');
    }
  };

  useEffect(() => {
    fetchAdminData();
  }, []);

  const handleApprove = async (cmp: any) => {
    try {
      await adService.approveCampaign(cmp.id);
      message.success(`Campaign "${cmp.name}" approved!`);
      fetchAdminData();
    } catch (err: any) {
      message.error(err.message || 'Approval failed');
    }
  };

  const handleOpenReject = (cmp: any) => {
    setSelectedRejectCampaign(cmp);
    setRejectReason('Does not meet ad quality or truthfulness guidelines.');
    setIsRejectModalOpen(true);
  };

  const handleConfirmReject = async () => {
    if (!selectedRejectCampaign) return;
    try {
      await adService.rejectCampaign(selectedRejectCampaign.id, rejectReason);
      message.success(`Campaign "${selectedRejectCampaign.name}" rejected.`);
      setIsRejectModalOpen(false);
      fetchAdminData();
    } catch (err: any) {
      message.error(err.message || 'Rejection failed');
    }
  };

  const handleSaveSettings = async () => {
    if (!settings) return;
    try {
      await adService.updateAdminSettings(settings);
      message.success('Ad network settings saved!');
      fetchAdminData();
    } catch (err: any) {
      message.error(err.message || 'Failed to save settings');
    }
  };

  return (
    <div className="flex-1 space-y-6 p-8 pt-6 h-full overflow-y-auto pb-16">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">Swipies Ads Moderation & Network</h1>
            <Badge variant="outline" className="border-purple-500/30 bg-purple-500/10 text-purple-400">
              <Shield className="mr-1 h-3 w-3" /> Admin Superuser
            </Badge>
          </div>
          <p className="text-muted-foreground mt-1 text-sm">
            Supervise ad campaigns, approve quality offers, configure frequency caps, and monitor global revenue.
          </p>
        </div>

        <Button variant="ghost" size="icon" onClick={fetchAdminData} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Advertisers</CardTitle>
            <Users className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview?.total_advertisers || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">Registered businesses</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Campaigns</CardTitle>
            <Layers className="h-4 w-4 text-indigo-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {overview?.active_campaigns || 0}{' '}
              <span className="text-xs font-normal text-muted-foreground">active / {overview?.total_campaigns || 0} total</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {overview?.pending_moderation ? `${overview.pending_moderation} pending review` : 'All reviewed'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Network Impressions</CardTitle>
            <Activity className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(overview?.total_impressions || 0).toLocaleString()}{' '}
              <span className="text-sm font-normal text-muted-foreground">({overview?.network_ctr || 0}% CTR)</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">{(overview?.total_clicks || 0).toLocaleString()} outbound visits</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Platform Ad Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-500">${((overview?.total_revenue || 0) > 0 ? overview?.total_revenue : (overview?.total_deposits || 0)).toFixed(2)}</div>
            <p className="text-xs text-muted-foreground mt-1">Cumulative deposits & spend across network</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="moderation" className="flex items-center gap-2">
            <Shield className="h-4 w-4" /> Moderation Queue ({moderationQueue.length})
          </TabsTrigger>
          <TabsTrigger value="network_analytics" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-blue-500" /> Сетевая аналитика
          </TabsTrigger>
          <TabsTrigger value="promos" className="flex items-center gap-2">
            <Ticket className="h-4 w-4" /> Promo Codes ({promoCodes.length})
          </TabsTrigger>
          <TabsTrigger value="settings" className="flex items-center gap-2">
            <Sparkles className="h-4 w-4" /> Global Network Settings
          </TabsTrigger>
        </TabsList>

        {/* 1. Moderation Tab */}
        <TabsContent value="moderation" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Campaign Moderation Queue</CardTitle>
              <CardDescription>
                Verify that sponsored offerings adhere to factual accuracy, honesty, and safety policies.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {moderationQueue.length === 0 ? (
                <div className="py-12 text-center text-sm text-muted-foreground">
                  <CheckCircle2 className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
                  No campaigns submitted yet.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b bg-muted/40 text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="py-3 px-4">Advertiser / Campaign</th>
                        <th className="py-3 px-4">Offer Copy</th>
                        <th className="py-3 px-4">Landing Page</th>
                        <th className="py-3 px-4">Moderation Status</th>
                        <th className="py-3 px-4 text-right">Moderation Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {(moderationQueue || []).map((cmp) => (
                        <tr key={cmp.id} className="hover:bg-muted/30 transition-colors">
                          <td className="py-3 px-4 align-top">
                            <div
                              className="font-semibold text-foreground hover:text-blue-500 cursor-pointer flex items-center gap-1.5"
                              onClick={() => handleOpenDetails(cmp)}
                              title="Tafsilotlarni ko'rish uchun bosing"
                            >
                              <span>{cmp.name}</span>
                              <Eye className="h-3.5 w-3.5 text-muted-foreground opacity-60 hover:opacity-100" />
                            </div>
                            <div className="text-xs text-muted-foreground font-medium">{cmp.company_name}</div>
                            <div className="flex flex-wrap gap-1 mt-1.5">
                              {(!cmp.target_languages || !Array.isArray(cmp.target_languages) || cmp.target_languages.includes('all') || cmp.target_languages.length === 0) ? (
                                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300 font-medium">🌐 Все языки</span>
                              ) : (
                                (Array.isArray(cmp.target_languages) ? cmp.target_languages : []).map((l: string) => (
                                  <span key={l} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-sky-50 text-sky-700 dark:bg-sky-950/50 dark:text-sky-300 font-bold uppercase">
                                    {l === 'uz' ? '🇺🇿 UZ' : l === 'ru' ? '🇷🇺 RU' : l === 'en' ? '🇬🇧 EN' : l}
                                  </span>
                                ))
                              )}
                              {Array.isArray(cmp.target_models) && cmp.target_models.length > 0 && !cmp.target_models.includes('all') && (
                                cmp.target_models.map((m: string) => (
                                  <span key={m} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-purple-50 text-purple-700 dark:bg-purple-950/50 dark:text-purple-300 font-medium">
                                    🤖 {m}
                                  </span>
                                ))
                              )}
                            </div>
                          </td>

                          {/* Offer Copy with Click-to-Expand */}
                          <td className="py-3 px-4 max-w-md align-top">
                            <div
                              onClick={() => toggleOfferExpand(cmp.id)}
                              className={`group relative text-xs rounded-lg p-2.5 transition-all cursor-pointer border ${
                                expandedOffers[cmp.id]
                                  ? 'bg-muted/80 border-blue-500/40 shadow-sm'
                                  : 'bg-muted/30 hover:bg-muted/60 border-border/40 hover:border-blue-500/30'
                              }`}
                              title="Ustiga bosing: to'liq matn ochiladi"
                            >
                              <div
                                className={`font-mono text-foreground leading-relaxed ${
                                  expandedOffers[cmp.id] ? 'whitespace-pre-wrap select-text' : 'line-clamp-2'
                                }`}
                              >
                                "{cmp.advertisement_text}"
                              </div>
                              <div className="flex items-center justify-between mt-1.5 pt-1.5 border-t border-border/40 text-[10px] text-muted-foreground">
                                <span className="flex items-center gap-1 text-blue-500 group-hover:text-blue-400 font-medium">
                                  {expandedOffers[cmp.id] ? (
                                    <>
                                      <ChevronUp className="h-3 w-3" /> Qisqartirish
                                    </>
                                  ) : (
                                    <>
                                      <ChevronDown className="h-3 w-3" /> To'liq o'qish ({cmp.advertisement_text?.length || 0} ta belgi)
                                    </>
                                  )}
                                </span>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleCopy(cmp.advertisement_text, 'Reklama matni');
                                  }}
                                  className="hover:text-foreground flex items-center gap-0.5 px-1.5 py-0.5 rounded hover:bg-background/80 transition-colors"
                                  title="Nusxa olish"
                                >
                                  <Copy className="h-2.5 w-2.5" /> Nusxa
                                </button>
                              </div>
                            </div>
                          </td>

                          {/* Landing Page */}
                          <td className="py-3 px-4 max-w-[200px] align-top">
                            <div className="flex flex-col gap-1">
                              <a
                                href={cmp.landing_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-xs text-blue-500 hover:underline flex items-center gap-1 break-all"
                                title={cmp.landing_url}
                              >
                                <span className="truncate max-w-[170px]">{cmp.landing_url}</span>
                                <ExternalLink className="h-3 w-3 shrink-0" />
                              </a>
                              <button
                                type="button"
                                onClick={() => handleCopy(cmp.landing_url, 'Havola')}
                                className="text-[10px] text-muted-foreground hover:text-foreground self-start flex items-center gap-1 mt-0.5"
                              >
                                <Copy className="h-2.5 w-2.5" /> URL nusxalash
                              </button>
                            </div>
                          </td>

                          {/* Moderation Status */}
                          <td className="py-3 px-4 align-top">
                            <Badge
                              variant="outline"
                              className={
                                cmp.moderation_status === 'approved'
                                  ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-500'
                                  : cmp.moderation_status === 'rejected'
                                  ? 'border-red-500/30 bg-red-500/10 text-red-500'
                                  : 'border-amber-500/30 bg-amber-500/10 text-amber-500'
                              }
                            >
                              {cmp.moderation_status}
                            </Badge>
                            {cmp.moderation_note && (
                              <div
                                className="text-[11px] text-muted-foreground mt-1 max-w-[170px] break-words cursor-pointer hover:text-foreground"
                                onClick={() => handleOpenDetails(cmp)}
                                title={cmp.moderation_note}
                              >
                                {cmp.moderation_note}
                              </div>
                            )}
                          </td>

                          {/* Moderation Actions */}
                          <td className="py-3 px-4 text-right align-top">
                            <div className="flex items-center justify-end gap-1.5 flex-wrap">
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-8 text-xs hover:bg-muted"
                                onClick={() => handleOpenDetails(cmp)}
                                title="Barcha ma'lumotlarni to'liq ko'rish"
                              >
                                <Eye className="mr-1 h-3.5 w-3.5 text-blue-500" /> Ko'rish
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-8 text-xs text-emerald-500 border-emerald-500/30 hover:bg-emerald-500/10"
                                onClick={() => handleApprove(cmp)}
                              >
                                <CheckCircle2 className="mr-1 h-3.5 w-3.5" /> Approve
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-8 text-xs text-red-500 border-red-500/30 hover:bg-red-500/10"
                                onClick={() => handleOpenReject(cmp)}
                              >
                                <XCircle className="mr-1 h-3.5 w-3.5" /> Reject
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 2. Settings Tab */}
        <TabsContent value="settings" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Global Ad Network & Platform Attribution Controls</CardTitle>
              <CardDescription>Configure global network rules and platform branding URLs.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 max-w-xl">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Max Daily Impressions Per User (Frequency Cap)</label>
                <Input
                  type="number"
                  value={settings?.max_impressions_per_user_day || 3}
                  onChange={(e) =>
                    setSettings({ ...settings!, max_impressions_per_user_day: parseInt(e.target.value) || 3 })
                  }
                />
                <p className="text-[11px] text-muted-foreground">
                  Prevents overloading users by capping the number of times any single campaign can be shown to a user in 24 hours.
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Swipies Platform Attribution Link</label>
                <Input
                  value={settings?.app_url || 'https://swipies.app'}
                  disabled
                />
                <p className="text-[11px] text-muted-foreground">
                  Official platform URL appended for Free-tier users (Paid Plus/Pro users are automatically 100% white-labeled).
                </p>
              </div>

              <Button onClick={handleSaveSettings} className="bg-blue-600 hover:bg-blue-700 text-white mt-2">
                <Save className="mr-1.5 h-4 w-4" /> Save Network Settings
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 3. Promo Codes Tab */}
        <TabsContent value="promos" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Promo Codes & Discounts</CardTitle>
                <CardDescription>
                  Manage percentage discounts, fixed USD credits, and advertiser bonus funds.
                </CardDescription>
              </div>
              <Button onClick={() => setIsPromoModalOpen(true)} size="sm" className="bg-blue-600 hover:bg-blue-700 text-white text-xs">
                <Plus className="mr-1 h-3.5 w-3.5" /> New Promo Code
              </Button>
            </CardHeader>
            <CardContent>
              {promoCodes.length === 0 ? (
                <div className="py-12 text-center text-sm text-muted-foreground">
                  <Ticket className="h-8 w-8 text-blue-500 mx-auto mb-2 opacity-50" />
                  No promo codes created yet. Click "New Promo Code" to add one.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b bg-muted/40 text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="py-3 px-4">Code</th>
                        <th className="py-3 px-4">Discount / Value</th>
                        <th className="py-3 px-4">Applies To</th>
                        <th className="py-3 px-4">Redemptions</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y text-xs">
                      {(promoCodes || []).map((p) => (
                        <tr key={p.id} className="hover:bg-muted/30">
                          <td className="py-3 px-4">
                            <div className="font-mono font-bold text-sm text-blue-600 dark:text-blue-400">{p.code}</div>
                          </td>
                          <td className="py-3 px-4">
                            <span className="font-semibold">
                              {p.discount_type === 'percent'
                                ? `${p.discount_value}% OFF`
                                : p.discount_type === 'fixed_usd'
                                ? `$${p.discount_value.toFixed(2)} OFF`
                                : `+$${p.discount_value.toFixed(2)} Bonus Credit`}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <Badge variant="outline" className="capitalize">
                              {p.applies_to} {p.plan_id ? `(${p.plan_id})` : ''}
                            </Badge>
                          </td>
                          <td className="py-3 px-4">
                            <span>{p.used_count} / {p.max_uses}</span>
                          </td>
                          <td className="py-3 px-4">
                            <Badge variant={p.is_active ? 'default' : 'secondary'} className={p.is_active ? 'bg-emerald-600' : ''}>
                              {p.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                          </td>
                          <td className="py-3 px-4 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 text-xs"
                                onClick={() => handleTogglePromo(p.id)}
                              >
                                {p.is_active ? 'Deactivate' : 'Activate'}
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 text-red-500 hover:text-red-700"
                                onClick={() => handleDeletePromo(p.id)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 2. Network Analytics Tab */}
        <TabsContent value="network_analytics" className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-muted/30 p-4 rounded-xl border">
            <div>
              <h3 className="text-base font-bold flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-blue-500" />
                Сводная аналитика рекламной сети Swipies
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Глобальные показы, клики, CTR и доход платформы в разрезе дней
              </p>
            </div>
            <div className="flex items-center gap-1.5 self-start sm:self-auto bg-background p-1 rounded-lg border">
              {[7, 14, 30].map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => {
                    setTimelineDays(d);
                    fetchAdminTimeline(d);
                  }}
                  className={`px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                    timelineDays === d
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                  }`}
                >
                  {d === 7 ? '7 дней' : d === 14 ? '14 дней' : '30 дней'}
                </button>
              ))}
              <Button
                size="sm"
                variant="ghost"
                className="h-7 px-2 text-xs"
                onClick={() => fetchAdminTimeline(timelineDays)}
                title="Обновить"
              >
                <RefreshCw className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <Card className="bg-gradient-to-br from-blue-50/50 to-transparent dark:from-blue-950/20">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">Глобальные показы</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-black text-blue-600 dark:text-blue-400">
                  {(adminTimeline?.total_network_impressions || 0).toLocaleString()}
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">Охват по всей сети</p>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-emerald-50/50 to-transparent dark:from-emerald-950/20">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">Глобальные клики</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
                  {(adminTimeline?.total_network_clicks || 0).toLocaleString()}
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">Переходы на сайты партнеров</p>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-amber-50/50 to-transparent dark:from-amber-950/20">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">Доход платформы</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-black text-amber-600 dark:text-amber-400">
                  ${(adminTimeline?.total_network_revenue || 0).toFixed(2)}
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">Суммарный доход за период</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold">Динамика показов и переходов сети</CardTitle>
              <CardDescription className="text-xs">
                Показатели платформы за последние {timelineDays} дней
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[300px] w-full">
                {adminTimeline?.timeline && adminTimeline.timeline.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={adminTimeline.timeline}
                      margin={{ top: 10, right: 20, left: -10, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient id="adminImpGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                        </linearGradient>
                        <linearGradient id="adminClkGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 11 }}
                        tickFormatter={(val) => {
                          const parts = val.split('-');
                          return parts.length === 3 ? `${parts[1]}.${parts[2]}` : val;
                        }}
                      />
                      <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'rgba(17, 24, 39, 0.95)',
                          borderRadius: '8px',
                          border: '1px solid rgba(255, 255, 255, 0.1)',
                          color: '#fff',
                          fontSize: '12px',
                        }}
                      />
                      <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                      <Area
                        type="monotone"
                        dataKey="impressions"
                        name="Показы сети"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#adminImpGradient)"
                      />
                      <Area
                        type="monotone"
                        dataKey="clicks"
                        name="Клики сети"
                        stroke="#10b981"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#adminClkGradient)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-xs text-muted-foreground">
                    За выбранный период данных нет
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Create Promo Code Modal */}
      <Dialog open={isPromoModalOpen} onOpenChange={setIsPromoModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Promo Code</DialogTitle>
            <DialogDescription>
              Create a discount or bonus credit code for users or advertisers.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-3 py-3 text-xs">
            <div className="space-y-1">
              <label className="font-semibold">Promo Code Name *</label>
              <Input
                placeholder="e.g. SUMMER2026 or WELCOME50"
                value={newPromoForm.code}
                onChange={(e) => setNewPromoForm({ ...newPromoForm, code: e.target.value.toUpperCase() })}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="font-semibold">Discount Type</label>
                <Select
                  value={newPromoForm.discount_type}
                  onValueChange={(val) => setNewPromoForm({ ...newPromoForm, discount_type: val })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="percent">Percentage (%)</SelectItem>
                    <SelectItem value="fixed_usd">Fixed USD ($)</SelectItem>
                    <SelectItem value="advertiser_bonus_usd">Advertiser Bonus USD ($)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1">
                <label className="font-semibold">Value</label>
                <Input
                  type="number"
                  placeholder="20"
                  value={newPromoForm.discount_value}
                  onChange={(e) => setNewPromoForm({ ...newPromoForm, discount_value: parseFloat(e.target.value) || 0 })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="font-semibold">Applies To</label>
                <Select
                  value={newPromoForm.applies_to}
                  onValueChange={(val) => setNewPromoForm({ ...newPromoForm, applies_to: val })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Purchases</SelectItem>
                    <SelectItem value="subscription">Subscriptions Only</SelectItem>
                    <SelectItem value="advertiser_deposit">Advertiser Deposits</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1">
                <label className="font-semibold">Plan ID (Optional)</label>
                <Select
                  value={newPromoForm.plan_id}
                  onValueChange={(val) => setNewPromoForm({ ...newPromoForm, plan_id: val })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Any Plan</SelectItem>
                    <SelectItem value="plus">Plus Plan</SelectItem>
                    <SelectItem value="pro">Pro Plan</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="font-semibold">Max Uses</label>
                <Input
                  type="number"
                  placeholder="100"
                  value={newPromoForm.max_uses}
                  onChange={(e) => setNewPromoForm({ ...newPromoForm, max_uses: parseInt(e.target.value) || 100 })}
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold">Validity (Days)</label>
                <Input
                  type="number"
                  placeholder="30"
                  value={newPromoForm.expires_days}
                  onChange={(e) => setNewPromoForm({ ...newPromoForm, expires_days: parseInt(e.target.value) || 30 })}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsPromoModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreatePromo} className="bg-blue-600 hover:bg-blue-700 text-white">
              Create Promo Code
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Reason Modal */}
      <Dialog open={isRejectModalOpen} onOpenChange={setIsRejectModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Reject Campaign</DialogTitle>
            <DialogDescription>
              Specify the reason why "{selectedRejectCampaign?.name}" is being rejected.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2 py-3">
            <label className="text-xs font-semibold">Moderation Feedback Note</label>
            <Textarea
              rows={3}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
            />
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsRejectModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleConfirmReject} className="bg-red-600 hover:bg-red-700 text-white">
              Confirm Rejection
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detailed Campaign View Modal */}
      <Dialog open={isDetailsModalOpen} onOpenChange={setIsDetailsModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between pr-6 gap-2">
              <DialogTitle className="text-base sm:text-lg font-bold flex items-center gap-2">
                <Megaphone className="h-5 w-5 text-blue-500 shrink-0" />
                <span>{selectedDetailsCampaign?.name || 'Reklama Kampaniyasi'}</span>
              </DialogTitle>
              <Badge
                variant="outline"
                className={
                  selectedDetailsCampaign?.moderation_status === 'approved'
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-500 shrink-0'
                    : selectedDetailsCampaign?.moderation_status === 'rejected'
                    ? 'border-red-500/30 bg-red-500/10 text-red-500 shrink-0'
                    : 'border-amber-500/30 bg-amber-500/10 text-amber-500 shrink-0'
                }
              >
                {selectedDetailsCampaign?.moderation_status}
              </Badge>
            </div>
            <DialogDescription className="text-xs">
              {selectedDetailsCampaign?.company_name} &bull; ID: {selectedDetailsCampaign?.id}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-3">
            {/* Offer Copy */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs font-semibold">
                <span className="text-foreground">📝 Reklama Matni (Offer Copy):</span>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-6 text-xs px-2"
                  onClick={() => handleCopy(selectedDetailsCampaign?.advertisement_text || '', 'Reklama matni')}
                >
                  <Copy className="h-3 w-3 mr-1" /> Nusxa olish
                </Button>
              </div>
              <div className="p-3.5 rounded-lg bg-muted/40 border text-xs sm:text-sm font-mono whitespace-pre-wrap leading-relaxed select-text">
                "{selectedDetailsCampaign?.advertisement_text}"
              </div>
            </div>

            {/* Landing Page */}
            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-foreground">🔗 O'tish Havolasi (Landing Page URL):</span>
              <div className="p-2.5 rounded-lg bg-muted/40 border flex items-center justify-between gap-2 flex-wrap sm:flex-nowrap">
                <a
                  href={selectedDetailsCampaign?.landing_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-blue-500 hover:underline break-all"
                >
                  {selectedDetailsCampaign?.landing_url}
                </a>
                <div className="flex items-center gap-1.5 shrink-0 ml-auto">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 px-2 text-xs"
                    onClick={() => handleCopy(selectedDetailsCampaign?.landing_url || '', 'Havola')}
                    title="Nusxalash"
                  >
                    <Copy className="h-3.5 w-3.5" />
                  </Button>
                  <a
                    href={selectedDetailsCampaign?.landing_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center justify-center h-7 px-2.5 text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
                  >
                    Ochish <ExternalLink className="ml-1 h-3 w-3" />
                  </a>
                </div>
              </div>
            </div>

            {/* Targeting & Language Rules */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div className="p-3 rounded-lg bg-muted/30 border space-y-1.5">
                <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
                  <Globe className="h-3.5 w-3.5 text-sky-500" /> Maqsadli Tillar:
                </span>
                <div className="flex flex-wrap gap-1">
                  {(!selectedDetailsCampaign?.target_languages ||
                    !Array.isArray(selectedDetailsCampaign.target_languages) ||
                    selectedDetailsCampaign.target_languages.includes('all') ||
                    selectedDetailsCampaign.target_languages.length === 0) ? (
                    <span className="text-xs font-medium text-blue-600">🌐 Barcha tillar</span>
                  ) : (
                    selectedDetailsCampaign.target_languages.map((l: string) => (
                      <span key={l} className="px-2 py-0.5 rounded text-xs bg-sky-100 dark:bg-sky-950 text-sky-800 dark:text-sky-300 font-bold uppercase">
                        {l === 'uz' ? '🇺🇿 O‘zbekcha (UZ)' : l === 'ru' ? '🇷🇺 Ruscha (RU)' : l === 'en' ? '🇬🇧 Inglizcha (EN)' : l}
                      </span>
                    ))
                  )}
                </div>
              </div>

              <div className="p-3 rounded-lg bg-muted/30 border space-y-1.5">
                <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
                  <Bot className="h-3.5 w-3.5 text-purple-500" /> AI Modellari (Targeting):
                </span>
                <div className="flex flex-wrap gap-1">
                  {(!selectedDetailsCampaign?.target_models ||
                    !Array.isArray(selectedDetailsCampaign.target_models) ||
                    selectedDetailsCampaign.target_models.includes('all') ||
                    selectedDetailsCampaign.target_models.length === 0) ? (
                    <span className="text-xs font-medium text-purple-600">🤖 Barcha AI modellari</span>
                  ) : (
                    selectedDetailsCampaign.target_models.map((m: string) => (
                      <span key={m} className="px-2 py-0.5 rounded text-xs bg-purple-100 dark:bg-purple-950 text-purple-800 dark:text-purple-300 font-medium">
                        🤖 {m}
                      </span>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Moderation Notes if present */}
            {selectedDetailsCampaign?.moderation_note && (
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs">
                <span className="font-semibold text-amber-600 dark:text-amber-400">Moderator Izohi:</span>
                <p className="mt-0.5 text-muted-foreground">{selectedDetailsCampaign.moderation_note}</p>
              </div>
            )}
          </div>

          <DialogFooter className="flex flex-col sm:flex-row gap-2">
            <Button variant="outline" onClick={() => setIsDetailsModalOpen(false)}>
              Yopish
            </Button>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                className="text-red-500 border-red-500/30 hover:bg-red-500/10"
                onClick={() => {
                  setIsDetailsModalOpen(false);
                  handleOpenReject(selectedDetailsCampaign);
                }}
              >
                <XCircle className="mr-1 h-3.5 w-3.5" /> Reject
              </Button>
              <Button
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
                onClick={() => {
                  setIsDetailsModalOpen(false);
                  handleApprove(selectedDetailsCampaign);
                }}
              >
                <CheckCircle2 className="mr-1 h-3.5 w-3.5" /> Approve
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
