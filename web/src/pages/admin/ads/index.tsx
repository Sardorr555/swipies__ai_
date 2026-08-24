import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertCircle,
  BarChart3,
  CheckCircle2,
  DollarSign,
  ExternalLink,
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
import adService, { AdminAdsOverview, AdminAdsSettings, PromoCodeItem } from '@/services/ad-service';

export default function AdminAdsPage() {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<AdminAdsOverview | null>(null);
  const [moderationQueue, setModerationQueue] = useState<any[]>([]);
  const [promoCodes, setPromoCodes] = useState<PromoCodeItem[]>([]);
  const [settings, setSettings] = useState<AdminAdsSettings | null>(null);
  const [activeTab, setActiveTab] = useState('moderation');

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

  const fetchAdminData = async () => {
    setLoading(true);
    try {
      const [ovRes, modRes, setRes, promoRes] = await Promise.all([
        adService.getAdminOverview(),
        adService.getAdminModerationQueue(),
        adService.getAdminSettings(),
        adService.adminListPromoCodes(),
      ]);

      if (ovRes.data?.data) setOverview(ovRes.data.data);
      if (modRes.data?.data) setModerationQueue(modRes.data.data);
      if (setRes.data?.data) setSettings(setRes.data.data);
      if (promoRes.data?.data) setPromoCodes(promoRes.data.data);
    } catch (err: any) {
      message.error(err.message || 'Failed to load ads admin data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePromo = async () => {
    if (!newPromoForm.code.trim()) {
      message.error('Укажите код промокода');
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
      message.success('Промокод успешно создан!');
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
      message.error(err.message || 'Ошибка создания промокода');
    }
  };

  const handleTogglePromo = async (promoId: string) => {
    try {
      await adService.adminTogglePromoCode(promoId);
      message.success('Статус промокода изменен');
      fetchAdminData();
    } catch (err: any) {
      message.error(err.message || 'Ошибка изменения статуса');
    }
  };

  const handleDeletePromo = async (promoId: string) => {
    try {
      await adService.adminDeletePromoCode(promoId);
      message.success('Промокод удален');
      fetchAdminData();
    } catch (err: any) {
      message.error(err.message || 'Ошибка удаления промокода');
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
    <div className="flex-1 space-y-6 p-8 pt-6">
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
            <div className="text-2xl font-bold text-emerald-500">${(overview?.total_revenue || 0).toFixed(2)}</div>
            <p className="text-xs text-muted-foreground mt-1">Cumulative spend across network</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="moderation" className="flex items-center gap-2">
            <Shield className="h-4 w-4" /> Moderation Queue ({moderationQueue.length})
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
                      {moderationQueue.map((cmp) => (
                        <tr key={cmp.id} className="hover:bg-muted/30">
                          <td className="py-3 px-4">
                            <div className="font-semibold">{cmp.name}</div>
                            <div className="text-xs text-muted-foreground font-medium">{cmp.company_name}</div>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {(!cmp.target_languages || cmp.target_languages.includes('all') || cmp.target_languages.length === 0) ? (
                                <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[9px] bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300 font-medium">🌐 Все языки</span>
                              ) : (
                                cmp.target_languages.map((l: string) => (
                                  <span key={l} className="inline-flex items-center px-1.5 py-0.2 rounded text-[9px] bg-sky-50 text-sky-700 dark:bg-sky-950/50 dark:text-sky-300 font-bold uppercase">
                                    {l === 'uz' ? '🇺🇿 UZ' : l === 'ru' ? '🇷🇺 RU' : l === 'en' ? '🇬🇧 EN' : l}
                                  </span>
                                ))
                              )}
                              {cmp.target_models && cmp.target_models.length > 0 && !cmp.target_models.includes('all') && (
                                <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[9px] bg-purple-50 text-purple-700 dark:bg-purple-950/50 dark:text-purple-300 font-medium">
                                  🤖 {cmp.target_models.join(', ')}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="py-3 px-4 max-w-sm">
                            <div className="text-xs line-clamp-2 text-foreground font-mono bg-muted/30 p-1.5 rounded">
                              "{cmp.advertisement_text}"
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <a
                              href={cmp.landing_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-xs text-blue-500 hover:underline flex items-center gap-1 max-w-[180px] truncate"
                            >
                              {cmp.landing_url} <ExternalLink className="h-3 w-3 inline" />
                            </a>
                          </td>
                          <td className="py-3 px-4">
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
                              <div className="text-[10px] text-muted-foreground mt-0.5 max-w-[150px] truncate">
                                {cmp.moderation_note}
                              </div>
                            )}
                          </td>
                          <td className="py-3 px-4 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                className="text-emerald-500 border-emerald-500/30 hover:bg-emerald-500/10"
                                onClick={() => handleApprove(cmp)}
                              >
                                <CheckCircle2 className="mr-1 h-3.5 w-3.5" /> Approve
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                className="text-red-500 border-red-500/30 hover:bg-red-500/10"
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
                      {promoCodes.map((p) => (
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
    </div>
  );
}
