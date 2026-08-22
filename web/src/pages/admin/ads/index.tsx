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
  RefreshCw,
  Save,
  Shield,
  ShieldAlert,
  Sparkles,
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import adService, { AdminAdsOverview, AdminAdsSettings } from '@/services/ad-service';

export default function AdminAdsPage() {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<AdminAdsOverview | null>(null);
  const [moderationQueue, setModerationQueue] = useState<any[]>([]);
  const [settings, setSettings] = useState<AdminAdsSettings | null>(null);
  const [activeTab, setActiveTab] = useState('moderation');

  // Reject modal state
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
  const [selectedRejectCampaign, setSelectedRejectCampaign] = useState<any | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  const fetchAdminData = async () => {
    setLoading(true);
    try {
      const [ovRes, modRes, setRes] = await Promise.all([
        adService.getAdminOverview(),
        adService.getAdminModerationQueue(),
        adService.getAdminSettings(),
      ]);

      if (ovRes.data?.data) setOverview(ovRes.data.data);
      if (modRes.data?.data) setModerationQueue(modRes.data.data);
      if (setRes.data?.data) setSettings(setRes.data.data);
    } catch (err: any) {
      message.error(err.message || 'Failed to load ads admin data');
    } finally {
      setLoading(false);
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
      </Tabs>

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
