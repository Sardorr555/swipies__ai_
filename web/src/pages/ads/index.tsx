import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertCircle,
  BarChart3,
  CheckCircle2,
  Coins,
  CreditCard,
  DollarSign,
  Edit3,
  ExternalLink,
  HelpCircle,
  Layers,
  Megaphone,
  MousePointer,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Target,
  Trash2,
  TrendingUp,
  Wallet,
  Zap,
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import AtmosPaymentModal from '@/components/atmos-payment-modal';
import adService, {
  AdCampaignItem,
  AdTransactionItem,
  AdvertiserDashboardData,
} from '@/services/ad-service';

export default function SwipiesAdsPage() {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<AdvertiserDashboardData | null>(null);
  const [transactions, setTransactions] = useState<AdTransactionItem[]>([]);
  const [activeTab, setActiveTab] = useState('campaigns');

  // Modals state
  const [isCampaignModalOpen, setIsCampaignModalOpen] = useState(false);
  const [isTopUpModalOpen, setIsTopUpModalOpen] = useState(false);
  const [isAtmosModalOpen, setIsAtmosModalOpen] = useState(false);
  const [isAnalyticsModalOpen, setIsAnalyticsModalOpen] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState<AdCampaignItem | null>(null);
  const [analyticsData, setAnalyticsData] = useState<any>(null);

  // Form states
  const [campaignForm, setCampaignForm] = useState<Partial<AdCampaignItem>>({
    name: '',
    product_name: '',
    description: '',
    advertisement_text: '',
    landing_url: 'https://',
    target_categories: [],
    keywords: [],
    daily_budget: 10,
    total_budget: 100,
    pricing_model: 'cpc',
    bid_amount: 0.15,
  });
  const [rawKeywords, setRawKeywords] = useState('');
  const [rawCategories, setRawCategories] = useState('');
  const [topUpAmount, setTopUpAmount] = useState('50');

  const fetchDashboard = async () => {
    setLoading(true);
    try {
      const res = await adService.getDashboard();
      if (res.data?.data) {
        setDashboard(res.data.data);
      }
    } catch (err: any) {
      message.error(err.message || 'Failed to load advertiser dashboard');
    } finally {
      setLoading(false);
    }
  };

  const fetchTransactions = async () => {
    try {
      const res = await adService.listTransactions();
      if (res.data?.data) {
        setTransactions(res.data.data);
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchDashboard();
    fetchTransactions();
  }, []);

  const handleOpenCreateCampaign = () => {
    setSelectedCampaign(null);
    setCampaignForm({
      name: '',
      product_name: '',
      description: '',
      advertisement_text: '',
      landing_url: 'https://',
      target_categories: [],
      keywords: [],
      daily_budget: 10,
      total_budget: 100,
      pricing_model: 'cpc',
      bid_amount: 0.15,
    });
    setRawKeywords('');
    setRawCategories('');
    setIsCampaignModalOpen(true);
  };

  const handleOpenEditCampaign = (cmp: AdCampaignItem) => {
    setSelectedCampaign(cmp);
    setCampaignForm({ ...cmp });
    setRawKeywords((cmp.keywords || []).join(', '));
    setRawCategories((cmp.target_categories || []).join(', '));
    setIsCampaignModalOpen(true);
  };

  const handleSaveCampaign = async () => {
    if (
      !campaignForm.name ||
      !campaignForm.product_name ||
      !campaignForm.advertisement_text ||
      !campaignForm.landing_url
    ) {
      message.error('Please fill in all required campaign fields.');
      return;
    }

    const keywords = rawKeywords
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    const target_categories = rawCategories
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    const payload = {
      ...campaignForm,
      keywords,
      target_categories,
    };

    try {
      if (selectedCampaign) {
        await adService.updateCampaign(selectedCampaign.id, payload);
        message.success('Campaign updated successfully!');
      } else {
        await adService.createCampaign(payload);
        message.success('Campaign created successfully!');
      }
      setIsCampaignModalOpen(false);
      fetchDashboard();
    } catch (err: any) {
      message.error(err.message || 'Failed to save campaign');
    }
  };

  const handleToggleStatus = async (cmp: AdCampaignItem) => {
    try {
      await adService.toggleCampaignStatus(cmp.id);
      message.success(`Campaign ${cmp.status === 'active' ? 'paused' : 'activated'}`);
      fetchDashboard();
    } catch (err: any) {
      message.error(err.message || 'Failed to toggle status');
    }
  };

  const handleDeleteCampaign = async (cmp: AdCampaignItem) => {
    if (!confirm(`Are you sure you want to archive campaign "${cmp.name}"?`)) return;
    try {
      await adService.deleteCampaign(cmp.id);
      message.success('Campaign archived');
      fetchDashboard();
    } catch (err: any) {
      message.error(err.message || 'Failed to delete campaign');
    }
  };

  const handleOpenAnalytics = async (cmp: AdCampaignItem) => {
    setSelectedCampaign(cmp);
    try {
      const res = await adService.getCampaignAnalytics(cmp.id);
      setAnalyticsData(res.data?.data || null);
      setIsAnalyticsModalOpen(true);
    } catch (err: any) {
      message.error('Failed to load campaign analytics');
    }
  };

  const handleTopUp = async () => {
    const num = parseFloat(topUpAmount);
    if (isNaN(num) || num <= 0) {
      message.error('Please enter a valid deposit amount');
      return;
    }

    try {
      await adService.depositFunds(num, 'Advertiser Wallet Top-Up');
      message.success(`Successfully deposited $${num.toFixed(2)} to your balance!`);
      setIsTopUpModalOpen(false);
      fetchDashboard();
      fetchTransactions();
    } catch (err: any) {
      message.error(err.message || 'Top-up failed');
    }
  };

  const balance = dashboard?.balance || 0;
  const currency = dashboard?.currency || 'USD';

  return (
    <div className="flex-1 space-y-6 p-8 pt-6">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">Swipies Ads</h1>
            <Badge variant="outline" className="border-blue-500/30 bg-blue-500/10 text-blue-400">
              <Sparkles className="mr-1 h-3 w-3" /> AI Intent Advertising
            </Badge>
          </div>
          <p className="text-muted-foreground mt-1 text-sm">
            Reach high-intent users at the exact moment they ask questions. Contextually matched & zero hallucination.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Balance Widget */}
          <div className="flex items-center gap-3 rounded-lg border bg-card px-4 py-2 shadow-sm">
            <Wallet className="h-5 w-5 text-emerald-500" />
            <div>
              <div className="text-xs text-muted-foreground">Available Balance</div>
              <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
                ${balance.toFixed(2)} {currency}
              </div>
            </div>
            <Button size="sm" variant="outline" onClick={() => setIsTopUpModalOpen(true)} className="ml-2">
              <CreditCard className="mr-1 h-3.5 w-3.5" /> Top-Up
            </Button>
          </div>

          <Button onClick={handleOpenCreateCampaign} className="bg-blue-600 hover:bg-blue-700 text-white">
            <Plus className="mr-1.5 h-4 w-4" /> New Campaign
          </Button>

          <Button variant="ghost" size="icon" onClick={fetchDashboard} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Campaigns</CardTitle>
            <Megaphone className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboard?.active_campaigns || 0}{' '}
              <span className="text-xs font-normal text-muted-foreground">/ {dashboard?.total_campaigns || 0} total</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">Live in AI query auction</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Impressions</CardTitle>
            <Activity className="h-4 w-4 text-indigo-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(dashboard?.total_impressions || 0).toLocaleString()}</div>
            <p className="text-xs text-muted-foreground mt-1">Times recommendations shown</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Clicks & Engagement</CardTitle>
            <MousePointer className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(dashboard?.total_clicks || 0).toLocaleString()}{' '}
              <span className="text-sm font-normal text-emerald-500">({dashboard?.ctr || 0}% CTR)</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">Verified outbound visits</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Spend</CardTitle>
            <DollarSign className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${(dashboard?.total_spent || 0).toFixed(2)}</div>
            <p className="text-xs text-muted-foreground mt-1">All-time advertising investment</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs Section */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="campaigns" className="flex items-center gap-2">
            <Layers className="h-4 w-4" /> Campaigns ({dashboard?.campaigns?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="billing" className="flex items-center gap-2">
            <DollarSign className="h-4 w-4" /> Billing & Transactions
          </TabsTrigger>
          <TabsTrigger value="guide" className="flex items-center gap-2">
            <HelpCircle className="h-4 w-4" /> How Swipies Ads Work
          </TabsTrigger>
        </TabsList>

        {/* 1. Campaigns Tab */}
        <TabsContent value="campaigns" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Your Advertising Campaigns</CardTitle>
              <CardDescription>
                Manage AI intent targeting, daily budgets, bids, and ad copy.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!dashboard?.campaigns || dashboard.campaigns.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-500/10 text-blue-500 mb-3">
                    <Megaphone className="h-6 w-6" />
                  </div>
                  <h3 className="text-lg font-semibold">No Campaigns Yet</h3>
                  <p className="text-sm text-muted-foreground max-w-sm mt-1">
                    Launch your first sponsored AI recommendation campaign and connect with users looking for your solutions.
                  </p>
                  <Button onClick={handleOpenCreateCampaign} className="mt-4 bg-blue-600 hover:bg-blue-700 text-white">
                    <Plus className="mr-1.5 h-4 w-4" /> Create First Campaign
                  </Button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b bg-muted/40 text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="py-3 px-4">Campaign / Product</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4">Model & Bid</th>
                        <th className="py-3 px-4">Budget & Spend</th>
                        <th className="py-3 px-4">Impressions</th>
                        <th className="py-3 px-4">Clicks (CTR)</th>
                        <th className="py-3 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {dashboard.campaigns.map((cmp) => (
                        <tr key={cmp.id} className="hover:bg-muted/30 transition-colors">
                          <td className="py-3 px-4">
                            <div className="font-semibold text-foreground">{cmp.name}</div>
                            <div className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
                              <span className="font-medium text-blue-500">{cmp.product_name}</span>
                              <span>•</span>
                              <a
                                href={cmp.landing_url}
                                target="_blank"
                                rel="noreferrer"
                                className="hover:underline flex items-center gap-0.5 text-xs text-muted-foreground truncate max-w-[200px]"
                              >
                                {cmp.landing_url} <ExternalLink className="h-2.5 w-2.5 inline" />
                              </a>
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex flex-col gap-1">
                              <Badge
                                variant="outline"
                                className={
                                  cmp.status === 'active'
                                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-500'
                                    : 'border-zinc-500/30 bg-zinc-500/10 text-zinc-400'
                                }
                              >
                                {cmp.status === 'active' ? 'Active' : 'Paused'}
                              </Badge>
                              {cmp.moderation_status === 'pending' && (
                                <Badge variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-500 text-[10px]">
                                  Moderation Pending
                                </Badge>
                              )}
                              {cmp.moderation_status === 'rejected' && (
                                <Badge variant="outline" className="border-red-500/30 bg-red-500/10 text-red-500 text-[10px]">
                                  Rejected
                                </Badge>
                              )}
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <div className="font-medium uppercase text-xs">{cmp.pricing_model}</div>
                            <div className="text-xs text-muted-foreground font-semibold">
                              ${cmp.bid_amount.toFixed(2)} / {cmp.pricing_model === 'cpc' ? 'click' : '1k imp'}
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <div className="text-xs">
                              <span className="font-bold">${cmp.spent_today.toFixed(2)}</span> / ${cmp.daily_budget.toFixed(2)} day
                            </div>
                            <div className="text-[11px] text-muted-foreground">
                              Total: ${cmp.total_spent.toFixed(2)} / ${cmp.total_budget.toFixed(2)}
                            </div>
                          </td>
                          <td className="py-3 px-4 font-medium">{cmp.impressions.toLocaleString()}</td>
                          <td className="py-3 px-4">
                            <div className="font-semibold text-emerald-600 dark:text-emerald-400">{cmp.clicks.toLocaleString()}</div>
                            <div className="text-xs text-muted-foreground">{cmp.ctr}% CTR</div>
                          </td>
                          <td className="py-3 px-4 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleToggleStatus(cmp)}
                                title={cmp.status === 'active' ? 'Pause Campaign' : 'Activate Campaign'}
                              >
                                {cmp.status === 'active' ? (
                                  <Pause className="h-4 w-4 text-amber-500" />
                                ) : (
                                  <Play className="h-4 w-4 text-emerald-500" />
                                )}
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleOpenAnalytics(cmp)}
                                title="View Analytics"
                              >
                                <BarChart3 className="h-4 w-4 text-blue-500" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleOpenEditCampaign(cmp)}
                                title="Edit Campaign"
                              >
                                <Edit3 className="h-4 w-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleDeleteCampaign(cmp)}
                                title="Archive Campaign"
                              >
                                <Trash2 className="h-4 w-4 text-red-500" />
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

        {/* 2. Billing Tab */}
        <TabsContent value="billing" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="md:col-span-1">
              <CardHeader>
                <CardTitle>Advertiser Wallet</CardTitle>
                <CardDescription>Manage advertising funds and payment deposits</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border bg-muted/40 p-4 text-center">
                  <div className="text-xs text-muted-foreground uppercase tracking-wider">Available Balance</div>
                  <div className="text-3xl font-extrabold text-emerald-600 dark:text-emerald-400 mt-1">
                    ${balance.toFixed(2)} {currency}
                  </div>
                </div>

                <Button onClick={() => setIsTopUpModalOpen(true)} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white">
                  <Plus className="mr-1.5 h-4 w-4" /> Top-Up Account Balance
                </Button>
              </CardContent>
            </Card>

            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Recent Transactions</CardTitle>
                <CardDescription>Ledger of deposits and advertising spend deductions</CardDescription>
              </CardHeader>
              <CardContent>
                {transactions.length === 0 ? (
                  <div className="py-8 text-center text-sm text-muted-foreground">No transactions recorded yet.</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="border-b bg-muted/40 uppercase text-muted-foreground">
                        <tr>
                          <th className="py-2.5 px-3">Type</th>
                          <th className="py-2.5 px-3">Description</th>
                          <th className="py-2.5 px-3">Amount</th>
                          <th className="py-2.5 px-3">Date</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {transactions.map((t) => (
                          <tr key={t.id} className="hover:bg-muted/20">
                            <td className="py-2.5 px-3 font-semibold uppercase">{t.type}</td>
                            <td className="py-2.5 px-3">{t.description}</td>
                            <td className="py-2.5 px-3">
                              <span className={t.amount >= 0 ? 'text-emerald-500 font-bold' : 'text-zinc-400'}>
                                {t.amount >= 0 ? `+$${t.amount.toFixed(2)}` : `-$${Math.abs(t.amount).toFixed(2)}`}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-muted-foreground">
                              {new Date(t.created_at).toLocaleDateString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* 3. Educational Guide Tab */}
        <TabsContent value="guide" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-blue-500" /> The Swipies Ads Principles
              </CardTitle>
              <CardDescription>
                How native AI intent recommendations work without spamming users or sacrificing answer quality.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-muted-foreground leading-relaxed">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-lg border p-4 bg-muted/20">
                  <div className="font-semibold text-foreground flex items-center gap-2 mb-2">
                    <Target className="h-4 w-4 text-blue-500" /> 1. Intent & Semantic Matching
                  </div>
                  <p className="text-xs">
                    Your ad only participates in the auction when a user asks a question directly relevant to your product category. If the query is unrelated, no ad is forced.
                  </p>
                </div>

                <div className="rounded-lg border p-4 bg-muted/20">
                  <div className="font-semibold text-foreground flex items-center gap-2 mb-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" /> 2. Transparent & Non-Intrusive
                  </div>
                  <p className="text-xs">
                    Recommendations are explicitly labeled with <span className="font-bold text-foreground">[Sponsored]</span> and separated from the main AI answer.
                  </p>
                </div>

                <div className="rounded-lg border p-4 bg-muted/20">
                  <div className="font-semibold text-foreground flex items-center gap-2 mb-2">
                    <TrendingUp className="h-4 w-4 text-purple-500" /> 3. Performance Driven (CPC/CPM)
                  </div>
                  <p className="text-xs">
                    Pay only when interested users engage or visit your landing page. Set strict daily budgets to control costs with 100% transparency.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Create / Edit Campaign Modal */}
      <Dialog open={isCampaignModalOpen} onOpenChange={setIsCampaignModalOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{selectedCampaign ? 'Edit Campaign' : 'Create New Campaign'}</DialogTitle>
            <DialogDescription>
              Define your product offer, ad copy, targeting keywords, and budget parameters.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4 max-h-[70vh] overflow-y-auto pr-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Campaign Name *</label>
                <Input
                  placeholder="e.g. Q3 Sales Pipeline Growth"
                  value={campaignForm.name}
                  onChange={(e) => setCampaignForm({ ...campaignForm, name: e.target.value })}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Product / Service Name *</label>
                <Input
                  placeholder="e.g. Acme CRM Cloud"
                  value={campaignForm.product_name}
                  onChange={(e) => setCampaignForm({ ...campaignForm, product_name: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Product Description & Key Differentiator</label>
              <Input
                placeholder="e.g. AI-powered CRM with automated WhatsApp sync and lead scoring"
                value={campaignForm.description}
                onChange={(e) => setCampaignForm({ ...campaignForm, description: e.target.value })}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Ad Copy (Recommended Offer) *</label>
              <Textarea
                placeholder="e.g. Get 30 days free trial with instant setup. No credit card required."
                rows={2}
                value={campaignForm.advertisement_text}
                onChange={(e) => setCampaignForm({ ...campaignForm, advertisement_text: e.target.value })}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Landing Page URL *</label>
              <Input
                placeholder="https://yourcompany.com/landing"
                value={campaignForm.landing_url}
                onChange={(e) => setCampaignForm({ ...campaignForm, landing_url: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Target Keywords (Comma-separated)</label>
                <Input
                  placeholder="crm, sales, leads, automation"
                  value={rawKeywords}
                  onChange={(e) => setRawKeywords(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Target Categories (Comma-separated)</label>
                <Input
                  placeholder="software, business, marketing"
                  value={rawCategories}
                  onChange={(e) => setRawCategories(e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Pricing Model</label>
                <Select
                  value={campaignForm.pricing_model}
                  onValueChange={(val: any) => setCampaignForm({ ...campaignForm, pricing_model: val })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cpc">CPC (Cost Per Click)</SelectItem>
                    <SelectItem value="cpm">CPM (Cost Per 1,000 Views)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Bid Amount ($)</label>
                <Input
                  type="number"
                  step="0.01"
                  value={campaignForm.bid_amount}
                  onChange={(e) => setCampaignForm({ ...campaignForm, bid_amount: parseFloat(e.target.value) })}
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Daily Budget ($)</label>
                <Input
                  type="number"
                  step="1"
                  value={campaignForm.daily_budget}
                  onChange={(e) => setCampaignForm({ ...campaignForm, daily_budget: parseFloat(e.target.value) })}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCampaignModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveCampaign} className="bg-blue-600 hover:bg-blue-700 text-white">
              Save Campaign
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Top-Up Wallet Modal */}
      <Dialog open={isTopUpModalOpen} onOpenChange={setIsTopUpModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-emerald-600" />
              Пополнение рекламного баланса
            </DialogTitle>
            <DialogDescription>
              Выберите сумму для пополнения счета рекламодателя через Atmos.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="grid grid-cols-4 gap-2">
              {['20', '50', '100', '250'].map((amt) => (
                <Button
                  key={amt}
                  variant={topUpAmount === amt ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setTopUpAmount(amt)}
                >
                  ${amt}
                </Button>
              ))}
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Сумма пополнения ($ USD)</label>
              <Input
                type="number"
                step="5"
                min="5"
                value={topUpAmount}
                onChange={(e) => setTopUpAmount(e.target.value)}
              />
            </div>

            <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-xs text-blue-800 flex justify-between items-center">
              <span>К оплате через Atmos:</span>
              <span className="font-bold text-sm text-blue-900">
                {(Math.round(parseFloat(topUpAmount || '0') * 12800)).toLocaleString()} UZS
              </span>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsTopUpModalOpen(false)}>
              Отмена
            </Button>
            <Button
              onClick={() => {
                const num = parseFloat(topUpAmount);
                if (isNaN(num) || num <= 0) {
                  message.error('Укажите корректную сумму');
                  return;
                }
                setIsTopUpModalOpen(false);
                setIsAtmosModalOpen(true);
              }}
              className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold flex items-center gap-1.5"
            >
              <CreditCard className="h-4 w-4" />
              Оплатить картой (${parseFloat(topUpAmount || '0').toFixed(2)})
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Atmos Payment Checkout Modal */}
      <AtmosPaymentModal
        open={isAtmosModalOpen}
        onOpenChange={setIsAtmosModalOpen}
        purpose="advertiser_deposit"
        advertiserId={dashboard?.advertiser_id}
        amountUsd={parseFloat(topUpAmount || '50')}
        onSuccess={() => {
          fetchDashboard();
          fetchTransactions();
        }}
      />

      {/* Campaign Analytics Modal */}
      <Dialog open={isAnalyticsModalOpen} onOpenChange={setIsAnalyticsModalOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Analytics: {selectedCampaign?.name}</DialogTitle>
            <DialogDescription>Recent user intent matches and engagement telemetry.</DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-3">
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="rounded border bg-muted/20 p-2.5">
                <div className="text-xs text-muted-foreground">Impressions</div>
                <div className="text-lg font-bold">{analyticsData?.total_impressions || 0}</div>
              </div>
              <div className="rounded border bg-muted/20 p-2.5">
                <div className="text-xs text-muted-foreground">Clicks</div>
                <div className="text-lg font-bold text-emerald-500">{analyticsData?.total_clicks || 0}</div>
              </div>
              <div className="rounded border bg-muted/20 p-2.5">
                <div className="text-xs text-muted-foreground">Total Spent</div>
                <div className="text-lg font-bold">${(analyticsData?.total_spent || 0).toFixed(2)}</div>
              </div>
            </div>

            <div>
              <div className="text-xs font-semibold mb-2">Recent Matching Query Intents</div>
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {analyticsData?.recent_impressions?.length === 0 ? (
                  <div className="text-xs text-muted-foreground py-2 text-center">No impressions recorded yet.</div>
                ) : (
                  analyticsData?.recent_impressions?.map((imp: any) => (
                    <div key={imp.id} className="rounded border p-2 text-xs flex justify-between items-center">
                      <span className="truncate max-w-[320px] italic">"{imp.query_intent}"</span>
                      <span className="text-muted-foreground text-[10px]">
                        {new Date(imp.time).toLocaleTimeString()}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button onClick={() => setIsAnalyticsModalOpen(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
