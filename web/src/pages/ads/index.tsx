import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertCircle,
  BarChart3,
  CheckCircle2,
  Coins,
  CreditCard,
  DollarSign,
  Download,
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
  Globe,
  Smartphone,
  Laptop,
  Cpu,
  FlaskConical,
  Shuffle,
  Trophy,
  ShieldCheck,
  Calendar,
  RotateCw,
  XCircle,
  MapPin,
  Code2,
  Copy,
  Check,
  Lightbulb,
  Wand2,
  Sliders,
} from 'lucide-react';
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
  AdVariantItem,
  AdTransactionItem,
  AdvertiserDashboardData,
  TimelineAnalyticsData,
  CampaignDetailedAnalyticsData,
  UserSubscriptionData,
  SavedPaymentMethodItem,
} from '@/services/ad-service';

export default function SwipiesAdsPage() {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<AdvertiserDashboardData | null>(null);
  const [transactions, setTransactions] = useState<AdTransactionItem[]>([]);
  const [activeTab, setActiveTab] = useState('campaigns');

  // Subscription & Saved Cards state
  const [subscription, setSubscription] = useState<UserSubscriptionData | null>(null);
  const [savedCards, setSavedCards] = useState<SavedPaymentMethodItem[]>([]);
  const [isCardsModalOpen, setIsCardsModalOpen] = useState(false);
  const [loadingSubscriptionAction, setLoadingSubscriptionAction] = useState(false);

  // Timeline Analytics state
  const [timelineData, setTimelineData] = useState<TimelineAnalyticsData | null>(null);
  const [timelineDays, setTimelineDays] = useState<number>(14);
  const [loadingTimeline, setLoadingTimeline] = useState<boolean>(false);

  // Modals state
  const [isCampaignModalOpen, setIsCampaignModalOpen] = useState(false);
  const [isTopUpModalOpen, setIsTopUpModalOpen] = useState(false);
  const [isAtmosModalOpen, setIsAtmosModalOpen] = useState(false);
  const [isAnalyticsModalOpen, setIsAnalyticsModalOpen] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState<AdCampaignItem | null>(null);
  const [analyticsData, setAnalyticsData] = useState<CampaignDetailedAnalyticsData | any>(null);

  // A/B Testing Modal state
  const [isVariantsModalOpen, setIsVariantsModalOpen] = useState(false);
  const [variantsCampaign, setVariantsCampaign] = useState<AdCampaignItem | null>(null);
  const [variantsList, setVariantsList] = useState<AdVariantItem[]>([]);
  const [loadingVariants, setLoadingVariants] = useState(false);
  const [newVariantName, setNewVariantName] = useState('');
  const [newVariantText, setNewVariantText] = useState('');
  const [newVariantUrl, setNewVariantUrl] = useState('');
  const [newVariantWeight, setNewVariantWeight] = useState('1.0');
  const [isGeneratingVariantCopy, setIsGeneratingVariantCopy] = useState(false);

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
    target_cpa: 5.0,
  });
  const [rawKeywords, setRawKeywords] = useState('');
  const [rawCategories, setRawCategories] = useState('');
  const [rawNegativeKeywords, setRawNegativeKeywords] = useState('');
  const [targetLanguages, setTargetLanguages] = useState<string[]>(['all']);
  const [targetModels, setTargetModels] = useState<string[]>(['all']);
  const [targetRegions, setTargetRegions] = useState<string[]>(['all']);
  const [topUpAmount, setTopUpAmount] = useState('50');
  const [isGeneratingCopy, setIsGeneratingCopy] = useState(false);

  // Conversion Pixel State
  const [isPixelModalOpen, setIsPixelModalOpen] = useState(false);
  const [pixelData, setPixelData] = useState<PixelSnippetData | null>(null);
  const [loadingPixel, setLoadingPixel] = useState(false);
  const [copiedSnippet, setCopiedSnippet] = useState(false);
  const [testOrderValue, setTestOrderValue] = useState('49.99');
  const [isSendingTestEvent, setIsSendingTestEvent] = useState(false);

  // AI Optimizer & Insights State
  const [insightsData, setInsightsData] = useState<AdvertiserInsightsData | null>(null);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [applyingInsightId, setApplyingInsightId] = useState<string | null>(null);

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

  const fetchInsights = async () => {
    setLoadingInsights(true);
    try {
      const res = await adService.getAdvertiserInsights();
      if (res.data?.data) {
        setInsightsData(res.data.data);
      }
    } catch (err: any) {
      // silently handle
    } finally {
      setLoadingInsights(false);
    }
  };

  const handleApplyInsight = async (insight: CampaignInsightItem) => {
    setApplyingInsightId(insight.id);
    try {
      const res = await adService.applyCampaignInsight(
        insight.campaign_id,
        insight.type,
        insight.action_payload
      );
      if (res.data?.data?.success) {
        message.success(res.data.data.message || 'Рекомендация успешно применена!');
        fetchInsights();
        fetchDashboard();
      }
    } catch (err: any) {
      message.error(err.message || 'Ошибка применения рекомендации');
    } finally {
      setApplyingInsightId(null);
    }
  };

  const fetchTimeline = async (days: number = timelineDays) => {
    setLoadingTimeline(true);
    try {
      const res = await adService.getAdvertiserTimeline(days);
      if (res.data?.data) {
        setTimelineData(res.data.data);
      }
    } catch (err: any) {
      console.error('Failed to load timeline analytics', err);
    } finally {
      setLoadingTimeline(false);
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

  const fetchSubscription = async () => {
    try {
      const res = await adService.getUserSubscription();
      if (res.data?.data) {
        setSubscription(res.data.data);
      }
    } catch (err: any) {
      console.error('Failed to load subscription info', err);
    }
  };

  const fetchSavedCards = async () => {
    try {
      const res = await adService.getSavedPaymentMethods();
      if (res.data?.data) {
        setSavedCards(res.data.data);
      }
    } catch (err: any) {
      console.error('Failed to load saved cards', err);
    }
  };

  const handleToggleAutoRenew = async () => {
    if (!subscription) return;
    setLoadingSubscriptionAction(true);
    try {
      if (subscription.auto_renew) {
        await adService.cancelSubscription(false);
        message.success('Автопродление подписки отключено. Подписка активна до окончания оплаченного периода.');
      } else {
        await adService.resumeSubscription();
        message.success('Автопродление подписки успешно возобновлено!');
      }
      fetchSubscription();
    } catch (err: any) {
      message.error(err.message || 'Ошибка обновления статуса автопродления');
    } finally {
      setLoadingSubscriptionAction(false);
    }
  };

  const handleDeleteCard = async (cardId: string) => {
    try {
      await adService.deleteSavedPaymentMethod(cardId);
      message.success('Карта успешно удалена');
      fetchSavedCards();
      fetchSubscription();
    } catch (err: any) {
      message.error(err.message || 'Не удалось удалить карту');
    }
  };

  const handleTriggerRenewals = async () => {
    try {
      const res = await adService.adminProcessRenewals();
      message.info(`Шедулер продления: обработано ${res.data?.data?.processed || 0}, продлено ${res.data?.data?.renewed || 0}`);
      fetchSubscription();
    } catch (err: any) {
      message.error('Ошибка запуска шедулера');
    }
  };

  useEffect(() => {
    fetchDashboard();
    fetchTransactions();
    fetchTimeline(timelineDays);
    fetchSubscription();
    fetchSavedCards();
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
      negative_keywords: [],
      daily_budget: 10,
      total_budget: 100,
      pricing_model: 'cpc',
      bid_amount: 0.15,
    });
    setRawKeywords('');
    setRawCategories('');
    setRawNegativeKeywords('');
    setTargetLanguages(['all']);
    setTargetModels(['all']);
    setTargetRegions(['all']);
    setIsCampaignModalOpen(true);
  };

  const handleOpenEditCampaign = (cmp: AdCampaignItem) => {
    setSelectedCampaign(cmp);
    setCampaignForm({ ...cmp });
    setRawKeywords((cmp.keywords || []).join(', '));
    setRawCategories((cmp.target_categories || []).join(', '));
    setRawNegativeKeywords((cmp.negative_keywords || []).join(', '));
    setTargetLanguages(cmp.target_languages && cmp.target_languages.length > 0 ? cmp.target_languages : ['all']);
    setTargetModels(cmp.target_models && cmp.target_models.length > 0 ? cmp.target_models : ['all']);
    setTargetRegions(cmp.target_regions && cmp.target_regions.length > 0 ? cmp.target_regions : ['all']);
    setIsCampaignModalOpen(true);
  };

  const handleGenerateAICopy = async () => {
    if (!campaignForm.product_name) {
      message.warning('Пожалуйста, укажите название продукта перед генерацией.');
      return;
    }
    setIsGeneratingCopy(true);
    try {
      const selectedLang = targetLanguages.includes('uz') ? 'uz' : targetLanguages.includes('en') ? 'en' : 'ru';
      const res = await adService.generateCopy({
        product_name: campaignForm.product_name,
        landing_url: campaignForm.landing_url,
        description: campaignForm.description,
        lang: selectedLang,
      });
      if (res.data?.data) {
        const data = res.data.data;
        if (data.ad_copy_variations && data.ad_copy_variations.length > 0) {
          setCampaignForm((prev) => ({
            ...prev,
            advertisement_text: data.ad_copy_variations[0],
            bid_amount: data.recommended_bid || prev.bid_amount,
          }));
        }
        if (data.recommended_keywords && data.recommended_keywords.length > 0) {
          setRawKeywords(data.recommended_keywords.join(', '));
        }
        if (data.recommended_negative_keywords && data.recommended_negative_keywords.length > 0) {
          setRawNegativeKeywords(data.recommended_negative_keywords.join(', '));
        }
        if (data.recommended_categories && data.recommended_categories.length > 0) {
          setRawCategories(data.recommended_categories.join(', '));
        }
        message.success('AI успешно сгенерировал продающий текст и ключевые слова!');
      }
    } catch (err: any) {
      message.error(err.message || 'Ошибка при генерации текста');
    } finally {
      setIsGeneratingCopy(false);
    }
  };

  const toggleLanguage = (langCode: string) => {
    if (langCode === 'all') {
      setTargetLanguages(['all']);
      return;
    }
    const filtered = targetLanguages.filter((l) => l !== 'all');
    if (filtered.includes(langCode)) {
      const next = filtered.filter((l) => l !== langCode);
      setTargetLanguages(next.length === 0 ? ['all'] : next);
    } else {
      setTargetLanguages([...filtered, langCode]);
    }
  };

  const toggleModel = (modelCode: string) => {
    if (modelCode === 'all') {
      setTargetModels(['all']);
      return;
    }
    const filtered = targetModels.filter((m) => m !== 'all');
    if (filtered.includes(modelCode)) {
      const next = filtered.filter((m) => m !== modelCode);
      setTargetModels(next.length === 0 ? ['all'] : next);
    } else {
      setTargetModels([...filtered, modelCode]);
    }
  };

  const toggleRegion = (regionCode: string) => {
    if (regionCode === 'all') {
      setTargetRegions(['all']);
      return;
    }
    const filtered = targetRegions.filter((r) => r !== 'all');
    if (filtered.includes(regionCode)) {
      const next = filtered.filter((r) => r !== regionCode);
      setTargetRegions(next.length === 0 ? ['all'] : next);
    } else {
      setTargetRegions([...filtered, regionCode]);
    }
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
    const negative_keywords = rawNegativeKeywords
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    const payload = {
      ...campaignForm,
      keywords,
      target_categories,
      negative_keywords,
      target_languages: targetLanguages,
      target_models: targetModels,
      target_regions: targetRegions,
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
    setIsAnalyticsModalOpen(true);
    try {
      const res = await adService.getCampaignAnalyticsDetailed(cmp.id, 14);
      setAnalyticsData(res.data?.data || null);
    } catch (err: any) {
      message.error('Failed to load campaign analytics');
    }
  };

  const fetchVariants = async (campaignId: string) => {
    setLoadingVariants(true);
    try {
      const res = await adService.getCampaignVariants(campaignId);
      if (res.data?.data) {
        setVariantsList(res.data.data);
      }
    } catch (err: any) {
      message.error(err.message || 'Ошибка загрузки вариантов объявления');
    } finally {
      setLoadingVariants(false);
    }
  };

  const handleOpenVariants = (cmp: AdCampaignItem) => {
    setVariantsCampaign(cmp);
    setNewVariantName('');
    setNewVariantText('');
    setNewVariantUrl(cmp.landing_url || '');
    setNewVariantWeight('1.0');
    setIsVariantsModalOpen(true);
    fetchVariants(cmp.id);
  };

  const handleCreateVariant = async () => {
    if (!variantsCampaign) return;
    if (!newVariantText.trim()) {
      message.error('Укажите текст рекламного объявления для нового варианта');
      return;
    }
    try {
      await adService.createCampaignVariant(variantsCampaign.id, {
        name: newVariantName.trim() || `Вариант ${variantsList.length + 1}`,
        advertisement_text: newVariantText.trim(),
        landing_url: newVariantUrl.trim() || undefined,
        weight: parseFloat(newVariantWeight) || 1.0,
        is_active: true,
      });
      message.success('Новый вариант объявления добавлен в ротацию!');
      setNewVariantName('');
      setNewVariantText('');
      setNewVariantUrl(variantsCampaign.landing_url || '');
      setNewVariantWeight('1.0');
      fetchVariants(variantsCampaign.id);
    } catch (err: any) {
      message.error(err.message || 'Ошибка при создании варианта');
    }
  };

  const handleToggleVariant = async (v: AdVariantItem) => {
    if (!variantsCampaign) return;
    try {
      await adService.toggleCampaignVariant(variantsCampaign.id, v.id);
      message.success(`Вариант «${v.name}» ${v.is_active ? 'поставлен на паузу' : 'активирован'}!`);
      fetchVariants(variantsCampaign.id);
    } catch (err: any) {
      message.error(err.message || 'Ошибка при изменении статуса варианта');
    }
  };

  const handleDeleteVariant = async (v: AdVariantItem) => {
    if (!variantsCampaign) return;
    try {
      await adService.deleteCampaignVariant(variantsCampaign.id, v.id);
      message.success(`Вариант «${v.name}» удален!`);
      fetchVariants(variantsCampaign.id);
    } catch (err: any) {
      message.error(err.message || 'Ошибка при удалении варианта');
    }
  };

  const handleGenerateVariantAI = async () => {
    if (!variantsCampaign) return;
    setIsGeneratingVariantCopy(true);
    try {
      const res = await adService.generateCopy({
        product_name: variantsCampaign.product_name,
        landing_url: variantsCampaign.landing_url,
        description: `Альтернативный продающий оффер для A/B тестирования: ${variantsCampaign.name}`,
        lang: 'ru',
      });
      if (res.data?.data?.ad_copy_variations && res.data.data.ad_copy_variations.length > 0) {
        const altIndex = Math.min(1, res.data.data.ad_copy_variations.length - 1);
        setNewVariantText(res.data.data.ad_copy_variations[altIndex] || res.data.data.ad_copy_variations[0]);
        if (!newVariantName) {
          setNewVariantName(`Вариант ${variantsList.length + 1} (AI Оффер)`);
        }
        message.success('AI сгенерировал новый вариант рекламного текста!');
      }
    } catch (err: any) {
      message.error(err.message || 'Ошибка при генерации варианта');
    } finally {
      setIsGeneratingVariantCopy(false);
    }
  };

  const handleOpenPixelModal = async () => {
    setIsPixelModalOpen(true);
    setLoadingPixel(true);
    try {
      const res = await adService.getPixelSnippet();
      if (res.data?.data) {
        setPixelData(res.data.data);
      }
    } catch (err: any) {
      message.error(err.message || 'Failed to load pixel snippet');
    } finally {
      setLoadingPixel(false);
    }
  };

  const handleCopySnippet = () => {
    if (pixelData?.snippet) {
      navigator.clipboard.writeText(pixelData.snippet);
      setCopiedSnippet(true);
      message.success('JS-код пикселя скопирован в буфер обмена!');
      setTimeout(() => setCopiedSnippet(false), 3000);
    }
  };

  const handleTestPixelEvent = async () => {
    if (!pixelData?.pixel_id) return;
    setIsSendingTestEvent(true);
    try {
      const val = parseFloat(testOrderValue) || 10.0;
      const res = await adService.testPixelTrack({
        pixel_id: pixelData.pixel_id,
        event: 'purchase',
        value: val,
        order_id: 'TEST-' + Math.floor(100000 + Math.random() * 900000),
      });
      if (res.data?.data) {
        message.success(`Тестовая конверсия ($${val}) успешно зарегистрирована!`);
        fetchDashboard();
      }
    } catch (err: any) {
      message.error(err.message || 'Ошибка тестовой отправки');
    } finally {
      setIsSendingTestEvent(false);
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

          <Button
            variant="outline"
            onClick={handleOpenPixelModal}
            className="border-purple-500/30 text-purple-600 dark:text-purple-400 hover:bg-purple-500/10"
          >
            <Code2 className="mr-1.5 h-4 w-4" /> Пиксель конверсий
          </Button>

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
          <TabsTrigger value="insights" className="flex items-center gap-2 relative">
            <Lightbulb className="h-4 w-4 text-amber-500" />
            AI Оптимизатор
            {insightsData && insightsData.total_insights > 0 && (
              <span className="ml-1 inline-flex items-center justify-center px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-amber-500 text-white animate-pulse">
                {insightsData.total_insights}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="analytics" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-blue-500" /> Аналитика & Графики
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
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Your Advertising Campaigns</CardTitle>
                <CardDescription>
                  Manage AI intent targeting, daily budgets, bids, and ad copy.
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="text-xs flex items-center gap-1.5"
                  onClick={() => window.open('/v1/ads/export/campaigns', '_blank')}
                >
                  <Download className="h-3.5 w-3.5" /> Экспорт CSV
                </Button>
                <Button onClick={handleOpenCreateCampaign} size="sm" className="bg-blue-600 hover:bg-blue-700 text-white text-xs">
                  <Plus className="mr-1 h-3.5 w-3.5" /> New Campaign
                </Button>
              </div>
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
                            <div className="flex flex-wrap gap-1 mt-1.5">
                              {(!cmp.target_languages || cmp.target_languages.includes('all') || cmp.target_languages.length === 0) ? (
                                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300 font-medium">🌐 Все языки</span>
                              ) : (
                                cmp.target_languages.map((l) => (
                                  <span key={l} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-sky-50 text-sky-700 dark:bg-sky-950/50 dark:text-sky-300 font-bold uppercase">
                                    {l === 'uz' ? '🇺🇿 UZ' : l === 'ru' ? '🇷🇺 RU' : l === 'en' ? '🇬🇧 EN' : l}
                                  </span>
                                ))
                              )}
                              {cmp.target_models && cmp.target_models.length > 0 && !cmp.target_models.includes('all') && (
                                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-purple-50 text-purple-700 dark:bg-purple-950/50 dark:text-purple-300 font-medium">
                                  🤖 {cmp.target_models.join(', ')}
                                </span>
                              )}
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
                            <div className="font-medium uppercase text-xs flex items-center gap-1">
                              {cmp.pricing_model}
                              {cmp.pricing_model === 'cpa' && (
                                <span className="inline-flex items-center px-1 rounded text-[9px] bg-purple-500/20 text-purple-600 dark:text-purple-300 font-bold">
                                  ⚡ AUTO
                                </span>
                              )}
                            </div>
                            <div className="text-xs text-muted-foreground font-semibold">
                              {cmp.pricing_model === 'cpa'
                                ? `$${(cmp.target_cpa || 5.0).toFixed(2)} Target CPA`
                                : `$${cmp.bid_amount.toFixed(2)} / ${cmp.pricing_model === 'cpc' ? 'click' : '1k imp'}`}
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
                            {((cmp.conversions_count && cmp.conversions_count > 0) || cmp.pricing_model === 'cpa') && (
                              <div className="text-[11px] font-medium text-purple-600 dark:text-purple-400 mt-0.5">
                                🎯 {cmp.conversions_count || 0} conv ({cmp.conversion_rate || 0}% CVR)
                              </div>
                            )}
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
                                onClick={() => handleOpenVariants(cmp)}
                                title="A/B Тестирование & Варианты"
                                className="text-purple-600 hover:text-purple-700 dark:text-purple-400"
                              >
                                <FlaskConical className="h-4 w-4" />
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

        {/* AI Campaign Optimizer & Copilot Tab */}
        <TabsContent value="insights" className="space-y-6">
          {/* Optimization Header / Score Card */}
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-6 rounded-xl border bg-gradient-to-r from-amber-500/10 via-purple-500/10 to-blue-500/10 dark:from-amber-950/30 dark:via-purple-950/30 dark:to-blue-950/30">
            <div className="flex items-center gap-4">
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-amber-500/20 text-amber-600 dark:text-amber-400 font-extrabold text-2xl border border-amber-500/30">
                {insightsData?.score || 100}%
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-bold">AI Рекламный Аудит & Оптимизатор</h3>
                  <Badge variant="outline" className="border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400">
                    <Sparkles className="mr-1 h-3 w-3" /> Smart Copilot
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground mt-1 max-w-xl">
                  AI в реальном времени анализирует воронку конверсий, качество ключевых слов, CTR офферов и защищает бюджет от нецелевых кликов.
                </p>
              </div>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={fetchInsights}
              disabled={loadingInsights}
              className="bg-background hover:bg-muted text-xs flex items-center gap-1.5 shrink-0"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loadingInsights ? 'animate-spin' : ''}`} />
              Пересканировать кампании
            </Button>
          </div>

          {/* Recommendations List */}
          {loadingInsights ? (
            <div className="flex flex-col items-center justify-center py-16">
              <RefreshCw className="h-8 w-8 animate-spin text-amber-500 mb-2" />
              <p className="text-sm text-muted-foreground">Идет аудит рекламных кампаний...</p>
            </div>
          ) : !insightsData || insightsData.insights.length === 0 ? (
            <Card className="p-8 text-center border-dashed">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500 mx-auto mb-3">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <h4 className="text-base font-bold text-foreground">Кампании максимально оптимизированы!</h4>
              <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
                Все ваши кампании имеют отличные показатели релевантности, настроенные минус-слова, A/B варианты и корректные ставки.
              </p>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {insightsData.insights.map((insight) => (
                <Card key={insight.id} className="relative flex flex-col justify-between border shadow-sm hover:border-amber-500/40 transition-colors">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <Badge
                        variant="outline"
                        className={
                          insight.category === 'cost'
                            ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[10px]'
                            : insight.category === 'quality'
                            ? 'border-rose-500/30 bg-rose-500/10 text-rose-600 dark:text-rose-400 text-[10px]'
                            : insight.category === 'reach'
                            ? 'border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400 text-[10px]'
                            : 'border-purple-500/30 bg-purple-500/10 text-purple-600 dark:text-purple-400 text-[10px]'
                        }
                      >
                        {insight.category === 'cost' && '🛡️ Защита бюджета'}
                        {insight.category === 'quality' && '🎨 Оффер & CTR'}
                        {insight.category === 'reach' && '🔍 Охват запросов'}
                        {insight.category === 'growth' && '🧪 A/B Эксперимент'}
                        {insight.category === 'bidding' && '⚡ Smart CPA'}
                      </Badge>

                      <div className="flex items-center gap-1">
                        <span className="text-[11px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/20">
                          {insight.estimated_impact}
                        </span>
                      </div>
                    </div>

                    <CardTitle className="text-base font-semibold leading-snug">{insight.title}</CardTitle>
                    <div className="text-xs text-muted-foreground font-medium flex items-center gap-1 mt-0.5">
                      <span className="text-blue-500 font-semibold">{insight.campaign_name}</span>
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-3 pb-4 text-xs">
                    <p className="text-muted-foreground leading-relaxed">{insight.description}</p>

                    <div className="p-2.5 rounded-lg bg-muted/40 border text-[11px] font-medium text-foreground">
                      <span className="text-muted-foreground block text-[10px] uppercase font-semibold">Действие:</span>
                      {insight.suggested_action}
                    </div>

                    <Button
                      size="sm"
                      className="w-full bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold flex items-center justify-center gap-1.5"
                      onClick={() => handleApplyInsight(insight)}
                      disabled={applyingInsightId === insight.id}
                    >
                      {applyingInsightId === insight.id ? (
                        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Zap className="h-3.5 w-3.5" />
                      )}
                      {applyingInsightId === insight.id ? 'Применение...' : 'Применить рекомендацию в 1 клик'}
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* 2. Interactive Analytics Tab */}
        <TabsContent value="analytics" className="space-y-6">
          {/* Header with Date Range filter */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-muted/30 p-4 rounded-xl border">
            <div>
              <h3 className="text-base font-bold flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-blue-500" />
                Интерактивная статистика эффективности
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Динамика показов, переходов, расходов и сегментация аудитории в реальном времени
              </p>
            </div>
            <div className="flex items-center gap-1.5 self-start sm:self-auto bg-background p-1 rounded-lg border">
              {[7, 14, 30].map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => {
                    setTimelineDays(d);
                    fetchTimeline(d);
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
                onClick={() => fetchTimeline(timelineDays)}
                title="Обновить данные"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loadingTimeline ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>

          {/* Quick Metrics in Analytics Tab */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card className="bg-gradient-to-br from-blue-50/50 to-transparent dark:from-blue-950/20">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">Показы за период</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-black text-blue-600 dark:text-blue-400">
                  {(timelineData?.total_impressions || 0).toLocaleString()}
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">Охват рекомендаций в чате</p>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-emerald-50/50 to-transparent dark:from-emerald-950/20">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">Клики за период</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
                  {(timelineData?.total_clicks || 0).toLocaleString()}
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">Переходы на ваш сайт</p>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-purple-50/50 to-transparent dark:from-purple-950/20">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">Средний CTR</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-black text-purple-600 dark:text-purple-400">
                  {timelineData?.ctr || 0}%
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">Конверсия показов в клики</p>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-amber-50/50 to-transparent dark:from-amber-950/20">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">Расходы за период</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-black text-amber-600 dark:text-amber-400">
                  ${(timelineData?.total_spend || 0).toFixed(2)}
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">CPC / CPM инвестиции</p>
              </CardContent>
            </Card>
          </div>

          {/* Main Chart Area */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <div>
                <CardTitle className="text-sm font-semibold">График показов и переходов по дням</CardTitle>
                <CardDescription className="text-xs">
                  Динамика вовлеченности аудитории за последние {timelineDays} дней
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-[280px] w-full">
                {timelineData?.timeline && timelineData.timeline.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={timelineData.timeline}
                      margin={{ top: 10, right: 20, left: -10, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient id="impGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                        </linearGradient>
                        <linearGradient id="clkGradient" x1="0" y1="0" x2="0" y2="1">
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
                        name="Показы (Impressions)"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#impGradient)"
                      />
                      <Area
                        type="monotone"
                        dataKey="clicks"
                        name="Клики (Clicks)"
                        stroke="#10b981"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#clkGradient)"
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

          {/* Breakdown Cards: Languages, Models, Devices, Regions */}
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
            {/* Language Breakdown */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-xs font-semibold flex items-center gap-2">
                  <Globe className="h-4 w-4 text-blue-500" />
                  Языки запросов пользователей
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {(() => {
                  const langs = timelineData?.languages || {};
                  const total = Object.values(langs).reduce((a, b) => a + b, 0) || 1;
                  const items = [
                    { code: 'ru', label: '🇷🇺 Русский', count: langs['ru'] || 0, color: 'bg-blue-500' },
                    { code: 'uz', label: '🇺🇿 Oʻzbekcha', count: langs['uz'] || 0, color: 'bg-emerald-500' },
                    { code: 'en', label: '🇬🇧 English', count: langs['en'] || 0, color: 'bg-purple-500' },
                    { code: 'other', label: '🌐 Другие', count: langs['other'] || 0, color: 'bg-zinc-400' },
                  ];
                  return items.map((item) => {
                    const pct = Math.round((item.count / total) * 100);
                    return (
                      <div key={item.code} className="space-y-1">
                        <div className="flex justify-between text-xs font-medium">
                          <span>{item.label}</span>
                          <span className="text-muted-foreground">{item.count} ({pct}%)</span>
                        </div>
                        <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                          <div className={`h-full ${item.color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  });
                })()}
              </CardContent>
            </Card>

            {/* AI Models Breakdown */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-xs font-semibold flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-purple-500" />
                  Используемые модели LLM
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {(() => {
                  const models = timelineData?.models || {};
                  const total = Object.values(models).reduce((a, b) => a + b, 0) || 1;
                  const items = [
                    { code: 'gpt-4o', label: '🤖 GPT-4o / Mini', count: models['gpt-4o'] || 0, color: 'bg-emerald-500' },
                    { code: 'deepseek', label: '⚡ DeepSeek R1 / V3', count: models['deepseek'] || 0, color: 'bg-blue-500' },
                    { code: 'claude', label: '🧠 Claude 3.5 Sonnet', count: models['claude'] || 0, color: 'bg-purple-500' },
                    { code: 'other', label: '🌐 Другие модели', count: models['other'] || 0, color: 'bg-zinc-400' },
                  ];
                  return items.map((item) => {
                    const pct = Math.round((item.count / total) * 100);
                    return (
                      <div key={item.code} className="space-y-1">
                        <div className="flex justify-between text-xs font-medium">
                          <span>{item.label}</span>
                          <span className="text-muted-foreground">{item.count} ({pct}%)</span>
                        </div>
                        <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                          <div className={`h-full ${item.color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  });
                })()}
              </CardContent>
            </Card>

            {/* Devices Breakdown */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-xs font-semibold flex items-center gap-2">
                  <Laptop className="h-4 w-4 text-emerald-500" />
                  Устройства и платформы
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {(() => {
                  const devs = timelineData?.devices || {};
                  const total = Object.values(devs).reduce((a, b) => a + b, 0) || 1;
                  const items = [
                    { code: 'desktop', label: '🖥️ Desktop (ПК)', count: devs['desktop'] || 0, color: 'bg-blue-500' },
                    { code: 'mobile', label: '📱 Mobile (Смартфоны)', count: devs['mobile'] || 0, color: 'bg-emerald-500' },
                    { code: 'tablet', label: '📟 Планшеты', count: devs['tablet'] || 0, color: 'bg-amber-500' },
                  ];
                  return items.map((item) => {
                    const pct = Math.round((item.count / total) * 100);
                    return (
                      <div key={item.code} className="space-y-1">
                        <div className="flex justify-between text-xs font-medium">
                          <span>{item.label}</span>
                          <span className="text-muted-foreground">{item.count} ({pct}%)</span>
                        </div>
                        <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                          <div className={`h-full ${item.color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  });
                })()}
              </CardContent>
            </Card>

            {/* Regional Breakdown */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-xs font-semibold flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-rose-500" />
                  Регионы Узбекистана
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2.5">
                {(() => {
                  const regions = timelineData?.regions || {};
                  const total = Object.values(regions).reduce((a, b) => a + b, 0) || 1;
                  const items = [
                    { code: 'tashkent', label: '📍 Ташкент', count: regions['tashkent'] || 0, color: 'bg-rose-500' },
                    { code: 'samarkand', label: '📍 Самарканд', count: regions['samarkand'] || 0, color: 'bg-blue-500' },
                    { code: 'fergana', label: '📍 Фергана', count: regions['fergana'] || 0, color: 'bg-emerald-500' },
                    { code: 'bukhara', label: '📍 Бухара', count: regions['bukhara'] || 0, color: 'bg-amber-500' },
                    { code: 'andijan', label: '📍 Андижан', count: regions['andijan'] || 0, color: 'bg-indigo-500' },
                    { code: 'other', label: '🌐 Другие регионы', count: (regions['namangan'] || 0) + (regions['other'] || 0), color: 'bg-zinc-400' },
                  ];
                  return items.map((item) => {
                    const pct = Math.round((item.count / total) * 100);
                    return (
                      <div key={item.code} className="space-y-1">
                        <div className="flex justify-between text-xs font-medium">
                          <span>{item.label}</span>
                          <span className="text-muted-foreground">{item.count} ({pct}%)</span>
                        </div>
                        <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                          <div className={`h-full ${item.color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  });
                })()}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* 3. Billing Tab */}
        <TabsContent value="billing" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            {/* Subscription & Auto-Renewal Card */}
            <Card className="md:col-span-1 border-blue-500/30 bg-gradient-to-br from-blue-950/20 via-background to-background">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-blue-500" />
                    Тариф и Автопродление
                  </CardTitle>
                  <Badge
                    variant={subscription?.plan_id === 'pro' ? 'default' : subscription?.plan_id === 'plus' ? 'secondary' : 'outline'}
                    className="uppercase font-bold text-[10px]"
                  >
                    {subscription?.plan_id ? subscription.plan_id.toUpperCase() : 'FREE'}
                  </Badge>
                </div>
                <CardDescription className="text-xs">
                  Управление тарифным планом Swipies AI и привязанными картами
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <div className="p-3 rounded-lg border bg-background/80 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Стоимость:</span>
                    <span className="font-bold text-foreground">
                      ${subscription?.price_usd ? subscription.price_usd.toFixed(2) : '0.00'} / мес
                    </span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Статус подписки:</span>
                    {subscription?.status === 'active' ? (
                      <span className="font-semibold text-emerald-500 flex items-center gap-1">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Активна
                      </span>
                    ) : subscription?.status === 'past_due' ? (
                      <span className="font-semibold text-rose-500 flex items-center gap-1">
                        <AlertCircle className="h-3.5 w-3.5" /> Ошибка оплаты
                      </span>
                    ) : (
                      <span className="font-semibold text-zinc-400">Базовый (Free)</span>
                    )}
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Автопродление:</span>
                    {subscription?.auto_renew ? (
                      <Badge className="bg-emerald-600/20 text-emerald-500 hover:bg-emerald-600/30 border-emerald-500/30 text-[10px]">
                        🟢 Включено (каждые 30 дн.)
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-zinc-400 text-[10px]">
                        ⏸️ Отключено
                      </Badge>
                    )}
                  </div>

                  {subscription?.next_billing_time ? (
                    <div className="flex justify-between items-center pt-1 border-t border-border/40">
                      <span className="text-muted-foreground flex items-center gap-1">
                        <Calendar className="h-3 w-3" /> Следующее списание:
                      </span>
                      <span className="font-medium text-foreground">
                        {new Date(subscription.next_billing_time).toLocaleDateString()}
                      </span>
                    </div>
                  ) : null}

                  {subscription?.card ? (
                    <div className="flex justify-between items-center pt-1 border-t border-border/40">
                      <span className="text-muted-foreground flex items-center gap-1">
                        <CreditCard className="h-3 w-3" /> Основная карта:
                      </span>
                      <span className="font-medium text-foreground">
                        {subscription.card.card_pan_masked}
                      </span>
                    </div>
                  ) : null}
                </div>

                <div className="flex flex-col gap-2 pt-1">
                  {subscription?.plan_id && subscription.plan_id !== 'free' && (
                    <Button
                      size="sm"
                      variant={subscription.auto_renew ? 'outline' : 'default'}
                      className="w-full text-xs"
                      onClick={handleToggleAutoRenew}
                      disabled={loadingSubscriptionAction}
                    >
                      {loadingSubscriptionAction ? (
                        <RefreshCw className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                      ) : subscription.auto_renew ? (
                        <>
                          <Pause className="mr-1.5 h-3.5 w-3.5 text-amber-500" /> Отключить автопродление
                        </>
                      ) : (
                        <>
                          <Play className="mr-1.5 h-3.5 w-3.5 text-emerald-500" /> Возобновить автопродление
                        </>
                      )}
                    </Button>
                  )}

                  <Button
                    size="sm"
                    variant="outline"
                    className="w-full text-xs flex items-center justify-center gap-1.5"
                    onClick={() => setIsCardsModalOpen(true)}
                  >
                    <CreditCard className="h-3.5 w-3.5 text-blue-500" />
                    Сохранённые карты ({savedCards.length})
                  </Button>
                </div>
              </CardContent>
            </Card>

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

            <Card className="md:col-span-1">
              <CardHeader>
                <CardTitle className="text-sm font-semibold">Уведомления и Безопасность</CardTitle>
                <CardDescription className="text-xs">Защищённые транзакции и СМС-оповещения</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2.5 text-xs text-muted-foreground">
                <div className="p-2.5 rounded border bg-muted/20 space-y-1">
                  <div className="font-semibold text-foreground flex items-center gap-1.5">
                    <ShieldCheck className="h-3.5 w-3.5 text-blue-500" /> Безопасная токенизация
                  </div>
                  <p>Все платежи обрабатываются через сертифицированный шлюз Atmos. Данные карт зашифрованы.</p>
                </div>
                <div className="p-2.5 rounded border bg-muted/20 space-y-1">
                  <div className="font-semibold text-foreground flex items-center gap-1.5">
                    <Zap className="h-3.5 w-3.5 text-amber-500" /> Мгновенный перерасчёт
                  </div>
                  <p>При автопродлении все преимущества тарифа (лимиты токенов, отсутствие рекламы) продлеваются без пауз.</p>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4">

            <Card className="md:col-span-2">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Recent Transactions</CardTitle>
                  <CardDescription>Ledger of deposits and advertising spend deductions</CardDescription>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="text-xs flex items-center gap-1.5"
                  onClick={() => window.open('/v1/ads/export/transactions', '_blank')}
                >
                  <Download className="h-3.5 w-3.5" /> Экспорт CSV
                </Button>
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
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold">Ad Copy (Recommended Offer) *</label>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="h-6 text-xs text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-950/40 px-2 flex items-center gap-1 font-semibold"
                  onClick={handleGenerateAICopy}
                  disabled={isGeneratingCopy}
                >
                  <Sparkles className={`h-3.5 w-3.5 ${isGeneratingCopy ? 'animate-spin' : ''}`} />
                  {isGeneratingCopy ? 'Генерация...' : '✨ Сгенерировать с AI'}
                </Button>
              </div>
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

            {/* Negative Keywords */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold">Минус-слова (Negative Keywords)</label>
                <span className="text-[11px] text-muted-foreground">Не показывать рекламу при этих словах</span>
              </div>
              <Input
                placeholder="бесплатно, скачать, взлом, кряк, torrent"
                value={rawNegativeKeywords}
                onChange={(e) => setRawNegativeKeywords(e.target.value)}
              />
            </div>

            {/* Language Targeting */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold">Целевые языки пользователей</label>
                <span className="text-[11px] text-muted-foreground">Язык запроса в чате</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {[
                  { code: 'all', label: '🌐 Все языки' },
                  { code: 'uz', label: "🇺🇿 O'zbekcha" },
                  { code: 'ru', label: '🇷🇺 Русский' },
                  { code: 'en', label: '🇬🇧 English' },
                ].map((item) => {
                  const isSelected = targetLanguages.includes(item.code);
                  return (
                    <Button
                      key={item.code}
                      type="button"
                      variant={isSelected ? 'default' : 'outline'}
                      size="sm"
                      className={`h-8 text-xs font-medium ${isSelected ? 'bg-blue-600 text-white' : ''}`}
                      onClick={() => toggleLanguage(item.code)}
                    >
                      {item.label}
                    </Button>
                  );
                })}
              </div>
            </div>

            {/* Model-Level Targeting */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold">Таргетинг на AI-модели</label>
                <span className="text-[11px] text-muted-foreground">В ответах каких моделей показывать</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {[
                  { code: 'all', label: '🤖 Все модели' },
                  { code: 'deepseek', label: '⚡ DeepSeek (V3/R1)' },
                  { code: 'gpt-4o', label: '🧠 OpenAI (GPT-4o)' },
                  { code: 'claude', label: '💎 Claude (Sonnet 3.5)' },
                  { code: 'qwen', label: '🚀 Qwen & Llama' },
                ].map((item) => {
                  const isSelected = targetModels.includes(item.code);
                  return (
                    <Button
                      key={item.code}
                      type="button"
                      variant={isSelected ? 'default' : 'outline'}
                      size="sm"
                      className={`h-8 text-xs font-medium ${isSelected ? 'bg-purple-600 text-white' : ''}`}
                      onClick={() => toggleModel(item.code)}
                    >
                      {item.label}
                    </Button>
                  );
                })}
              </div>
            </div>

            {/* Geo Regional Targeting */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5 text-rose-500" /> Гео-таргетинг (Регионы Узбекистана)
                </label>
                <span className="text-[11px] text-muted-foreground">Локализация показов по городам и областям</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {[
                  { code: 'all', label: '🇺🇿 Все регионы' },
                  { code: 'tashkent', label: '📍 Ташкент' },
                  { code: 'samarkand', label: '📍 Самарканд' },
                  { code: 'bukhara', label: '📍 Бухара' },
                  { code: 'fergana', label: '📍 Фергана' },
                  { code: 'andijan', label: '📍 Андижан' },
                  { code: 'namangan', label: '📍 Наманган' },
                  { code: 'khorezm', label: '📍 Хорезм' },
                  { code: 'kashkadarya', label: '📍 Кашкадарья' },
                  { code: 'karakalpakstan', label: '📍 Каракалпакстан' },
                  { code: 'global', label: '🌐 Международный' },
                ].map((item) => {
                  const isSelected = targetRegions.includes(item.code);
                  return (
                    <Button
                      key={item.code}
                      type="button"
                      variant={isSelected ? 'default' : 'outline'}
                      size="sm"
                      className={`h-7 text-xs font-medium ${isSelected ? 'bg-rose-600 text-white' : ''}`}
                      onClick={() => toggleRegion(item.code)}
                    >
                      {item.label}
                    </Button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Модель оплаты</label>
                <Select
                  value={campaignForm.pricing_model}
                  onValueChange={(val: any) => setCampaignForm({ ...campaignForm, pricing_model: val })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cpc">CPC (Оплата за клик)</SelectItem>
                    <SelectItem value="cpm">CPM (За 1000 показов)</SelectItem>
                    <SelectItem value="cpa">CPA (За конверсию / лид)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {campaignForm.pricing_model === 'cpa' ? (
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-purple-600 dark:text-purple-400">Target CPA ($)</label>
                  <Input
                    type="number"
                    step="0.5"
                    value={campaignForm.target_cpa || 5.0}
                    onChange={(e) => setCampaignForm({ ...campaignForm, target_cpa: parseFloat(e.target.value) })}
                    placeholder="5.00"
                  />
                </div>
              ) : (
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold">Ставка / Bid ($)</label>
                  <Input
                    type="number"
                    step="0.01"
                    value={campaignForm.bid_amount}
                    onChange={(e) => setCampaignForm({ ...campaignForm, bid_amount: parseFloat(e.target.value) })}
                  />
                </div>
              )}

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

            {campaignForm.pricing_model === 'cpa' && (
              <div className="p-3 bg-purple-500/10 border border-purple-500/20 rounded-lg text-xs text-purple-700 dark:text-purple-300 flex items-start gap-2">
                <Sparkles className="h-4 w-4 shrink-0 mt-0.5 text-purple-500" />
                <div>
                  <span className="font-semibold">⚡ AI Smart Auto-Bidding (Target CPA):</span> Алгоритм автоматически оптимизирует ставку участия в аукционе на основе исторического CR (коэффициента конверсий вашего сайта), чтобы удерживать стоимость целевого действия в рамках указанного Target CPA.
                </div>
              </div>
            )}
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
            <DialogTitle className="flex items-center gap-2 text-base font-bold">
              <CreditCard className="h-5 w-5 text-emerald-600" />
              Пополнение рекламного баланса
            </DialogTitle>
            <DialogDescription className="text-xs">
              Моментальное зачисление средств на баланс рекламодателя через национальные и международные карты.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Быстрый выбор суммы:</label>
              <div className="grid grid-cols-5 gap-2">
                {['20', '50', '100', '250', '500'].map((amt) => (
                  <Button
                    key={amt}
                    type="button"
                    variant={topUpAmount === amt ? 'default' : 'outline'}
                    size="sm"
                    className={`font-bold text-xs h-9 ${topUpAmount === amt ? 'bg-blue-600 text-white' : ''}`}
                    onClick={() => setTopUpAmount(amt)}
                  >
                    ${amt}
                  </Button>
                ))}
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Сумма пополнения ($ USD)</label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type="number"
                  step="5"
                  min="5"
                  value={topUpAmount}
                  onChange={(e) => setTopUpAmount(e.target.value)}
                  className="pl-9 font-mono text-base font-bold h-11"
                  placeholder="50.00"
                />
              </div>
            </div>

            <div className="rounded-xl bg-gradient-to-r from-blue-50/80 to-indigo-50/80 border border-blue-100 p-3.5 space-y-1 dark:from-blue-950/30 dark:to-indigo-950/20 dark:border-blue-900/50">
              <div className="flex justify-between items-center text-xs">
                <span className="text-muted-foreground font-medium">К оплате через Atmos:</span>
                <span className="font-extrabold text-blue-700 dark:text-blue-400 text-base">
                  {(Math.round(parseFloat(topUpAmount || '0') * 12800)).toLocaleString()} UZS
                </span>
              </div>
              <div className="text-[10px] text-muted-foreground flex justify-between items-center pt-1 border-t border-blue-100/60 dark:border-blue-900/40">
                <span>Курс: 1 USD = 12,800 UZS</span>
                <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Комиссия 0%</span>
              </div>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setIsTopUpModalOpen(false)}>
              Отмена
            </Button>
            <Button
              onClick={() => {
                const num = parseFloat(topUpAmount);
                if (isNaN(num) || num <= 0) {
                  message.error('Пожалуйста, укажите корректную сумму пополнения');
                  return;
                }
                setIsTopUpModalOpen(false);
                setIsAtmosModalOpen(true);
              }}
              className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold flex items-center gap-1.5 shadow-md shadow-emerald-500/20"
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
          message.success('Баланс рекламодателя успешно обновлен!');
        }}
      />

      {/* Campaign Analytics Modal */}
      <Dialog open={isAnalyticsModalOpen} onOpenChange={setIsAnalyticsModalOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <BarChart3 className="h-5 w-5 text-blue-500" />
              Аналитика кампании: {selectedCampaign?.name}
            </DialogTitle>
            <DialogDescription className="text-xs">
              Продукт: <span className="font-semibold text-foreground">{selectedCampaign?.product_name}</span> | Статус:{' '}
              <span className="font-semibold uppercase text-emerald-500">{selectedCampaign?.status}</span>
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Quick Metrics */}
            <div className="grid grid-cols-4 gap-2 text-center">
              <div className="rounded-lg border bg-blue-50/50 dark:bg-blue-950/20 p-2.5">
                <div className="text-[11px] text-muted-foreground">Показы</div>
                <div className="text-base font-bold text-blue-600 dark:text-blue-400">
                  {analyticsData?.total_impressions || 0}
                </div>
              </div>
              <div className="rounded-lg border bg-emerald-50/50 dark:bg-emerald-950/20 p-2.5">
                <div className="text-[11px] text-muted-foreground">Клики</div>
                <div className="text-base font-bold text-emerald-600 dark:text-emerald-400">
                  {analyticsData?.total_clicks || 0}
                </div>
              </div>
              <div className="rounded-lg border bg-purple-50/50 dark:bg-purple-950/20 p-2.5">
                <div className="text-[11px] text-muted-foreground">CTR</div>
                <div className="text-base font-bold text-purple-600 dark:text-purple-400">
                  {analyticsData?.ctr || 0}%
                </div>
              </div>
              <div className="rounded-lg border bg-amber-50/50 dark:bg-amber-950/20 p-2.5">
                <div className="text-[11px] text-muted-foreground">Расход</div>
                <div className="text-base font-bold text-amber-600 dark:text-amber-400">
                  ${(analyticsData?.total_spend || analyticsData?.total_spent || 0).toFixed(2)}
                </div>
              </div>
            </div>

            {/* Campaign Daily Timeline Mini Chart */}
            {analyticsData?.timeline && analyticsData.timeline.length > 0 && (
              <div className="rounded-lg border p-3 bg-muted/10 space-y-1">
                <div className="text-xs font-semibold text-muted-foreground mb-1">
                  Динамика за последние 14 дней
                </div>
                <div className="h-44 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={analyticsData.timeline}
                      margin={{ top: 5, right: 10, left: -20, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient id="modalImpGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                        </linearGradient>
                        <linearGradient id="modalClkGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 10 }}
                        tickFormatter={(val) => {
                          const parts = val.split('-');
                          return parts.length === 3 ? `${parts[1]}.${parts[2]}` : val;
                        }}
                      />
                      <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'rgba(17, 24, 39, 0.95)',
                          borderRadius: '6px',
                          border: '1px solid rgba(255, 255, 255, 0.1)',
                          color: '#fff',
                          fontSize: '11px',
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="impressions"
                        name="Показы"
                        stroke="#3b82f6"
                        strokeWidth={1.5}
                        fillOpacity={1}
                        fill="url(#modalImpGradient)"
                      />
                      <Area
                        type="monotone"
                        dataKey="clicks"
                        name="Клики"
                        stroke="#10b981"
                        strokeWidth={1.5}
                        fillOpacity={1}
                        fill="url(#modalClkGradient)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Demographics / Devices info */}
            {analyticsData?.languages && (
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 border rounded-lg bg-muted/20 space-y-1">
                  <div className="font-semibold text-muted-foreground text-[11px] flex items-center gap-1">
                    <Globe className="h-3.5 w-3.5 text-blue-500" /> Языки аудитории
                  </div>
                  <div className="flex flex-wrap gap-1 pt-1">
                    {Object.entries(analyticsData.languages).map(([l, count]: any) => (
                      <span key={l} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-background border font-mono">
                        {l.toUpperCase()}: {count}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="p-2.5 border rounded-lg bg-muted/20 space-y-1">
                  <div className="font-semibold text-muted-foreground text-[11px] flex items-center gap-1">
                    <Laptop className="h-3.5 w-3.5 text-emerald-500" /> Устройства
                  </div>
                  <div className="flex flex-wrap gap-1 pt-1">
                    {Object.entries(analyticsData.devices || {}).map(([d, count]: any) => (
                      <span key={d} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-background border font-mono">
                        {d}: {count}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Recent Matching Query Intents if available */}
            {analyticsData?.recent_impressions && (
              <div>
                <div className="text-xs font-semibold mb-1.5">Недавние поисковые намерения</div>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {analyticsData.recent_impressions.length === 0 ? (
                    <div className="text-xs text-muted-foreground py-1 text-center">Нет записанных показов</div>
                  ) : (
                    analyticsData.recent_impressions.map((imp: any) => (
                      <div key={imp.id} className="rounded border p-1.5 text-xs flex justify-between items-center bg-background/50">
                        <span className="truncate max-w-[340px] italic">"{imp.query_intent}"</span>
                        <span className="text-muted-foreground text-[10px]">
                          {new Date(imp.time).toLocaleTimeString()}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button onClick={() => setIsAnalyticsModalOpen(false)}>Закрыть</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* A/B Testing & Copy Variants Modal */}
      <Dialog open={isVariantsModalOpen} onOpenChange={setIsVariantsModalOpen}>
        <DialogContent className="sm:max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400">
                  <FlaskConical className="h-5 w-5" />
                </div>
                <div>
                  <DialogTitle>A/B Тестирование & Варианты объявлений</DialogTitle>
                  <DialogDescription>
                    Кампания: <span className="font-semibold text-foreground">{variantsCampaign?.name}</span> ({variantsCampaign?.product_name})
                  </DialogDescription>
                </div>
              </div>
              <Badge variant="outline" className="border-purple-500/30 text-purple-600 bg-purple-500/10 flex items-center gap-1">
                <Shuffle className="h-3 w-3" /> Multi-Armed Bandit
              </Badge>
            </div>
          </DialogHeader>

          <div className="space-y-5 py-2">
            {/* Info notice */}
            <div className="p-3 rounded-lg bg-blue-50/70 border border-blue-200 dark:bg-blue-950/30 dark:border-blue-800/50 text-xs text-blue-800 dark:text-blue-200 flex items-start gap-2.5">
              <Zap className="h-4 w-4 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
              <div>
                <strong>Автоматическая CTR-оптимизация:</strong> Движок в реальном времени распределяет 80% показов варианту с наивысшим CTR, а 20% показов направляет на исследование новых вариантов текста.
              </div>
            </div>

            {/* List of existing variants */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold flex items-center gap-1.5">
                  <Layers className="h-4 w-4 text-muted-foreground" /> Варианты в ротации ({variantsList.length})
                </h4>
                <Button size="sm" variant="ghost" onClick={() => variantsCampaign && fetchVariants(variantsCampaign.id)} disabled={loadingVariants} className="h-7 text-xs">
                  <RefreshCw className={`h-3 w-3 mr-1 ${loadingVariants ? 'animate-spin' : ''}`} /> Обновить
                </Button>
              </div>

              {loadingVariants ? (
                <div className="p-6 text-center text-xs text-muted-foreground">Загрузка вариантов...</div>
              ) : variantsList.length === 0 ? (
                <div className="p-4 rounded-lg border border-dashed text-center text-xs text-muted-foreground">
                  У этой кампании пока нет дополнительных вариантов (используется основной текст по умолчанию).
                  Добавьте альтернативные заголовки ниже для запуска A/B теста!
                </div>
              ) : (
                <div className="space-y-2.5">
                  {variantsList.map((v) => {
                    const maxCtr = Math.max(...variantsList.map((x) => x.ctr));
                    const isLeader = variantsList.length > 1 && v.impressions >= 5 && v.ctr === maxCtr && maxCtr > 0;
                    return (
                      <div
                        key={v.id}
                        className={`p-3.5 rounded-lg border transition-all ${
                          !v.is_active
                            ? 'bg-muted/20 border-muted opacity-60'
                            : isLeader
                            ? 'bg-purple-50/40 border-purple-300 dark:bg-purple-950/20 dark:border-purple-800'
                            : 'bg-card border-border'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="space-y-1 flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-sm">{v.name}</span>
                              {isLeader && (
                                <Badge className="bg-amber-500 hover:bg-amber-600 text-white text-[10px] flex items-center gap-1 py-0 h-4">
                                  <Trophy className="h-2.5 w-2.5" /> Топ CTR
                                </Badge>
                              )}
                              <Badge
                                variant="outline"
                                className={`text-[10px] h-4 ${
                                  v.is_active
                                    ? 'border-emerald-500/40 text-emerald-600 bg-emerald-500/10'
                                    : 'border-zinc-400 text-zinc-500 bg-zinc-500/10'
                                }`}
                              >
                                {v.is_active ? 'В ротации' : 'На паузе'}
                              </Badge>
                              <span className="text-[11px] text-muted-foreground">Вес: {v.weight}x</span>
                            </div>
                            <p className="text-xs text-foreground bg-muted/30 p-2 rounded border border-muted/50 whitespace-pre-wrap font-sans">
                              "{v.advertisement_text}"
                            </p>
                            {v.landing_url && (
                              <div className="text-[11px] text-muted-foreground flex items-center gap-1">
                                <span>URL перехода:</span>
                                <a href={v.landing_url} target="_blank" rel="noreferrer" className="text-blue-500 hover:underline truncate max-w-[280px]">
                                  {v.landing_url}
                                </a>
                              </div>
                            )}
                          </div>

                          <div className="flex flex-col items-end gap-2 shrink-0">
                            {/* Metrics pill */}
                            <div className="flex items-center gap-3 bg-muted/50 px-2.5 py-1 rounded text-xs">
                              <div>
                                <span className="text-muted-foreground text-[10px] block">Показы</span>
                                <span className="font-semibold">{v.impressions.toLocaleString()}</span>
                              </div>
                              <div className="h-6 w-px bg-border" />
                              <div>
                                <span className="text-muted-foreground text-[10px] block">Клики</span>
                                <span className="font-semibold text-emerald-600">{v.clicks.toLocaleString()}</span>
                              </div>
                              <div className="h-6 w-px bg-border" />
                              <div>
                                <span className="text-muted-foreground text-[10px] block">CTR</span>
                                <span className="font-bold text-blue-600">{v.ctr}%</span>
                              </div>
                            </div>

                            {/* Actions */}
                            <div className="flex items-center gap-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 px-2 text-xs"
                                onClick={() => handleToggleVariant(v)}
                              >
                                {v.is_active ? (
                                  <span className="flex items-center gap-1 text-amber-600"><Pause className="h-3 w-3" /> Пауза</span>
                                ) : (
                                  <span className="flex items-center gap-1 text-emerald-600"><Play className="h-3 w-3" /> Включить</span>
                                )}
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 px-2 text-xs text-red-500 hover:text-red-600"
                                onClick={() => handleDeleteVariant(v)}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Form: Add New Variant */}
            <div className="p-4 rounded-xl border bg-muted/10 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold flex items-center gap-1.5">
                  <Plus className="h-4 w-4 text-blue-500" /> Добавить вариант объявления
                </h4>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs bg-purple-50 hover:bg-purple-100 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300 border-purple-300"
                  onClick={handleGenerateVariantAI}
                  disabled={isGeneratingVariantCopy}
                >
                  <Sparkles className={`h-3 w-3 mr-1 ${isGeneratingVariantCopy ? 'animate-spin' : ''}`} />
                  {isGeneratingVariantCopy ? 'Генерация...' : '✨ Сгенерировать AI-оффер'}
                </Button>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Название варианта</label>
                  <Input
                    placeholder="Например: Вариант B (Скидка 20%)"
                    value={newVariantName}
                    onChange={(e) => setNewVariantName(e.target.value)}
                    className="h-8 text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Вес трафика (1.0 = 100%)</label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="5.0"
                    value={newVariantWeight}
                    onChange={(e) => setNewVariantWeight(e.target.value)}
                    className="h-8 text-xs"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Текст рекламного объявления (A/B Copy)</label>
                <Textarea
                  placeholder="Введите привлекательный текст оффера..."
                  value={newVariantText}
                  onChange={(e) => setNewVariantText(e.target.value)}
                  rows={2}
                  className="text-xs"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Посадочная страница (Landing URL, опционально)</label>
                <Input
                  placeholder="https://yourbrand.com/promo-b"
                  value={newVariantUrl}
                  onChange={(e) => setNewVariantUrl(e.target.value)}
                  className="h-8 text-xs"
                />
              </div>

              <Button
                onClick={handleCreateVariant}
                disabled={!newVariantText.trim()}
                className="w-full bg-purple-600 hover:bg-purple-700 text-white text-xs h-8"
              >
                <Plus className="h-3.5 w-3.5 mr-1" /> Добавить вариант в A/B ротацию
              </Button>
            </div>
          </div>

          <DialogFooter>
            <Button onClick={() => setIsVariantsModalOpen(false)}>Закрыть</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Saved Cards Modal */}
      <Dialog open={isCardsModalOpen} onOpenChange={setIsCardsModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-blue-500" /> Сохранённые банковские карты
            </DialogTitle>
            <DialogDescription className="text-xs">
              Карты Uzcard, Humo, Visa и Mastercard, сохранённые для автопродления подписки и пополнения баланса.
            </DialogDescription>
          </DialogHeader>

          <div className="py-3 space-y-3">
            {savedCards.length === 0 ? (
              <div className="py-8 text-center text-xs text-muted-foreground border rounded-lg bg-muted/20">
                <CreditCard className="h-8 w-8 mx-auto mb-2 opacity-40" />
                Нет сохранённых карт. При следующей оплате подписки или пополнении кошелька карта сохранится автоматически.
              </div>
            ) : (
              savedCards.map((card) => (
                <div
                  key={card.id}
                  className="flex items-center justify-between p-3 rounded-lg border bg-muted/30 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded bg-blue-500/10 text-blue-500 font-bold uppercase text-[11px]">
                      {card.card_type || 'UZCARD'}
                    </div>
                    <div>
                      <div className="font-semibold text-xs text-foreground flex items-center gap-2">
                        {card.card_pan_masked}
                        {card.is_default && (
                          <Badge variant="outline" className="text-[9px] py-0 px-1 text-blue-500 border-blue-500/30">
                            Основная
                          </Badge>
                        )}
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        Срок действия: {card.card_expiry}
                      </div>
                    </div>
                  </div>

                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 w-8 p-0 text-red-500 hover:text-red-600 hover:bg-red-500/10"
                    onClick={() => handleDeleteCard(card.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))
            )}
          </div>

          <DialogFooter>
            <Button onClick={() => setIsCardsModalOpen(false)}>Готово</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Conversion Pixel & Smart Bidding Modal */}
      <Dialog open={isPixelModalOpen} onOpenChange={setIsPixelModalOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Code2 className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              Пиксель конверсий Swipies & Smart Auto-Bidding
            </DialogTitle>
            <DialogDescription>
              Установите код пикселя на ваш сайт, чтобы отслеживать покупки, лиды и регистрации, а также автоматически обучать алгоритм Smart CPA ставок.
            </DialogDescription>
          </DialogHeader>

          {loadingPixel ? (
            <div className="flex flex-col items-center justify-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin text-purple-500 mb-2" />
              <p className="text-sm text-muted-foreground">Генерация кода пикселя...</p>
            </div>
          ) : pixelData ? (
            <div className="space-y-4">
              {/* Pixel ID Card */}
              <div className="flex items-center justify-between p-3 rounded-lg bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800">
                <div>
                  <div className="text-xs font-semibold text-purple-700 dark:text-purple-300">Ваш Pixel ID</div>
                  <div className="text-sm font-mono font-bold">{pixelData.pixel_id}</div>
                </div>
                <Badge variant="outline" className="bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300">
                  Активен
                </Badge>
              </div>

              {/* Code Snippet Box */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold">HTML-код для вставки перед &lt;/head&gt;</label>
                  <Button size="sm" variant="ghost" onClick={handleCopySnippet} className="h-7 text-xs flex items-center gap-1 text-purple-600">
                    {copiedSnippet ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                    {copiedSnippet ? 'Скопировано' : 'Копировать код'}
                  </Button>
                </div>
                <pre className="p-3 bg-zinc-950 text-zinc-100 text-xs font-mono rounded-lg overflow-x-auto border border-zinc-800">
                  <code>{pixelData.snippet}</code>
                </pre>
              </div>

              {/* Integration Instructions */}
              <div className="space-y-2 p-3 bg-muted/40 rounded-lg text-xs">
                <div className="font-semibold text-foreground">💡 Как вызывать регистрацию конверсии на сайте (JS):</div>
                <pre className="p-2 bg-background border rounded font-mono text-[11px] overflow-x-auto">
                  <code>{pixelData.example_usage}</code>
                </pre>
                <div className="text-muted-foreground text-[11px]">
                  Поддерживаемые события: <code className="bg-muted px-1 rounded">purchase</code>, <code className="bg-muted px-1 rounded">lead</code>, <code className="bg-muted px-1 rounded">signup</code>, <code className="bg-muted px-1 rounded">add_to_cart</code>.
                </div>
              </div>

              {/* Live Test Event Simulation */}
              <div className="border-t pt-3 space-y-2">
                <div className="text-xs font-semibold flex items-center gap-1.5">
                  <Zap className="h-3.5 w-3.5 text-amber-500" /> Проверить интеграцию (Отправить тестовую конверсию)
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-32">
                    <Input
                      type="number"
                      placeholder="Сумма ($)"
                      value={testOrderValue}
                      onChange={(e) => setTestOrderValue(e.target.value)}
                      className="h-8 text-xs"
                    />
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 text-xs bg-purple-50 text-purple-700 dark:bg-purple-950 dark:text-purple-300 border-purple-300"
                    onClick={handleTestPixelEvent}
                    disabled={isSendingTestEvent}
                  >
                    {isSendingTestEvent ? 'Отправка...' : '⚡ Отправить тестовое событие'}
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-red-500 py-4 text-center">Не удалось загрузить данные пикселя.</p>
          )}

          <DialogFooter>
            <Button onClick={() => setIsPixelModalOpen(false)}>Закрыть</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
