import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertCircle,
  BarChart3,
  Bot,
  Building2,
  CheckCircle2,
  Cpu,
  Database,
  Edit3,
  Eye,
  EyeOff,
  Globe,
  Key,
  Layers,
  Lock,
  Mic,
  Plus,
  RefreshCw,
  Save,
  Server,
  Shield,
  Sparkles,
  Trash2,
  Users,
  Volume2,
  Zap,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import message from '@/components/ui/message';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

import {
  AIAuditLogItem,
  AIModelItem,
  AIProviderItem,
  AdminAnalyticsData,
  DynamicProviderModelItem,
  GlobalInstanceStats,
  SubscriptionAIPolicyItem,
  SubscriptionPlanItem,
  UserPolicyOverrideDetail,
  UserPolicyOverrideSummaryItem,
  deleteAdminModel,
  deleteAdminProvider,
  deleteAdminUserPolicy,
  getAdminAnalytics,
  getAdminAuditLogs,
  getAdminAvailableProviders,
  getAdminByokStats,
  getAdminInstance,
  getAdminModels,
  getAdminPlans,
  getAdminPolicies,
  getAdminProviderModelsDynamic,
  getAdminProviders,
  getAdminUserPolicy,
  getAdminUserPolicyOverrides,
  replaceAdminProviderKey,
  saveAdminModel,
  saveAdminProvider,
  setAdminUserPolicy,
  testAdminProviderConnection,
  toggleGlobalModel,
  toggleModelExclusion,
  updateAdminInstance,
  updateAdminPlan,
  updateAdminPolicies,
  verifyAdminProvider,
  verifyAdminProviderLive,
  wipeAdminProviderKey,
} from '@/services/ai-management-service';

export const POLICY_ERROR_EXPLANATIONS: Record<string, { title: string; desc: string; badgeColor: string; level: string }> = {
  PROVIDER_EXCLUDED: {
    level: 'Level 1',
    title: 'Provider Model Excluded',
    desc: 'Model was specifically excluded by admin in provider settings (extra.excluded_models).',
    badgeColor: 'bg-amber-500/15 text-amber-500 border-amber-500/30',
  },
  GLOBALLY_DISABLED: {
    level: 'Level 2',
    title: 'Globally Disabled / Unconfigured',
    desc: 'Model is disabled globally by Kill-Switch, or provider API key is missing/unconfigured.',
    badgeColor: 'bg-rose-500/15 text-rose-500 border-rose-500/30',
  },
  USER_RESTRICTED: {
    level: 'Level 3',
    title: 'User Restricted (Explicit DENY)',
    desc: 'Admin set an explicit DENY override for this specific user account.',
    badgeColor: 'bg-orange-500/15 text-orange-500 border-orange-500/30',
  },
  PLAN_RESTRICTED: {
    level: 'Level 4',
    title: 'Subscription Plan Restricted',
    desc: 'Model is not authorized under the user’s subscription tier (Free / Plus / Pro).',
    badgeColor: 'bg-blue-500/15 text-blue-500 border-blue-500/30',
  },
  QUOTA_EXCEEDED: {
    level: 'Level 5',
    title: 'Token Quota Reached',
    desc: 'User or Plan monthly/daily token quota has been 100% exhausted.',
    badgeColor: 'bg-purple-500/15 text-purple-500 border-purple-500/30',
  },
};

const PROVIDER_PRESETS = [
  { name: 'OpenAI', baseUrl: 'https://api.openai.com/v1', suggestedModel: 'gpt-4o' },
  { name: 'Anthropic', baseUrl: 'https://api.anthropic.com/v1', suggestedModel: 'claude-3-5-sonnet-20241022' },
  { name: 'DeepSeek', baseUrl: 'https://api.deepseek.com/v1', suggestedModel: 'deepseek-chat' },
  { name: 'Google', baseUrl: 'https://generativelanguage.googleapis.com', suggestedModel: 'gemini-1.5-pro' },
  { name: 'OpenAI-Compatible', baseUrl: 'http://localhost:8000/v1', suggestedModel: 'custom-model' },
  { name: 'Ollama', baseUrl: 'http://localhost:11434/v1', suggestedModel: 'llama3:latest' },
];

export default function AIManagementPage() {
  const [activeTab, setActiveTab] = useState('instance');
  const [loading, setLoading] = useState(false);

  // Data states
  const [instanceStats, setInstanceStats] = useState<GlobalInstanceStats | null>(null);
  const [providers, setProviders] = useState<AIProviderItem[]>([]);
  const [models, setModels] = useState<AIModelItem[]>([]);
  const [plans, setPlans] = useState<SubscriptionPlanItem[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string>('plus');
  const [policies, setPolicies] = useState<SubscriptionAIPolicyItem[]>([]);
  const [analytics, setAnalytics] = useState<AdminAnalyticsData | null>(null);
  const [auditLogs, setAuditLogs] = useState<AIAuditLogItem[]>([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [byokStats, setByokStats] = useState<{ total_byok_models: number; active_byok_models: number; locked_byok_models: number; byok_users_count: number } | null>(null);
  const [availableProviders, setAvailableProviders] = useState<{ name: string; model_types: string[]; url: Record<string, string> }[]>([]);

  // Modals
  const [isProviderModalOpen, setIsProviderModalOpen] = useState(false);
  const [verifyingProvider, setVerifyingProvider] = useState(false);
  const [verifyResult, setVerifyResult] = useState<{ success: boolean; message: string; available_models: any[]; count: number } | null>(null);
  const [editingProvider, setEditingProvider] = useState<Partial<AIProviderItem> & { api_key?: string }>({
    provider_name: 'OpenAI',
    base_url: 'https://api.openai.com/v1',
    api_key: '',
    organization: '',
    status: 'active',
  });

  // Provider Action State
  const [testingProviderName, setTestingProviderName] = useState<string | null>(null);
  const [liveVerifyingProviderName, setLiveVerifyingProviderName] = useState<string | null>(null);
  const [wipingProviderName, setWipingProviderName] = useState<string | null>(null);

  // Replace Key Modal
  const [isReplaceKeyModalOpen, setIsReplaceKeyModalOpen] = useState(false);
  const [replaceTargetProvider, setReplaceTargetProvider] = useState<AIProviderItem | null>(null);
  const [newApiKeyInput, setNewApiKeyInput] = useState('');
  const [newBaseUrlInput, setNewBaseUrlInput] = useState('');
  const [showReplaceKey, setShowReplaceKey] = useState(false);
  const [replacingKey, setReplacingKey] = useState(false);

  // Models Sub-Tab & Dynamic Discovery State
  const [modelsSubTab, setModelsSubTab] = useState<'configured' | 'dynamic'>('configured');
  const [selectedDiscoveryProvider, setSelectedDiscoveryProvider] = useState<string>('OpenAI');
  const [dynamicModels, setDynamicModels] = useState<DynamicProviderModelItem[]>([]);
  const [loadingDynamicModels, setLoadingDynamicModels] = useState<boolean>(false);
  const [togglingGlobalModelId, setTogglingGlobalModelId] = useState<string | null>(null);
  const [togglingExclusionKey, setTogglingExclusionKey] = useState<string | null>(null);

  const [isModelModalOpen, setIsModelModalOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<Partial<AIModelItem> & { allowed_plans?: string[] }>({
    provider: 'OpenAI',
    model_name: '',
    model_type: 'CHAT',
    base_url: 'https://api.openai.com/v1',
    api_key: '',
    input_token_price: 0.15,
    output_token_price: 0.60,
    max_tokens: 8192,
    enabled: true,
    is_global: true,
    allowed_plans: ['plus', 'pro'],
  });

  const providerOptions = useMemo(() => {
    if (availableProviders && availableProviders.length > 0) {
      return availableProviders.map((p) => ({
        name: p.name,
        baseUrl: p.url?.default || '',
      }));
    }
    return PROVIDER_PRESETS;
  }, [availableProviders]);

  const chatModels = useMemo(() => {
    return models.filter((m) => m.model_type === 'CHAT' || !m.model_type);
  }, [models]);

  const embeddingModels = useMemo(() => {
    return models.filter((m) => m.model_type === 'EMBEDDING');
  }, [models]);

  const rerankModels = useMemo(() => {
    return models.filter((m) => m.model_type === 'RERANK');
  }, [models]);

  const visionModels = useMemo(() => {
    return models.filter((m) => m.model_type === 'IMAGE2TEXT' || m.model_type === 'CHAT');
  }, [models]);

  const asrModels = useMemo(() => {
    return models.filter((m) => m.model_type === 'SPEECH2TEXT');
  }, [models]);

  const ttsModels = useMemo(() => {
    return models.filter((m) => m.model_type === 'TTS' || m.model_type === 'TEXT2SPEECH');
  }, [models]);

  // Subscriptions & Policies Sub-Tab
  const [policySubTab, setPolicySubTab] = useState<'matrix' | 'user_overrides'>('matrix');

  // Per-User Policy & Overrides State (Levels 3 & 5)
  const [userOverridesList, setUserOverridesList] = useState<UserPolicyOverrideSummaryItem[]>([]);
  const [loadingUserOverrides, setLoadingUserOverrides] = useState(false);
  const [userSearchId, setUserSearchId] = useState('');
  const [searchingUserPolicy, setSearchingUserPolicy] = useState(false);
  const [selectedUserDetail, setSelectedUserDetail] = useState<UserPolicyOverrideDetail | null>(null);
  const [userEditedOverrides, setUserEditedOverrides] = useState<Record<string, 'ALLOW' | 'DENY' | 'DEFAULT'>>({});
  const [userEditedTokenLimit, setUserEditedTokenLimit] = useState<number>(0);
  const [userEditedTokenLimitEnabled, setUserEditedTokenLimitEnabled] = useState<boolean>(true);
  const [savingUserPolicy, setSavingUserPolicy] = useState(false);

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchInstanceStats(),
        fetchProviders(),
        fetchAvailableProviders(),
        fetchModels(),
        fetchPlans(),
        fetchPolicies(selectedPlanId),
        fetchUserOverridesList(),
        fetchAnalytics(),
        fetchAuditLogs(),
        fetchByokStats(),
      ]);
    } catch (e: any) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableProviders = async () => {
    try {
      const res = await getAdminAvailableProviders();
      if (res.data?.code === 0 && res.data?.data) {
        setAvailableProviders(res.data.data);
      }
    } catch (e) {
      console.error('fetchAvailableProviders failed', e);
    }
  };

  const fetchInstanceStats = async () => {
    try {
      const res = await getAdminInstance();
      if (res.data?.code === 0 && res.data?.data) {
        setInstanceStats(res.data.data);
      }
    } catch (e) {
      console.error('fetchInstanceStats failed', e);
    }
  };

  const fetchProviders = async () => {
    try {
      const res = await getAdminProviders();
      if (res.data?.code === 0 && res.data?.data) {
        setProviders(res.data.data);
      }
    } catch (e) {
      console.error('fetchProviders failed', e);
    }
  };

  const fetchModels = async () => {
    try {
      const res = await getAdminModels();
      if (res.data?.code === 0 && res.data?.data) {
        setModels(res.data.data);
      }
    } catch (e) {
      console.error('fetchModels failed', e);
    }
  };

  const fetchPlans = async () => {
    try {
      const res = await getAdminPlans();
      if (res.data?.code === 0 && res.data?.data) {
        setPlans(res.data.data);
      }
    } catch (e) {
      console.error('fetchPlans failed', e);
    }
  };

  const fetchPolicies = async (planId: string) => {
    try {
      const res = await getAdminPolicies(planId);
      if (res.data?.code === 0 && res.data?.data) {
        setPolicies(res.data.data);
      }
    } catch (e) {
      console.error('fetchPolicies failed', e);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const res = await getAdminAnalytics();
      if (res.data?.code === 0 && res.data?.data) {
        setAnalytics(res.data.data);
      }
    } catch (e) {
      console.error('fetchAnalytics failed', e);
    }
  };

  const fetchAuditLogs = async () => {
    try {
      const res = await getAdminAuditLogs({ limit: 50, offset: 0 });
      if (res.data?.code === 0 && res.data?.data) {
        setAuditLogs(res.data.data.items || []);
        setAuditTotal(res.data.data.total || 0);
      }
    } catch (e) {
      console.error('fetchAuditLogs failed', e);
    }
  };

  const fetchByokStats = async () => {
    try {
      const res = await getAdminByokStats();
      if (res.data?.code === 0 && res.data?.data) {
        setByokStats(res.data.data);
      }
    } catch (e) {
      console.error('fetchByokStats failed', e);
    }
  };

  // Global Instance Updates
  const handleUpdateGlobalDefaults = async (field: keyof GlobalInstanceStats, value: any) => {
    try {
      const res = await updateAdminInstance({ [field]: value });
      if (res.data?.code === 0) {
        message.success('Global Instance settings updated successfully');
        fetchInstanceStats();
      } else {
        message.error(res.data?.message || 'Failed to update Global Instance');
      }
    } catch (e: any) {
      message.error(e?.message || 'Update error');
    }
  };

  // Helper: Provider Status Badge
  const getProviderStatusBadge = (p: AIProviderItem) => {
    const isConfigured = p.has_api_key || p.is_configured || Boolean(p.api_key_masked || p.masked_api_key);
    if (!isConfigured || p.status === 'unconfigured') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-zinc-500/15 text-zinc-400 border border-zinc-500/30 flex items-center gap-1">
          <span className="size-1.5 rounded-full bg-zinc-400" />
          UNCONFIGURED
        </span>
      );
    }
    if (p.status === 'verified' || p.status === 'active') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/15 text-emerald-500 border border-emerald-500/30 flex items-center gap-1">
          <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
          VERIFIED & ACTIVE
        </span>
      );
    }
    if (p.status === 'unverified') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/15 text-amber-500 border border-amber-500/30 flex items-center gap-1">
          <span className="size-1.5 rounded-full bg-amber-500" />
          REQUIRES LIVE TEST
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/15 text-rose-500 border border-rose-500/30 flex items-center gap-1">
        <span className="size-1.5 rounded-full bg-rose-500" />
        {p.status.toUpperCase()}
      </span>
    );
  };

  // Provider Actions
  const handleTestProviderConnection = async (providerName: string) => {
    setTestingProviderName(providerName);
    try {
      const res = await testAdminProviderConnection(providerName);
      if (res.data?.code === 0 && res.data?.data) {
        const d = res.data.data;
        if (d.success) {
          message.success(`🟢 Connection to ${providerName} healthy! Latency: ${d.latency_ms || 120}ms. Detected ${d.count || 0} models.`);
        } else {
          message.error(`🔴 Connection test failed for ${providerName}: ${d.message || 'Unknown error'}`);
        }
      } else {
        message.error(res.data?.message || `Failed to test ${providerName}`);
      }
    } catch (e: any) {
      message.error(e?.message || `Test request failed for ${providerName}`);
    } finally {
      setTestingProviderName(null);
    }
  };

  const handleLiveVerifyProvider = async (providerName: string) => {
    setLiveVerifyingProviderName(providerName);
    try {
      const res = await verifyAdminProviderLive(providerName);
      if (res.data?.code === 0 && res.data?.data) {
        const d = res.data.data;
        if (d.success || d.verified) {
          message.success(`🟢 Full-Cycle Live Verification passed for ${providerName}! Provider is now VERIFIED & ACTIVE.`);
          fetchProviders();
          fetchModels();
          fetchInstanceStats();
        } else {
          message.error(`🔴 Live verification failed for ${providerName}: ${d.message || d.error || 'Verification error'}`);
        }
      } else {
        message.error(res.data?.message || `Verification failed for ${providerName}`);
      }
    } catch (e: any) {
      message.error(e?.message || `Verification request failed for ${providerName}`);
    } finally {
      setLiveVerifyingProviderName(null);
    }
  };

  const handleWipeProviderKey = async (providerName: string) => {
    if (
      !confirm(
        `⚠️ Warning: Wiping the API key for ${providerName} will immediately trigger a Wipe Cascade: all models for this provider will be disabled and marked unconfigured_provider. Are you sure you want to proceed?`
      )
    ) {
      return;
    }
    setWipingProviderName(providerName);
    try {
      const res = await wipeAdminProviderKey(providerName);
      if (res.data?.code === 0) {
        const disabledCount = res.data?.data?.models_disabled_count ?? res.data?.data?.cascaded_models_count ?? 0;
        message.success(`🗑️ API Key wiped for ${providerName}. Wipe Cascade disabled ${disabledCount} models.`);
        fetchProviders();
        fetchModels();
        fetchInstanceStats();
      } else {
        message.error(res.data?.message || `Failed to wipe ${providerName} key`);
      }
    } catch (e: any) {
      message.error(e?.message || `Wipe error for ${providerName}`);
    } finally {
      setWipingProviderName(null);
    }
  };

  const handleOpenReplaceKeyModal = (p: AIProviderItem) => {
    setReplaceTargetProvider(p);
    setNewApiKeyInput('');
    setNewBaseUrlInput(p.base_url || '');
    setShowReplaceKey(false);
    setIsReplaceKeyModalOpen(true);
  };

  const handleExecuteReplaceKey = async () => {
    if (!replaceTargetProvider) return;
    if (!newApiKeyInput.trim()) {
      message.error('Please enter a new API Key');
      return;
    }
    setReplacingKey(true);
    try {
      const res = await replaceAdminProviderKey(
        replaceTargetProvider.provider_name,
        newApiKeyInput.trim(),
        newBaseUrlInput.trim() || undefined
      );
      if (res.data?.code === 0) {
        message.success(
          `🔑 API Key updated for ${replaceTargetProvider.provider_name}! Provider and cascaded models auto-reactivated.`
        );
        setIsReplaceKeyModalOpen(false);
        fetchProviders();
        fetchModels();
        fetchInstanceStats();
      } else {
        message.error(res.data?.message || 'Failed to replace API key');
      }
    } catch (e: any) {
      message.error(e?.message || 'Replace key error');
    } finally {
      setReplacingKey(false);
    }
  };

  const handleOpenAddProvider = () => {
    setEditingProvider({
      provider_name: 'OpenAI',
      base_url: 'https://api.openai.com/v1',
      api_key: '',
      organization: '',
      status: 'active',
    });
    setVerifyResult(null);
    setVerifyingProvider(false);
    setIsProviderModalOpen(true);
  };

  const handleOpenEditProvider = (p: AIProviderItem) => {
    setEditingProvider({
      id: p.id,
      provider_name: p.provider_name,
      base_url: p.base_url || '',
      organization: p.organization || '',
      status: p.status,
      api_key: '', // Left blank unless updated
    });
    setVerifyResult(null);
    setVerifyingProvider(false);
    setIsProviderModalOpen(true);
  };

  const handleVerifyProvider = async () => {
    if (!editingProvider.provider_name) {
      message.error('Provider name is required');
      return;
    }
    if (!editingProvider.api_key && !editingProvider.id) {
      message.error('API Key is required to verify connection');
      return;
    }
    setVerifyingProvider(true);
    setVerifyResult(null);
    try {
      const res = await verifyAdminProvider({
        provider_name: editingProvider.provider_name,
        api_key: editingProvider.api_key,
        base_url: editingProvider.base_url,
      });
      if (res.data?.code === 0 && res.data?.data) {
        setVerifyResult(res.data.data);
        if (res.data.data.success) {
          message.success(`Verified successfully! ${res.data.data.count} models detected.`);
          if (res.data.data.available_models) {
            setEditingProvider((prev) => ({
              ...prev,
              available_models: res.data.data.available_models,
            }));
          }
        } else {
          message.error(res.data.data.message || 'Connection verification failed');
        }
      } else {
        message.error(res.data?.message || 'Verification failed');
      }
    } catch (e: any) {
      message.error(e?.message || 'Verification request failed');
    } finally {
      setVerifyingProvider(false);
    }
  };

  const handleSaveProvider = async () => {
    if (!editingProvider.provider_name) {
      message.error('Provider name is required');
      return;
    }
    try {
      const res = await saveAdminProvider(editingProvider);
      if (res.data?.code === 0) {
        message.success(`Provider '${editingProvider.provider_name}' saved and models synchronized!`);
        setIsProviderModalOpen(false);
        fetchProviders();
        fetchModels();
        fetchPolicies(selectedPlanId);
        fetchInstanceStats();
      } else {
        message.error(res.data?.message || 'Failed to save provider');
      }
    } catch (e: any) {
      message.error(e?.message || 'Save error');
    }
  };

  const handleDeleteProvider = async (providerId: string) => {
    if (!confirm('Are you sure you want to delete this provider?')) return;
    try {
      const res = await deleteAdminProvider(providerId);
      if (res.data?.code === 0) {
        message.success('Provider deleted');
        fetchProviders();
        fetchInstanceStats();
      } else {
        message.error(res.data?.message || 'Delete failed');
      }
    } catch (e: any) {
      message.error(e?.message || 'Delete error');
    }
  };

  // Model Actions & Governance
  const handleToggleGlobalModel = async (modelId: string, currentEnabled: boolean) => {
    setTogglingGlobalModelId(modelId);
    try {
      const res = await toggleGlobalModel(modelId, !currentEnabled);
      if (res.data?.code === 0) {
        message.success(
          !currentEnabled
            ? `🟢 Model ${modelId} activated globally.`
            : `🔴 Kill-Switch engaged: Model ${modelId} disabled globally (Level 2).`
        );
        fetchModels();
        fetchInstanceStats();
      } else {
        message.error(res.data?.message || 'Failed to toggle model state');
      }
    } catch (e: any) {
      message.error(e?.message || 'Toggle error');
    } finally {
      setTogglingGlobalModelId(null);
    }
  };

  const handleFetchDynamicModels = async (providerName: string) => {
    if (!providerName) return;
    setLoadingDynamicModels(true);
    try {
      const res = await getAdminProviderModelsDynamic(providerName);
      if (res.data?.code === 0 && res.data?.data) {
        setDynamicModels(res.data.data);
        message.success(`Discovered ${res.data.data.length} live models from ${providerName}`);
      } else {
        message.error(res.data?.message || `Failed to discover models from ${providerName}`);
      }
    } catch (e: any) {
      message.error(e?.message || 'Discovery error');
    } finally {
      setLoadingDynamicModels(false);
    }
  };

  const handleToggleModelExclusion = async (provider: string, modelName: string, currentlyExcluded: boolean) => {
    const key = `${provider}_${modelName}`;
    setTogglingExclusionKey(key);
    try {
      const res = await toggleModelExclusion(provider, modelName, !currentlyExcluded);
      if (res.data?.code === 0) {
        message.success(
          !currentlyExcluded
            ? `🟡 Model '${modelName}' is now EXCLUDED from ${provider} (Level 1 Exclusion).`
            : `🟢 Model '${modelName}' is now RESTORED in ${provider}.`
        );
        handleFetchDynamicModels(provider);
        fetchProviders();
        fetchModels();
      } else {
        message.error(res.data?.message || 'Exclusion toggle failed');
      }
    } catch (e: any) {
      message.error(e?.message || 'Exclusion toggle error');
    } finally {
      setTogglingExclusionKey(null);
    }
  };

  const handleOpenAddModel = () => {
    setEditingModel({
      provider: providers[0]?.provider_name || 'OpenAI',
      model_name: '',
      model_type: 'CHAT',
      base_url: 'https://api.openai.com/v1',
      api_key: '',
      input_token_price: 0.15,
      output_token_price: 0.60,
      max_tokens: 8192,
      enabled: true,
      is_global: true,
      allowed_plans: ['plus', 'pro'],
    });
    setShowApiKey(false);
    setIsModelModalOpen(true);
  };

  const handleOpenEditModel = (m: AIModelItem) => {
    setEditingModel({
      ...m,
      api_key: '',
    });
    setShowApiKey(false);
    setIsModelModalOpen(true);
  };

  const handleSaveModel = async () => {
    if (!editingModel.model_name || !editingModel.provider) {
      message.error('Model name and Provider are required');
      return;
    }
    try {
      const res = await saveAdminModel(editingModel);
      if (res.data?.code === 0) {
        message.success('Model saved successfully');
        setIsModelModalOpen(false);
        fetchModels();
        fetchPolicies(selectedPlanId);
        fetchInstanceStats();
      } else {
        message.error(res.data?.message || 'Failed to save model');
      }
    } catch (e: any) {
      message.error(e?.message || 'Save error');
    }
  };

  const handleDeleteModel = async (modelId: string) => {
    if (!confirm(`Are you sure you want to delete model ${modelId}?`)) return;
    try {
      const res = await deleteAdminModel(modelId);
      if (res.data?.code === 0) {
        message.success('Model deleted');
        fetchModels();
        fetchPolicies(selectedPlanId);
        fetchInstanceStats();
      } else {
        message.error(res.data?.message || 'Delete failed');
      }
    } catch (e: any) {
      message.error(e?.message || 'Delete error');
    }
  };

  // Plan Updates
  const handleUpdatePlanField = async (planId: string, field: keyof SubscriptionPlanItem, val: any) => {
    try {
      const res = await updateAdminPlan(planId, { [field]: val });
      if (res.data?.code === 0) {
        message.success('Plan limit updated');
        fetchPlans();
      } else {
        message.error(res.data?.message || 'Update failed');
      }
    } catch (e: any) {
      message.error(e?.message || 'Update error');
    }
  };

  // Policy Matrix Updates
  const handleTogglePolicyAccess = async (planId: string, modelId: string, enabled: boolean) => {
    try {
      const existing = policies.find((p) => p.model_id === modelId) || {
        id: `${planId}_${modelId}`,
        plan_id: planId,
        model_id: modelId,
        model_token_limit: 0,
        is_default_llm: false,
        is_default_embd: false,
        enabled: false,
      };

      const updatedPolicy = { ...existing, enabled };
      const res = await updateAdminPolicies(planId, [updatedPolicy]);
      if (res.data?.code === 0) {
        message.success(`Access updated for ${modelId}`);
        fetchPolicies(planId);
      } else {
        message.error(res.data?.message || 'Policy update failed');
      }
    } catch (e: any) {
      message.error(e?.message || 'Policy update error');
    }
  };

  const handleUpdatePolicyLimit = async (planId: string, modelId: string, limit: number) => {
    try {
      const existing = policies.find((p) => p.model_id === modelId) || {
        id: `${planId}_${modelId}`,
        plan_id: planId,
        model_id: modelId,
        model_token_limit: 0,
        is_default_llm: false,
        is_default_embd: false,
        enabled: true,
      };

      const updatedPolicy = { ...existing, model_token_limit: limit };
      const res = await updateAdminPolicies(planId, [updatedPolicy]);
      if (res.data?.code === 0) {
        message.success(`Token limit updated for ${modelId}`);
        fetchPolicies(planId);
      } else {
        message.error(res.data?.message || 'Update failed');
      }
    } catch (e: any) {
      message.error(e?.message || 'Update error');
    }
  };

  // Per-User Policy Overrides Handlers (Levels 3 & 5)
  const fetchUserOverridesList = async () => {
    setLoadingUserOverrides(true);
    try {
      const res = await getAdminUserPolicyOverrides();
      if (res.data?.code === 0 && res.data?.data) {
        setUserOverridesList(res.data.data);
      }
    } catch (e) {
      console.error('fetchUserOverridesList failed', e);
    } finally {
      setLoadingUserOverrides(false);
    }
  };

  const handleSelectUserForPolicy = async (userId: string) => {
    if (!userId.trim()) return;
    setSearchingUserPolicy(true);
    try {
      const res = await getAdminUserPolicy(userId.trim());
      if (res.data?.code === 0 && res.data?.data) {
        const u = res.data.data;
        setSelectedUserDetail(u);
        setUserSearchId(u.user_id);
        setUserEditedTokenLimit(u.monthly_token_limit || 0);
        setUserEditedTokenLimitEnabled(u.token_limit_enabled ?? true);

        // Map existing overrides for easy toggle
        const overridesMap: Record<string, 'ALLOW' | 'DENY' | 'DEFAULT'> = {};
        models.forEach((m) => {
          if (
            u.allowed_models_override?.includes(m.model_name) ||
            u.model_overrides?.[m.model_name] === 'ALLOW'
          ) {
            overridesMap[m.model_name] = 'ALLOW';
          } else if (
            u.forbidden_models?.includes(m.model_name) ||
            u.model_overrides?.[m.model_name] === 'DENY'
          ) {
            overridesMap[m.model_name] = 'DENY';
          } else {
            overridesMap[m.model_name] = 'DEFAULT';
          }
        });
        setUserEditedOverrides(overridesMap);
        message.success(`Loaded policy profile for ${u.nickname || u.email || u.user_id}`);
      } else {
        message.error(res.data?.message || `User '${userId}' not found`);
      }
    } catch (e: any) {
      message.error(e?.message || 'Error fetching user policy');
    } finally {
      setSearchingUserPolicy(false);
    }
  };

  const handleSaveUserPolicy = async () => {
    if (!selectedUserDetail) return;
    setSavingUserPolicy(true);
    try {
      const allowed: string[] = [];
      const forbidden: string[] = [];
      const overridesObj: Record<string, string> = {};

      Object.entries(userEditedOverrides).forEach(([modelName, state]) => {
        if (state === 'ALLOW') {
          allowed.push(modelName);
          overridesObj[modelName] = 'ALLOW';
        } else if (state === 'DENY') {
          forbidden.push(modelName);
          overridesObj[modelName] = 'DENY';
        }
      });

      const payload = {
        allowed_models_override: allowed,
        forbidden_models: forbidden,
        model_overrides: overridesObj,
        monthly_token_limit: userEditedTokenLimit,
        token_limit_enabled: userEditedTokenLimitEnabled,
      };

      const res = await setAdminUserPolicy(selectedUserDetail.user_id, payload);
      if (res.data?.code === 0) {
        message.success(
          `✅ Saved Level 3 & Level 5 policy overrides for ${
            selectedUserDetail.email || selectedUserDetail.user_id
          }`
        );
        fetchUserOverridesList();
        handleSelectUserForPolicy(selectedUserDetail.user_id);
      } else {
        message.error(res.data?.message || 'Failed to save user policy');
      }
    } catch (e: any) {
      message.error(e?.message || 'Error saving user policy');
    } finally {
      setSavingUserPolicy(false);
    }
  };

  const handleResetUserPolicy = async (userId: string) => {
    if (
      !confirm(
        `Reset all custom overrides (Level 3 DENY/ALLOW and Level 5 token limit) for this user to default Plan tier?`
      )
    ) {
      return;
    }
    try {
      const res = await deleteAdminUserPolicy(userId);
      if (res.data?.code === 0) {
        message.success('User overrides reset to plan defaults');
        fetchUserOverridesList();
        if (selectedUserDetail?.user_id === userId) {
          handleSelectUserForPolicy(userId);
        }
      } else {
        message.error(res.data?.message || 'Reset failed');
      }
    } catch (e: any) {
      message.error(e?.message || 'Reset error');
    }
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto pr-2 space-y-6">
      {/* Header Banner: Single Global Instance Status */}
      <div className="rounded-xl border border-border-button bg-bg-card p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-accent-primary/10 text-accent-primary border border-accent-primary/20">
              <Server className="size-8" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-text-primary">
                  {instanceStats?.name || 'Global RAGFlow Instance'}
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-500 border border-emerald-500/30">
                  {instanceStats?.status || 'ACTIVE'}
                </span>
                <span className="px-2 py-0.5 rounded text-xs font-mono bg-bg-base text-text-secondary border border-border-button">
                  ID: {instanceStats?.instance_id || 'GLOBAL'}
                </span>
              </div>
              <p className="text-xs text-text-secondary mt-1">
                Single centralized AI infrastructure for all FREE, PLUS, and PRO platform requests.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={fetchInitialData} disabled={loading}>
              <RefreshCw className={`size-4 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Metric Quick Badges */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 pt-4 border-t border-border-button">
          <div className="p-3 rounded-lg bg-bg-base border border-border-button/60">
            <div className="text-xs text-text-secondary flex items-center gap-1.5">
              <Users className="size-3.5 text-blue-500" /> Platform Users
            </div>
            <div className="text-lg font-bold text-text-primary mt-1">
              {(instanceStats?.total_users || 0).toLocaleString()}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-bg-base border border-border-button/60">
            <div className="text-xs text-text-secondary flex items-center gap-1.5">
              <Cpu className="size-3.5 text-purple-500" /> Platform Models
            </div>
            <div className="text-lg font-bold text-text-primary mt-1">
              {instanceStats?.total_models || 0}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-bg-base border border-border-button/60">
            <div className="text-xs text-text-secondary flex items-center gap-1.5">
              <Building2 className="size-3.5 text-amber-500" /> AI Providers
            </div>
            <div className="text-lg font-bold text-text-primary mt-1">
              {instanceStats?.total_providers || 0}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-bg-base border border-border-button/60">
            <div className="text-xs text-text-secondary flex items-center gap-1.5">
              <Key className="size-3.5 text-emerald-500" /> PRO BYOK Connections
            </div>
            <div className="text-lg font-bold text-text-primary mt-1">
              {instanceStats?.byok_connections || 0}
            </div>
          </div>
        </div>
      </div>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid grid-cols-6 w-full max-w-4xl bg-bg-card border border-border-button p-1 rounded-lg">
          <TabsTrigger value="instance" className="text-xs">
            <Server className="size-3.5 mr-1.5" /> Instance & Providers
          </TabsTrigger>
          <TabsTrigger value="models" className="text-xs">
            <Cpu className="size-3.5 mr-1.5" /> Models & Pricing
          </TabsTrigger>
          <TabsTrigger value="subscriptions" className="text-xs">
            <Layers className="size-3.5 mr-1.5" /> Subscriptions & Policies
          </TabsTrigger>
          <TabsTrigger value="byok" className="text-xs">
            <Key className="size-3.5 mr-1.5" /> PRO BYOK
          </TabsTrigger>
          <TabsTrigger value="analytics" className="text-xs">
            <BarChart3 className="size-3.5 mr-1.5" /> Analytics & Cost
          </TabsTrigger>
          <TabsTrigger value="audit" className="text-xs">
            <Shield className="size-3.5 mr-1.5" /> Audit Logs
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: Global Instance & Providers */}
        <TabsContent value="instance" className="space-y-5 pt-2">
          {/* Global Defaults Card */}
          <Card className="bg-bg-card border-border-button">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base font-semibold flex items-center gap-2">
                    <Globe className="size-4 text-accent-primary" /> Default System AI Models
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Centralized system defaults for Chat, Embeddings, Reranking, Vision, and Subscription Tiers. Applied across all user chats, knowledgebases, and assistants.
                  </CardDescription>
                </div>
                <Button size="sm" variant="outline" onClick={fetchInstanceStats}>
                  <RefreshCw className="size-3.5 mr-1" /> Reload Defaults
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Primary System Capabilities (Chat, Embedding, Rerank, Vision, Audio/ASR, TTS) */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 p-3.5 rounded-lg bg-bg-base/60 border border-border-button/60">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-text-primary flex items-center gap-1.5">
                    <Bot className="size-3.5 text-blue-500" /> Default Chat Model
                  </label>
                  <Select
                    value={instanceStats?.default_chat_model || instanceStats?.default_free_model_id || ''}
                    onValueChange={(val) => handleUpdateGlobalDefaults('default_chat_model', val)}
                  >
                    <SelectTrigger className="bg-bg-card border-border-button text-xs">
                      <SelectValue placeholder={chatModels.length > 0 ? "Select Default Chat Model" : "No active API models (add provider key)"} />
                    </SelectTrigger>
                    <SelectContent className="max-h-60 overflow-y-auto">
                      {chatModels.length === 0 ? (
                        <div className="p-2 text-xs text-text-secondary text-center">No chat models connected via API key</div>
                      ) : (
                        chatModels.map((m) => (
                          <SelectItem key={m.id} value={m.id}>
                            {m.model_name} ({m.provider})
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-text-primary flex items-center gap-1.5">
                    <Database className="size-3.5 text-purple-500" /> Default Embedding Model
                  </label>
                  <Select
                    value={instanceStats?.default_embd_id || ''}
                    onValueChange={(val) => handleUpdateGlobalDefaults('default_embd_id', val)}
                  >
                    <SelectTrigger className="bg-bg-card border-border-button text-xs">
                      <SelectValue placeholder={embeddingModels.length > 0 ? "Select Embedding Model" : "No active API models (add provider key)"} />
                    </SelectTrigger>
                    <SelectContent className="max-h-60 overflow-y-auto">
                      {embeddingModels.length === 0 ? (
                        <div className="p-2 text-xs text-text-secondary text-center">No embedding models connected via API key</div>
                      ) : (
                        embeddingModels.map((m) => (
                          <SelectItem key={m.id} value={m.id}>
                            {m.model_name} ({m.provider})
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-text-primary flex items-center gap-1.5">
                    <Layers className="size-3.5 text-amber-500" /> Default Rerank Model
                  </label>
                  <Select
                    value={instanceStats?.default_rerank_id || ''}
                    onValueChange={(val) => handleUpdateGlobalDefaults('default_rerank_id', val)}
                  >
                    <SelectTrigger className="bg-bg-card border-border-button text-xs">
                      <SelectValue placeholder={rerankModels.length > 0 ? "Select Rerank Model" : "Optional / None"} />
                    </SelectTrigger>
                    <SelectContent className="max-h-60 overflow-y-auto">
                      {rerankModels.length === 0 ? (
                        <div className="p-2 text-xs text-text-secondary text-center">No rerank models connected via API key</div>
                      ) : (
                        rerankModels.map((m) => (
                          <SelectItem key={m.id} value={m.id}>
                            {m.model_name} ({m.provider})
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-text-primary flex items-center gap-1.5">
                    <Sparkles className="size-3.5 text-emerald-500" /> Default Vision / Multimodal
                  </label>
                  <Select
                    value={instanceStats?.default_image2text_model || ''}
                    onValueChange={(val) => handleUpdateGlobalDefaults('default_image2text_model', val)}
                  >
                    <SelectTrigger className="bg-bg-card border-border-button text-xs">
                      <SelectValue placeholder={visionModels.length > 0 ? "Select Vision Model" : "Optional / None"} />
                    </SelectTrigger>
                    <SelectContent className="max-h-60 overflow-y-auto">
                      {visionModels.length === 0 ? (
                        <div className="p-2 text-xs text-text-secondary text-center">No vision models connected via API key</div>
                      ) : (
                        visionModels.map((m) => (
                          <SelectItem key={m.id} value={m.id}>
                            {m.model_name} ({m.provider})
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-text-primary flex items-center gap-1.5">
                    <Mic className="size-3.5 text-rose-500" /> Default Audio / Speech2Text (STT / ASR)
                  </label>
                  <Select
                    value={instanceStats?.default_asr_model || ''}
                    onValueChange={(val) => handleUpdateGlobalDefaults('default_asr_model', val)}
                  >
                    <SelectTrigger className="bg-bg-card border-border-button text-xs">
                      <SelectValue placeholder={asrModels.length > 0 ? "Select Speech2Text Model" : "Optional / None"} />
                    </SelectTrigger>
                    <SelectContent className="max-h-60 overflow-y-auto">
                      {asrModels.length === 0 ? (
                        <div className="p-2 text-xs text-text-secondary text-center">No speech-to-text models connected via API key</div>
                      ) : (
                        asrModels.map((m) => (
                          <SelectItem key={m.id} value={m.id}>
                            {m.model_name} ({m.provider})
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-text-primary flex items-center gap-1.5">
                    <Volume2 className="size-3.5 text-cyan-500" /> Default Text-to-Speech (TTS)
                  </label>
                  <Select
                    value={instanceStats?.default_tts_model || ''}
                    onValueChange={(val) => handleUpdateGlobalDefaults('default_tts_model', val)}
                  >
                    <SelectTrigger className="bg-bg-card border-border-button text-xs">
                      <SelectValue placeholder={ttsModels.length > 0 ? "Select TTS Model" : "Optional / None"} />
                    </SelectTrigger>
                    <SelectContent className="max-h-60 overflow-y-auto">
                      {ttsModels.length === 0 ? (
                        <div className="p-2 text-xs text-text-secondary text-center">No text-to-speech models connected via API key</div>
                      ) : (
                        ttsModels.map((m) => (
                          <SelectItem key={m.id} value={m.id}>
                            {m.model_name} ({m.provider})
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Plan Tier Defaults */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-text-secondary">Free Plan Default Model</label>
                  <Select
                    value={instanceStats?.default_free_model_id || ''}
                    onValueChange={(val) => handleUpdateGlobalDefaults('default_free_model_id', val)}
                  >
                    <SelectTrigger className="bg-bg-base border-border-button text-xs">
                      <SelectValue placeholder={chatModels.length > 0 ? "Select Model for Free Plan" : "No active API models"} />
                    </SelectTrigger>
                    <SelectContent className="max-h-60 overflow-y-auto">
                      {chatModels.map((m) => (
                        <SelectItem key={m.id} value={m.id}>
                          {m.model_name} ({m.provider})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-text-secondary">Plus Plan Default Model</label>
                  <Select
                    value={instanceStats?.default_plus_model_id || ''}
                    onValueChange={(val) => handleUpdateGlobalDefaults('default_plus_model_id', val)}
                  >
                    <SelectTrigger className="bg-bg-base border-border-button text-xs">
                      <SelectValue placeholder={chatModels.length > 0 ? "Select Model for Plus Plan" : "No active API models"} />
                    </SelectTrigger>
                    <SelectContent className="max-h-60 overflow-y-auto">
                      {chatModels.map((m) => (
                        <SelectItem key={m.id} value={m.id}>
                          {m.model_name} ({m.provider})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-text-secondary">Pro Plan Default Model</label>
                  <Select
                    value={instanceStats?.default_pro_model_id || ''}
                    onValueChange={(val) => handleUpdateGlobalDefaults('default_pro_model_id', val)}
                  >
                    <SelectTrigger className="bg-bg-base border-border-button text-xs">
                      <SelectValue placeholder={chatModels.length > 0 ? "Select Model for Pro Plan" : "No active API models"} />
                    </SelectTrigger>
                    <SelectContent className="max-h-60 overflow-y-auto">
                      {chatModels.map((m) => (
                        <SelectItem key={m.id} value={m.id}>
                          {m.model_name} ({m.provider})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* AI Providers Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-text-primary flex items-center gap-2">
                  <Building2 className="size-4 text-accent-primary" /> Platform AI Providers
                </h3>
                <p className="text-xs text-text-secondary">
                  API credentials belong to the Global Instance and are never exposed to frontend users.
                </p>
              </div>
              <Button size="sm" onClick={handleOpenAddProvider}>
                <Plus className="size-4 mr-1.5" /> Add Provider
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {providers.map((p) => {
                const isConfigured = p.has_api_key || p.is_configured || Boolean(p.api_key_masked || p.masked_api_key);
                const displayMask = p.masked_api_key || p.api_key_masked || (isConfigured ? '••••••••••••' : '');
                const isTesting = testingProviderName === p.provider_name;
                const isLiveVerifying = liveVerifyingProviderName === p.provider_name;
                const isWiping = wipingProviderName === p.provider_name;
                const providerModelsCount = models.filter(
                  (m) => m.provider.toLowerCase() === p.provider_name.toLowerCase()
                ).length;

                return (
                  <Card
                    key={p.id || p.provider_name}
                    className="bg-bg-card border-border-button hover:border-accent-primary/50 transition-all shadow-sm flex flex-col justify-between"
                  >
                    <div>
                      <CardHeader className="pb-2.5">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <div className="p-1.5 rounded-lg bg-accent-primary/10 text-accent-primary border border-accent-primary/20">
                              <Zap className="size-4" />
                            </div>
                            <div>
                              <CardTitle className="text-sm font-bold text-text-primary">
                                {p.display_name || p.provider_name}
                              </CardTitle>
                              <span className="text-[10px] font-mono text-text-secondary">
                                {p.provider_name.toLowerCase()}
                              </span>
                            </div>
                          </div>
                          <div>{getProviderStatusBadge(p)}</div>
                        </div>
                      </CardHeader>
                      <CardContent className="text-xs space-y-2.5 pt-0">
                        <div className="space-y-1 p-2.5 rounded-lg bg-bg-base/70 border border-border-button/40">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="text-text-secondary">API Key:</span>
                            <span className="font-mono text-text-primary font-medium">
                              {isConfigured ? (
                                <span className="text-emerald-500 font-mono font-bold">{displayMask}</span>
                              ) : (
                                <span className="text-amber-500 font-semibold">⚪ Unconfigured</span>
                              )}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="text-text-secondary">Base URL:</span>
                            <span
                              className="font-mono text-text-primary truncate max-w-[170px]"
                              title={p.base_url || 'Default'}
                            >
                              {p.base_url || 'Default'}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="text-text-secondary">Platform Models:</span>
                            <span className="font-semibold text-text-primary">
                              {providerModelsCount} synced
                            </span>
                          </div>
                          {p.last_error && (
                            <div className="text-[10px] text-rose-400 bg-rose-500/10 p-1.5 rounded border border-rose-500/20 mt-1">
                              <span className="font-semibold">Last Error:</span> {p.last_error}
                            </div>
                          )}
                        </div>

                        {/* Action Buttons: Ping & Live Verification */}
                        <div className="grid grid-cols-2 gap-1.5 pt-1">
                          <Button
                            variant="outline"
                            size="xs"
                            disabled={!isConfigured || isTesting || isLiveVerifying}
                            onClick={() => handleTestProviderConnection(p.provider_name)}
                            className="text-[11px] h-7 flex items-center justify-center gap-1 border-border-button hover:bg-bg-base"
                          >
                            <Activity className={`size-3 text-blue-500 ${isTesting ? 'animate-spin' : ''}`} />
                            {isTesting ? 'Testing...' : 'Test Ping'}
                          </Button>

                          <Button
                            variant="outline"
                            size="xs"
                            disabled={!isConfigured || isTesting || isLiveVerifying}
                            onClick={() => handleLiveVerifyProvider(p.provider_name)}
                            className={`text-[11px] h-7 flex items-center justify-center gap-1 border-border-button hover:bg-bg-base ${
                              p.status === 'unverified'
                                ? 'border-amber-500/50 bg-amber-500/10 text-amber-500 font-bold animate-pulse'
                                : ''
                            }`}
                          >
                            <Zap className={`size-3 text-amber-500 ${isLiveVerifying ? 'animate-spin' : ''}`} />
                            {isLiveVerifying ? 'Verifying...' : '⚡ Live Verify'}
                          </Button>
                        </div>
                      </CardContent>
                    </div>

                    {/* Footer Row: Replace Key, Wipe Key, Edit, Delete */}
                    <div className="px-4 py-2.5 bg-bg-base/40 border-t border-border-button/60 flex items-center justify-between gap-1 rounded-b-lg">
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="xs"
                          onClick={() => handleOpenReplaceKeyModal(p)}
                          className="text-[11px] h-6 px-2 text-text-secondary hover:text-accent-primary"
                        >
                          <Key className="size-3 mr-1" /> Key
                        </Button>
                        {isConfigured && (
                          <Button
                            variant="ghost"
                            size="xs"
                            disabled={isWiping}
                            onClick={() => handleWipeProviderKey(p.provider_name)}
                            className="text-[11px] h-6 px-2 text-rose-400 hover:text-rose-600 hover:bg-rose-500/10"
                            title="Wipe key with cascade disable on all models"
                          >
                            <Lock className="size-3 mr-1" /> Wipe
                          </Button>
                        )}
                      </div>

                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="xs"
                          onClick={() => handleOpenEditProvider(p)}
                          className="text-[11px] h-6 px-2 text-text-secondary hover:text-text-primary"
                          title="Edit Provider Settings"
                        >
                          <Edit3 className="size-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="xs"
                          onClick={() => handleDeleteProvider(p.id)}
                          className="text-[11px] h-6 px-2 text-rose-500 hover:text-rose-600"
                          title="Delete Provider"
                        >
                          <Trash2 className="size-3" />
                        </Button>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>

            {/* AI Gateway 5-Tier Policy Enforcement & Error Codes Reference Guide */}
            <Card className="bg-bg-card border-border-button mt-6 shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Shield className="size-4 text-accent-primary" /> AI Gateway 5-Tier Policy Enforcement & Error Guide
                </CardTitle>
                <CardDescription className="text-xs">
                  Every user model request is evaluated through a strict 5-level pre-flight hierarchy. If blocked, the gateway returns a descriptive machine code:
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3">
                  {Object.entries(POLICY_ERROR_EXPLANATIONS).map(([code, item]) => (
                    <div
                      key={code}
                      className="p-3 rounded-lg bg-bg-base/80 border border-border-button flex flex-col justify-between space-y-2"
                    >
                      <div>
                        <div className="flex items-center justify-between gap-1 mb-1.5">
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold border ${item.badgeColor}`}>
                            {item.level}
                          </span>
                          <span className="font-mono text-[10px] text-text-secondary truncate">{code}</span>
                        </div>
                        <div className="font-semibold text-text-primary text-xs">{item.title}</div>
                        <p className="text-[11px] text-text-secondary mt-1 leading-snug">{item.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* TAB 2: Platform Models & Governance */}
        <TabsContent value="models" className="space-y-4 pt-2">
          {/* Header Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-bg-card p-3 rounded-lg border border-border-button shadow-sm">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setModelsSubTab('configured')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-all ${
                  modelsSubTab === 'configured'
                    ? 'bg-accent-primary text-white shadow-sm'
                    : 'bg-bg-base text-text-secondary hover:text-text-primary border border-border-button/60'
                }`}
              >
                <Cpu className="size-3.5" />
                Configured Platform Models ({models.length})
              </button>
              <button
                type="button"
                onClick={() => {
                  setModelsSubTab('dynamic');
                  if (dynamicModels.length === 0 && providers.length > 0) {
                    handleFetchDynamicModels(selectedDiscoveryProvider || providers[0].provider_name);
                  }
                }}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-all ${
                  modelsSubTab === 'dynamic'
                    ? 'bg-accent-primary text-white shadow-sm'
                    : 'bg-bg-base text-text-secondary hover:text-text-primary border border-border-button/60'
                }`}
              >
                <Globe className="size-3.5" />
                Live Provider Discovery & Exclusion (Level 1)
              </button>
            </div>

            <Button size="sm" onClick={handleOpenAddModel} className="text-xs h-8">
              <Plus className="size-3.5 mr-1" /> Add Platform Model
            </Button>
          </div>

          {modelsSubTab === 'configured' ? (
            /* SubTab 1: Configured Platform Models */
            <div className="border border-border-button rounded-lg bg-bg-card overflow-hidden shadow-sm">
              <div className="p-3 bg-bg-base/40 border-b border-border-button flex items-center justify-between">
                <div className="text-xs text-text-secondary">
                  Active Platform Models with <span className="font-semibold text-text-primary">Level 2 Global Kill-Switch</span> and pricing policies.
                </div>
                <div className="flex items-center gap-2 text-[11px] text-text-secondary">
                  <span className="flex items-center gap-1">
                    <span className="size-2 rounded-full bg-emerald-500" /> Active
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="size-2 rounded-full bg-rose-500" /> Kill-Switch Disabled
                  </span>
                </div>
              </div>
              <table className="w-full text-xs text-left">
                <thead className="bg-bg-base/70 text-text-secondary border-b border-border-button">
                  <tr>
                    <th className="p-3">Model</th>
                    <th className="p-3">Provider</th>
                    <th className="p-3">Type</th>
                    <th className="p-3">Allowed Plans</th>
                    <th className="p-3 text-right">Input ($/1M)</th>
                    <th className="p-3 text-right">Output ($/1M)</th>
                    <th className="p-3 text-center">Global Kill-Switch (Level 2)</th>
                    <th className="p-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-button">
                  {models.map((m) => {
                    const isToggling = togglingGlobalModelId === m.id;
                    const parentProvider = providers.find(
                      (p) => p.provider_name.toLowerCase() === m.provider.toLowerCase()
                    );
                    const isExcludedInProvider = Boolean(
                      parentProvider?.extra?.excluded_models?.includes(m.model_name)
                    );

                    return (
                      <tr key={m.id} className="hover:bg-bg-base/40 transition-colors">
                        <td className="p-3 font-semibold text-text-primary">
                          <div className="flex items-center gap-1.5">
                            <span>{m.model_name}</span>
                            {isExcludedInProvider && (
                              <span
                                className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/15 text-amber-500 border border-amber-500/30"
                                title="Excluded from parent provider via Level 1 rule"
                              >
                                Level 1 Excluded
                              </span>
                            )}
                          </div>
                          <span className="block text-[10px] font-mono text-text-secondary">{m.id}</span>
                        </td>
                        <td className="p-3 text-text-primary font-medium">{m.provider}</td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded text-[10px] bg-bg-base font-mono border border-border-button">
                            {m.model_type}
                          </span>
                        </td>
                        <td className="p-3">
                          <div className="flex gap-1 flex-wrap">
                            {(m.allowed_plans || []).map((plan) => (
                              <span
                                key={plan}
                                className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${
                                  plan === 'free'
                                    ? 'bg-emerald-500/15 text-emerald-500'
                                    : plan === 'plus'
                                    ? 'bg-blue-500/15 text-blue-500'
                                    : 'bg-purple-500/15 text-purple-500'
                                }`}
                              >
                                {plan}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="p-3 text-right font-mono">${(m.input_token_price || 0).toFixed(3)}</td>
                        <td className="p-3 text-right font-mono">${(m.output_token_price || 0).toFixed(3)}</td>
                        <td className="p-3 text-center">
                          <button
                            type="button"
                            disabled={isToggling}
                            onClick={() => handleToggleGlobalModel(m.id, m.enabled)}
                            className={`px-2.5 py-1 rounded-full text-[10px] font-bold inline-flex items-center gap-1 transition-all ${
                              m.enabled
                                ? 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30 hover:bg-emerald-500/25'
                                : 'bg-rose-500/15 text-rose-500 border border-rose-500/30 hover:bg-rose-500/25'
                            }`}
                            title="Click to toggle Global Kill-Switch"
                          >
                            <span
                              className={`size-1.5 rounded-full ${
                                m.enabled ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'
                              }`}
                            />
                            {isToggling ? 'Updating...' : m.enabled ? 'ACTIVE' : 'KILL-SWITCH (OFF)'}
                          </button>
                        </td>
                        <td className="p-3 text-right">
                          <div className="flex justify-end gap-1">
                            <Button variant="ghost" size="xs" onClick={() => handleOpenEditModel(m)} title="Edit Model Pricing">
                              <Edit3 className="size-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="xs"
                              className="text-rose-500 hover:text-rose-600"
                              onClick={() => handleDeleteModel(m.id)}
                              title="Delete Model"
                            >
                              <Trash2 className="size-3.5" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            /* SubTab 2: Provider Dynamic Discovery & Exclusion (Level 1) */
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-bg-card border border-border-button shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-text-primary">Select AI Provider:</label>
                    <Select
                      value={selectedDiscoveryProvider}
                      onValueChange={(val) => {
                        setSelectedDiscoveryProvider(val);
                        handleFetchDynamicModels(val);
                      }}
                    >
                      <SelectTrigger className="w-[200px] h-8 bg-bg-base border-border-button text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {providers.map((p) => (
                          <SelectItem key={p.provider_name} value={p.provider_name}>
                            {p.provider_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="pt-4">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={loadingDynamicModels}
                      onClick={() => handleFetchDynamicModels(selectedDiscoveryProvider)}
                      className="text-xs h-8 flex items-center gap-1.5"
                    >
                      <RefreshCw className={`size-3.5 ${loadingDynamicModels ? 'animate-spin' : ''}`} />
                      {loadingDynamicModels ? 'Querying API...' : 'Live Sync Discovered Models'}
                    </Button>
                  </div>
                </div>
                <div className="text-xs text-text-secondary max-w-md">
                  Level 1 Exclusion immediately hides the model from all users of this provider and returns <span className="font-mono text-amber-500">PROVIDER_EXCLUDED</span> if invoked.
                </div>
              </div>

              <div className="border border-border-button rounded-lg bg-bg-card overflow-hidden shadow-sm">
                <table className="w-full text-xs text-left">
                  <thead className="bg-bg-base/70 text-text-secondary border-b border-border-button">
                    <tr>
                      <th className="p-3">Discovered Model Identifier</th>
                      <th className="p-3">Provider</th>
                      <th className="p-3">Type</th>
                      <th className="p-3">Discovery Status</th>
                      <th className="p-3 text-center">Level 1 Exclusion Rule</th>
                      <th className="p-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-button">
                    {dynamicModels.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="p-8 text-center text-text-secondary">
                          {loadingDynamicModels ? (
                            <div className="flex items-center justify-center gap-2">
                              <RefreshCw className="size-4 animate-spin text-accent-primary" />
                              <span>Querying live models from {selectedDiscoveryProvider}...</span>
                            </div>
                          ) : (
                            <div>Click &quot;Live Sync Discovered Models&quot; above to query available models.</div>
                          )}
                        </td>
                      </tr>
                    ) : (
                      dynamicModels.map((dm) => {
                        const isExclusionPending = togglingExclusionKey === `${dm.provider}_${dm.model_name}`;
                        return (
                          <tr key={dm.model_name} className="hover:bg-bg-base/40 transition-colors">
                            <td className="p-3 font-semibold text-text-primary font-mono">
                              {dm.model_name}
                            </td>
                            <td className="p-3 text-text-primary font-medium">{dm.provider}</td>
                            <td className="p-3">
                              <span className="px-2 py-0.5 rounded text-[10px] bg-bg-base font-mono border border-border-button">
                                {dm.model_type}
                              </span>
                            </td>
                            <td className="p-3">
                              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold border border-emerald-500/20">
                                Live Discovered
                              </span>
                            </td>
                            <td className="p-3 text-center">
                              <button
                                type="button"
                                disabled={isExclusionPending}
                                onClick={() => handleToggleModelExclusion(dm.provider, dm.model_name, Boolean(dm.is_excluded))}
                                className={`px-2.5 py-1 rounded-full text-[10px] font-bold inline-flex items-center gap-1 transition-all ${
                                  dm.is_excluded
                                    ? 'bg-amber-500/15 text-amber-500 border border-amber-500/30 hover:bg-amber-500/25'
                                    : 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30 hover:bg-emerald-500/25'
                                }`}
                                title="Click to toggle Level 1 Exclusion"
                              >
                                {isExclusionPending ? (
                                  <RefreshCw className="size-3 animate-spin" />
                                ) : (
                                  <span
                                    className={`size-1.5 rounded-full ${
                                      dm.is_excluded ? 'bg-amber-500' : 'bg-emerald-500'
                                    }`}
                                  />
                                )}
                                {dm.is_excluded ? 'EXCLUDED (Level 1)' : 'AVAILABLE'}
                              </button>
                            </td>
                            <td className="p-3 text-right">
                              <Button
                                variant="outline"
                                size="xs"
                                onClick={() => {
                                  setEditingModel({
                                    provider: dm.provider,
                                    model_name: dm.model_name,
                                    model_type: dm.model_type as any,
                                    base_url: providers.find((p) => p.provider_name.toLowerCase() === dm.provider.toLowerCase())?.base_url || '',
                                    input_token_price: 0.15,
                                    output_token_price: 0.60,
                                    max_tokens: 8192,
                                    enabled: true,
                                    is_global: true,
                                    allowed_plans: ['plus', 'pro'],
                                  });
                                  setIsModelModalOpen(true);
                                }}
                                className="text-[11px] h-6 px-2"
                              >
                                <Plus className="size-3 mr-1" /> Configure Pricing
                              </Button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </TabsContent>

        {/* TAB 3: Subscriptions & Policies */}
        <TabsContent value="subscriptions" className="space-y-5 pt-2">
          {/* Sub-Navigation */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-bg-card p-3 rounded-lg border border-border-button shadow-sm">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPolicySubTab('matrix')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-all ${
                  policySubTab === 'matrix'
                    ? 'bg-accent-primary text-white shadow-sm'
                    : 'bg-bg-base text-text-secondary hover:text-text-primary border border-border-button/60'
                }`}
              >
                <Layers className="size-3.5" />
                Subscription Plans & Policy Matrix (Level 4 Baseline)
              </button>
              <button
                type="button"
                onClick={() => setPolicySubTab('user_overrides')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-all ${
                  policySubTab === 'user_overrides'
                    ? 'bg-accent-primary text-white shadow-sm'
                    : 'bg-bg-base text-text-secondary hover:text-text-primary border border-border-button/60'
                }`}
              >
                <Users className="size-3.5" />
                Per-User Overrides & Quotas (Level 3 & Level 5)
              </button>
            </div>
          </div>

          {policySubTab === 'matrix' ? (
            /* SubTab 1: Plan Limits & Matrix */
            <div className="space-y-6">
              {/* Subscription Plans Limit Configuration */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {plans.map((p) => {
                  const isPro = p.id.toLowerCase() === 'pro';
                  const isPlus = p.id.toLowerCase() === 'plus';
                  return (
                    <Card key={p.id} className="bg-bg-card border-border-button relative overflow-hidden shadow-sm">
                      <div className={`h-1.5 w-full ${isPro ? 'bg-purple-500' : isPlus ? 'bg-blue-500' : 'bg-emerald-500'}`} />
                      <CardHeader className="pb-3">
                        <div className="flex justify-between items-center">
                          <CardTitle className="text-base font-bold">{p.name}</CardTitle>
                          <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-bg-base border border-border-button">
                            {p.id}
                          </span>
                        </div>
                      </CardHeader>
                      <CardContent className="text-xs space-y-3 pt-0">
                        <div className="space-y-1">
                          <label className="text-text-secondary text-[11px]">Monthly Token Limit</label>
                          <Input
                            type="number"
                            defaultValue={p.monthly_token_limit}
                            onBlur={(e) => handleUpdatePlanField(p.id, 'monthly_token_limit', parseInt(e.target.value) || 0)}
                            className="bg-bg-base h-8 text-xs font-mono"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-text-secondary text-[11px]">Daily Token Limit</label>
                          <Input
                            type="number"
                            defaultValue={p.daily_token_limit || 50000}
                            onBlur={(e) => handleUpdatePlanField(p.id, 'daily_token_limit', parseInt(e.target.value) || 0)}
                            className="bg-bg-base h-8 text-xs font-mono"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-text-secondary text-[11px]">Daily Requests Limit</label>
                          <Input
                            type="number"
                            defaultValue={p.daily_request_limit || 500}
                            onBlur={(e) => handleUpdatePlanField(p.id, 'daily_request_limit', parseInt(e.target.value) || 0)}
                            className="bg-bg-base h-8 text-xs font-mono"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-text-secondary text-[11px]">Rate Limit (Req / Min)</label>
                          <Input
                            type="number"
                            defaultValue={p.requests_per_minute || 60}
                            onBlur={(e) => handleUpdatePlanField(p.id, 'requests_per_minute', parseInt(e.target.value) || 0)}
                            className="bg-bg-base h-8 text-xs font-mono"
                          />
                        </div>

                        <div className="pt-2 border-t border-border-button flex items-center justify-between">
                          <span className="text-text-secondary">Allow PRO BYOK:</span>
                          <Switch
                            checked={p.allow_byok ?? isPro}
                            disabled={!isPro}
                            onCheckedChange={(checked) => handleUpdatePlanField(p.id, 'allow_byok', checked)}
                          />
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>

              {/* Model Access Policy Matrix */}
              <Card className="bg-bg-card border-border-button shadow-sm">
                <CardHeader className="pb-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <CardTitle className="text-base font-semibold">Model Access Policy Matrix (Level 4)</CardTitle>
                      <CardDescription className="text-xs">
                        Define which models are authorized for each subscription plan. Users without per-user overrides inherit these rules.
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-text-secondary">Filter Plan:</span>
                      <Select value={selectedPlanId} onValueChange={(val) => { setSelectedPlanId(val); fetchPolicies(val); }}>
                        <SelectTrigger className="w-32 h-8 text-xs bg-bg-base border-border-button">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="free">FREE</SelectItem>
                          <SelectItem value="plus">PLUS</SelectItem>
                          <SelectItem value="pro">PRO</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="border border-border-button rounded-lg overflow-hidden">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-bg-base text-text-secondary border-b border-border-button">
                        <tr>
                          <th className="p-3">Model</th>
                          <th className="p-3">Provider</th>
                          <th className="p-3">Type</th>
                          <th className="p-3 text-center">Enabled for {selectedPlanId.toUpperCase()}</th>
                          <th className="p-3 text-right">Per-Model Monthly Cap (0 = Unlimited)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-button">
                        {models.map((m) => {
                          const policy = policies.find((p) => p.model_id === m.id);
                          const isEnabled = policy ? policy.enabled : false;
                          const limit = policy ? policy.model_token_limit : 0;
                          return (
                            <tr key={m.id} className="hover:bg-bg-base/40 transition-colors">
                              <td className="p-3 font-medium text-text-primary">{m.model_name}</td>
                              <td className="p-3 text-text-secondary">{m.provider}</td>
                              <td className="p-3 font-mono">{m.model_type}</td>
                              <td className="p-3 text-center">
                                <Switch
                                  checked={isEnabled}
                                  onCheckedChange={(checked) => handleTogglePolicyAccess(selectedPlanId, m.id, checked)}
                                />
                              </td>
                              <td className="p-3 text-right">
                                <Input
                                  type="number"
                                  defaultValue={limit}
                                  onBlur={(e) => handleUpdatePolicyLimit(selectedPlanId, m.id, parseInt(e.target.value) || 0)}
                                  className="w-36 ml-auto h-7 text-xs font-mono bg-bg-base text-right"
                                />
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            /* SubTab 2: Per-User Policy & Overrides (Levels 3 & 5) */
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column: Search & User Overrides List */}
              <div className="space-y-4">
                <Card className="bg-bg-card border-border-button shadow-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                      <Users className="size-4 text-accent-primary" /> Inspect User Policy
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Enter User ID to load full policy context (Plan Baseline + Overrides + Live Quota).
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex gap-2">
                      <Input
                        value={userSearchId}
                        onChange={(e) => setUserSearchId(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSelectUserForPolicy(userSearchId)}
                        placeholder="User ID (UUID or text)..."
                        className="text-xs h-8 bg-bg-base font-mono"
                      />
                      <Button
                        size="sm"
                        disabled={searchingUserPolicy || !userSearchId.trim()}
                        onClick={() => handleSelectUserForPolicy(userSearchId)}
                        className="text-xs h-8 shrink-0"
                      >
                        {searchingUserPolicy ? <RefreshCw className="size-3.5 animate-spin" /> : 'Inspect'}
                      </Button>
                    </div>

                    <div className="pt-2 border-t border-border-button">
                      <div className="text-[11px] font-semibold text-text-secondary mb-2 flex items-center justify-between">
                        <span>Users with Active Overrides:</span>
                        <Button
                          variant="ghost"
                          size="xs"
                          onClick={fetchUserOverridesList}
                          className="h-5 px-1.5 text-[10px]"
                        >
                          <RefreshCw className={`size-2.5 mr-1 ${loadingUserOverrides ? 'animate-spin' : ''}`} /> Refresh
                        </Button>
                      </div>
                      <div className="space-y-1.5 max-h-[360px] overflow-y-auto pr-1">
                        {userOverridesList.length === 0 ? (
                          <div className="text-xs text-text-secondary text-center py-4">
                            No custom user overrides configured yet.
                          </div>
                        ) : (
                          userOverridesList.map((uo) => (
                            <button
                              key={uo.user_id}
                              type="button"
                              onClick={() => handleSelectUserForPolicy(uo.user_id)}
                              className={`w-full text-left p-2.5 rounded-lg border text-xs transition-all ${
                                selectedUserDetail?.user_id === uo.user_id
                                  ? 'bg-accent-primary/10 border-accent-primary text-text-primary'
                                  : 'bg-bg-base/70 border-border-button hover:bg-bg-base text-text-secondary'
                              }`}
                            >
                              <div className="font-semibold text-text-primary truncate">
                                {uo.nickname || uo.email || uo.user_id}
                              </div>
                              <div className="text-[10px] font-mono text-text-secondary truncate mt-0.5">
                                ID: {uo.user_id}
                              </div>
                              <div className="flex gap-1 mt-1.5">
                                {uo.has_model_overrides && (
                                  <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-orange-500/15 text-orange-500 border border-orange-500/30">
                                    Model Overrides (L3)
                                  </span>
                                )}
                                {uo.has_token_override && (
                                  <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-purple-500/15 text-purple-500 border border-purple-500/30">
                                    Token Limit (L5)
                                  </span>
                                )}
                              </div>
                            </button>
                          ))
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Right Column: Full-Context User Inspector */}
              <div className="lg:col-span-2 space-y-4">
                {selectedUserDetail ? (
                  <Card className="bg-bg-card border-border-button shadow-sm">
                    <CardHeader className="pb-3 border-b border-border-button">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <CardTitle className="text-base font-bold text-text-primary">
                              {selectedUserDetail.nickname || selectedUserDetail.email || 'User Policy Profile'}
                            </CardTitle>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              selectedUserDetail.plan === 'pro'
                                ? 'bg-purple-500/15 text-purple-500 border border-purple-500/30'
                                : selectedUserDetail.plan === 'plus'
                                ? 'bg-blue-500/15 text-blue-500 border border-blue-500/30'
                                : 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30'
                            }`}>
                              Plan: {selectedUserDetail.plan || 'FREE'} (Level 4 Baseline)
                            </span>
                          </div>
                          <p className="text-xs font-mono text-text-secondary mt-0.5">
                            User ID: {selectedUserDetail.user_id} • Tenant: {selectedUserDetail.tenant_id}
                          </p>
                        </div>

                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleResetUserPolicy(selectedUserDetail.user_id)}
                            className="text-xs text-rose-500 hover:text-rose-600 h-8"
                          >
                            <Trash2 className="size-3 mr-1" /> Reset to Plan Default
                          </Button>
                          <Button
                            size="sm"
                            disabled={savingUserPolicy}
                            onClick={handleSaveUserPolicy}
                            className="text-xs h-8"
                          >
                            {savingUserPolicy ? <RefreshCw className="size-3.5 animate-spin mr-1" /> : <Save className="size-3.5 mr-1" />}
                            Save Overrides
                          </Button>
                        </div>
                      </div>
                    </CardHeader>

                    <CardContent className="space-y-5 pt-4">
                      {/* Level 5 Quota Gauge & Token Limit Controls */}
                      <div className="p-3.5 rounded-lg bg-bg-base/70 border border-border-button space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-text-primary flex items-center gap-1.5">
                            <Zap className="size-3.5 text-purple-500" /> Level 5 Token Quota & Usage Gauge
                          </span>
                          <div className="flex items-center gap-2">
                            <span className="text-[11px] text-text-secondary">Enforce Custom Limit:</span>
                            <Switch
                              checked={userEditedTokenLimitEnabled}
                              onCheckedChange={setUserEditedTokenLimitEnabled}
                            />
                          </div>
                        </div>

                        {/* Usage Gauge */}
                        {(() => {
                          const used = selectedUserDetail.token_usage?.total_tokens || selectedUserDetail.token_usage?.total_used || 0;
                          const limit = userEditedTokenLimit > 0 ? userEditedTokenLimit : (selectedUserDetail.monthly_token_limit || 100000);
                          const pct = Math.min(100, Math.round((used / limit) * 100));
                          return (
                            <div className="space-y-1.5">
                              <div className="flex justify-between text-[11px] font-mono">
                                <span className="text-text-secondary">
                                  Used: <strong className="text-text-primary">{used.toLocaleString()}</strong> tokens
                                </span>
                                <span className="text-text-secondary">
                                  Limit: <strong className="text-text-primary">{limit.toLocaleString()}</strong> ({pct}%)
                                </span>
                              </div>
                              <div className="w-full bg-bg-card h-2.5 rounded-full overflow-hidden border border-border-button/80">
                                <div
                                  className={`h-full rounded-full transition-all ${
                                    pct >= 90 ? 'bg-rose-500' : pct >= 75 ? 'bg-amber-500' : 'bg-accent-primary'
                                  }`}
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                            </div>
                          );
                        })()}

                        <div className="flex items-center gap-3 pt-1">
                          <div className="space-y-1 flex-1">
                            <label className="text-[11px] text-text-secondary font-medium">Custom Monthly Token Limit (0 = Default):</label>
                            <Input
                              type="number"
                              value={userEditedTokenLimit}
                              onChange={(e) => setUserEditedTokenLimit(parseInt(e.target.value) || 0)}
                              className="text-xs h-8 bg-bg-card font-mono"
                            />
                          </div>
                        </div>
                      </div>

                      {/* Level 3 Model Overrides Matrix */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="text-xs font-bold text-text-primary flex items-center gap-1.5">
                              <Shield className="size-3.5 text-orange-500" /> Level 3 Granular Model Overrides (ALLOW / DENY)
                            </h4>
                            <p className="text-[11px] text-text-secondary">
                              Explicit DENY immediately blocks the model for this user with error <span className="font-mono text-orange-500">USER_RESTRICTED (403)</span>.
                            </p>
                          </div>
                        </div>

                        <div className="border border-border-button rounded-lg overflow-hidden bg-bg-base/40">
                          <table className="w-full text-xs text-left">
                            <thead className="bg-bg-base text-text-secondary border-b border-border-button">
                              <tr>
                                <th className="p-2.5">Model</th>
                                <th className="p-2.5">Provider</th>
                                <th className="p-2.5">Plan Baseline</th>
                                <th className="p-2.5 text-center">Level 3 Override Decision</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-border-button">
                              {models.map((m) => {
                                const currentOverride = userEditedOverrides[m.model_name] || 'DEFAULT';
                                const planAllows = (m.allowed_plans || []).includes(selectedUserDetail.plan || 'free');

                                return (
                                  <tr key={m.id} className="hover:bg-bg-base/60 transition-colors">
                                    <td className="p-2.5 font-semibold text-text-primary">
                                      {m.model_name}
                                    </td>
                                    <td className="p-2.5 text-text-secondary">{m.provider}</td>
                                    <td className="p-2.5">
                                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                                        planAllows ? 'bg-emerald-500/15 text-emerald-500' : 'bg-zinc-500/15 text-zinc-400'
                                      }`}>
                                        {planAllows ? 'Included in Plan' : 'Not in Plan'}
                                      </span>
                                    </td>
                                    <td className="p-2.5 text-center">
                                      <div className="inline-flex items-center gap-1 p-0.5 rounded-lg bg-bg-card border border-border-button">
                                        <button
                                          type="button"
                                          onClick={() =>
                                            setUserEditedOverrides({
                                              ...userEditedOverrides,
                                              [m.model_name]: 'ALLOW',
                                            })
                                          }
                                          className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all ${
                                            currentOverride === 'ALLOW'
                                              ? 'bg-emerald-500 text-white shadow-xs'
                                              : 'text-text-secondary hover:text-text-primary'
                                          }`}
                                        >
                                          ALLOW
                                        </button>
                                        <button
                                          type="button"
                                          onClick={() =>
                                            setUserEditedOverrides({
                                              ...userEditedOverrides,
                                              [m.model_name]: 'DEFAULT',
                                            })
                                          }
                                          className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all ${
                                            currentOverride === 'DEFAULT'
                                              ? 'bg-zinc-600 text-white shadow-xs'
                                              : 'text-text-secondary hover:text-text-primary'
                                          }`}
                                        >
                                          INHERIT
                                        </button>
                                        <button
                                          type="button"
                                          onClick={() =>
                                            setUserEditedOverrides({
                                              ...userEditedOverrides,
                                              [m.model_name]: 'DENY',
                                            })
                                          }
                                          className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all ${
                                            currentOverride === 'DENY'
                                              ? 'bg-rose-500 text-white shadow-xs'
                                              : 'text-text-secondary hover:text-text-primary'
                                          }`}
                                        >
                                          DENY
                                        </button>
                                      </div>
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <Card className="bg-bg-card border-border-button p-12 text-center shadow-sm">
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <div className="p-3 rounded-full bg-accent-primary/10 text-accent-primary">
                        <Users className="size-8" />
                      </div>
                      <h3 className="text-base font-semibold text-text-primary">No User Selected</h3>
                      <p className="text-xs text-text-secondary max-w-sm">
                        Enter a User ID on the left or select a user from the active overrides list to view and configure their Level 3 (ALLOW/DENY) model rules and Level 5 token limits.
                      </p>
                    </div>
                  </Card>
                )}
              </div>
            </div>
          )}
        </TabsContent>

        {/* TAB 4: BYOK Administration */}
        <TabsContent value="byok" className="space-y-4 pt-2">
          <Card className="bg-bg-card border-border-button">
            <CardHeader>
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Key className="size-4 text-purple-500" /> PRO Bring-Your-Own-Key (BYOK) Management
              </CardTitle>
              <CardDescription className="text-xs">
                PRO users can register custom AI connections integrated with the single Global Instance. All API keys are encrypted at rest with AES/HMAC.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <div className="p-4 rounded-lg bg-bg-base border border-border-button">
                  <div className="text-xs text-text-secondary">Total BYOK Models</div>
                  <div className="text-xl font-bold text-text-primary mt-1">
                    {byokStats?.total_byok_models || 0}
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-bg-base border border-border-button">
                  <div className="text-xs text-text-secondary">Active Connections</div>
                  <div className="text-xl font-bold text-emerald-500 mt-1">
                    {byokStats?.active_byok_models || 0}
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-bg-base border border-border-button">
                  <div className="text-xs text-text-secondary">Locked (Downgraded)</div>
                  <div className="text-xl font-bold text-amber-500 mt-1">
                    {byokStats?.locked_byok_models || 0}
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-bg-base border border-border-button">
                  <div className="text-xs text-text-secondary">PRO Users with BYOK</div>
                  <div className="text-xl font-bold text-purple-500 mt-1">
                    {byokStats?.byok_users_count || 0}
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-bg-base border border-border-button space-y-4">
                <h4 className="text-sm font-semibold text-text-primary">Global BYOK Controls</h4>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs font-medium text-text-primary">Enable BYOK for PRO Plan</div>
                    <div className="text-[11px] text-text-secondary">Toggle custom AI key connections globally for PRO subscribers</div>
                  </div>
                  <Switch
                    checked={instanceStats?.byok_enabled ?? true}
                    onCheckedChange={(checked) => handleUpdateGlobalDefaults('byok_enabled', checked)}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-border-button">
                  <div className="space-y-1">
                    <label className="text-xs text-text-secondary">Max BYOK Models per PRO User</label>
                    <Input
                      type="number"
                      defaultValue={instanceStats?.max_byok_models || 10}
                      onBlur={(e) => handleUpdateGlobalDefaults('max_byok_models', parseInt(e.target.value) || 10)}
                      className="bg-bg-card h-8 text-xs font-mono"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-text-secondary">Monthly BYOK Token Limit</label>
                    <Input
                      type="number"
                      defaultValue={instanceStats?.byok_token_limit || 50000000}
                      onBlur={(e) => handleUpdateGlobalDefaults('byok_token_limit', parseInt(e.target.value) || 50000000)}
                      className="bg-bg-card h-8 text-xs font-mono"
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 5: Analytics & Cost Management */}
        <TabsContent value="analytics" className="space-y-5 pt-2">
          {/* Analytics Summary */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <Card className="bg-bg-card border-border-button p-4">
              <div className="text-xs text-text-secondary">Total Requests</div>
              <div className="text-xl font-bold text-text-primary mt-1">
                {(analytics?.summary?.total_requests || 0).toLocaleString()}
              </div>
            </Card>
            <Card className="bg-bg-card border-border-button p-4">
              <div className="text-xs text-text-secondary">Total Tokens</div>
              <div className="text-xl font-bold text-text-primary mt-1">
                {(analytics?.summary?.total_tokens || 0).toLocaleString()}
              </div>
            </Card>
            <Card className="bg-bg-card border-border-button p-4">
              <div className="text-xs text-text-secondary">Input Tokens</div>
              <div className="text-xl font-bold text-blue-500 mt-1">
                {(analytics?.summary?.total_input_tokens || 0).toLocaleString()}
              </div>
            </Card>
            <Card className="bg-bg-card border-border-button p-4">
              <div className="text-xs text-text-secondary">Output Tokens</div>
              <div className="text-xl font-bold text-purple-500 mt-1">
                {(analytics?.summary?.total_output_tokens || 0).toLocaleString()}
              </div>
            </Card>
            <Card className="bg-bg-card border-border-button p-4">
              <div className="text-xs text-text-secondary">Estimated AI Cost</div>
              <div className="text-xl font-bold text-emerald-500 mt-1">
                ${(analytics?.summary?.total_cost || 0).toFixed(4)}
              </div>
            </Card>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Cost by Subscription */}
            <Card className="bg-bg-card border-border-button">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold">Usage by Subscription Plan</CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <table className="w-full text-xs text-left">
                  <thead className="bg-bg-base text-text-secondary border-b border-border-button">
                    <tr>
                      <th className="p-2">Plan</th>
                      <th className="p-2 text-right">Requests</th>
                      <th className="p-2 text-right">Tokens</th>
                      <th className="p-2 text-right">Cost ($)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-button">
                    {(analytics?.by_subscription || []).map((sub) => (
                      <tr key={sub.subscription_id}>
                        <td className="p-2 font-bold uppercase">{sub.subscription_id}</td>
                        <td className="p-2 text-right font-mono">{sub.requests.toLocaleString()}</td>
                        <td className="p-2 text-right font-mono">{sub.tokens.toLocaleString()}</td>
                        <td className="p-2 text-right font-mono text-emerald-500">${sub.cost.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>

            {/* Cost by Model */}
            <Card className="bg-bg-card border-border-button">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold">Top Models by Consumption</CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <table className="w-full text-xs text-left">
                  <thead className="bg-bg-base text-text-secondary border-b border-border-button">
                    <tr>
                      <th className="p-2">Model</th>
                      <th className="p-2 text-right">Tokens</th>
                      <th className="p-2 text-right">Cost ($)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-button">
                    {(analytics?.by_model || []).slice(0, 5).map((m) => (
                      <tr key={m.model_id}>
                        <td className="p-2 font-medium">{m.model_id}</td>
                        <td className="p-2 text-right font-mono">{m.total_tokens.toLocaleString()}</td>
                        <td className="p-2 text-right font-mono text-emerald-500">${m.cost.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          </div>

          {/* Top Users Table */}
          <Card className="bg-bg-card border-border-button">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Top Consuming Users</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="border border-border-button rounded-lg overflow-hidden">
                <table className="w-full text-xs text-left">
                  <thead className="bg-bg-base text-text-secondary border-b border-border-button">
                    <tr>
                      <th className="p-2.5">User</th>
                      <th className="p-2.5">Plan</th>
                      <th className="p-2.5 text-right">Requests</th>
                      <th className="p-2.5 text-right">Tokens</th>
                      <th className="p-2.5 text-right">Estimated Cost ($)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-button">
                    {(analytics?.top_users || []).map((u) => (
                      <tr key={u.user_id} className="hover:bg-bg-base/40">
                        <td className="p-2.5">
                          <div className="font-semibold text-text-primary">{u.nickname || u.email || u.user_id}</div>
                          <div className="text-[10px] text-text-secondary font-mono">{u.user_id}</div>
                        </td>
                        <td className="p-2.5 uppercase font-bold text-[10px]">{u.subscription_id}</td>
                        <td className="p-2.5 text-right font-mono">{u.requests.toLocaleString()}</td>
                        <td className="p-2.5 text-right font-mono">{u.tokens.toLocaleString()}</td>
                        <td className="p-2.5 text-right font-mono text-emerald-500">${u.cost.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 6: Audit Logs */}
        <TabsContent value="audit" className="space-y-4 pt-2">
          <Card className="bg-bg-card border-border-button">
            <CardHeader className="pb-3">
              <div className="flex justify-between items-center">
                <div>
                  <CardTitle className="text-base font-semibold flex items-center gap-2">
                    <Shield className="size-4 text-accent-primary" /> AI Infrastructure Audit Logs ({auditTotal || auditLogs.length})
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Complete immutable log of administrative configuration changes. API keys and credentials are automatically sanitized.
                  </CardDescription>
                </div>
                <Button size="xs" variant="outline" onClick={fetchAuditLogs}>
                  <RefreshCw className="size-3.5 mr-1" /> Refresh Logs
                </Button>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="border border-border-button rounded-lg overflow-hidden">
                <table className="w-full text-xs text-left">
                  <thead className="bg-bg-base text-text-secondary border-b border-border-button">
                    <tr>
                      <th className="p-3">Timestamp</th>
                      <th className="p-3">Administrator</th>
                      <th className="p-3">Action</th>
                      <th className="p-3">Target</th>
                      <th className="p-3">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-button">
                    {auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-bg-base/40">
                        <td className="p-3 font-mono text-[11px] text-text-secondary whitespace-nowrap">
                          {log.create_time ? new Date(log.create_time * 1000).toLocaleString() : '-'}
                        </td>
                        <td className="p-3">
                          <div className="font-semibold text-text-primary">{log.user_email || log.user_id}</div>
                        </td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-accent-primary/10 text-accent-primary border border-accent-primary/20">
                            {log.action}
                          </span>
                        </td>
                        <td className="p-3 font-mono text-text-secondary">
                          {log.target_type}: {log.target_id}
                        </td>
                        <td className="p-3 font-mono text-[11px] max-w-md truncate text-text-secondary">
                          {JSON.stringify(log.details_parsed)}
                        </td>
                      </tr>
                    ))}
                    {auditLogs.length === 0 && (
                      <tr>
                        <td colSpan={5} className="p-8 text-center text-text-secondary">
                          No audit logs recorded yet.
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

      {/* Provider Add/Edit Modal */}
      <Dialog open={isProviderModalOpen} onOpenChange={setIsProviderModalOpen}>
        <DialogContent className="sm:max-w-md bg-bg-card border-border-button">
          <DialogHeader>
            <DialogTitle className="text-base font-bold">
              {editingProvider.id ? 'Edit Global Provider' : 'Add Global AI Provider'}
            </DialogTitle>
            <DialogDescription className="text-xs text-text-secondary">
              Configure provider credentials for the single Global RAGFlow Instance.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-text-secondary">Provider Preset</label>
              <Select
                value={editingProvider.provider_name || 'OpenAI'}
                onValueChange={(val) => {
                  const preset = providerOptions.find((p) => p.name === val);
                  setEditingProvider({
                    ...editingProvider,
                    provider_name: val,
                    base_url: preset?.baseUrl || editingProvider.base_url,
                  });
                }}
              >
                <SelectTrigger className="bg-bg-base border-border-button text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="max-h-60 overflow-y-auto">
                  {providerOptions.map((p) => (
                    <SelectItem key={p.name} value={p.name}>
                      {p.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-text-secondary">Base URL</label>
              <Input
                value={editingProvider.base_url || ''}
                onChange={(e) => setEditingProvider({ ...editingProvider, base_url: e.target.value })}
                placeholder="https://api.openai.com/v1"
                className="bg-bg-base border-border-button text-xs font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-text-secondary">API Key</label>
              <Input
                type="password"
                value={editingProvider.api_key || ''}
                onChange={(e) => setEditingProvider({ ...editingProvider, api_key: e.target.value })}
                placeholder={editingProvider.id ? 'Leave blank to keep existing key' : 'Enter secret API key'}
                className="bg-bg-base border-border-button text-xs font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-text-secondary">Organization ID (Optional)</label>
              <Input
                value={editingProvider.organization || ''}
                onChange={(e) => setEditingProvider({ ...editingProvider, organization: e.target.value })}
                placeholder="org-..."
                className="bg-bg-base border-border-button text-xs font-mono"
              />
            </div>

            {/* Verification Results Panel */}
            {verifyResult && (
              <div
                className={`p-3 rounded-lg border text-xs space-y-2 ${
                  verifyResult.success
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                    : 'bg-red-500/10 border-red-500/30 text-red-600 dark:text-red-400'
                }`}
              >
                <div className="flex items-center gap-1.5 font-semibold">
                  {verifyResult.success ? <CheckCircle2 className="size-4 shrink-0" /> : <AlertCircle className="size-4 shrink-0" />}
                  <span>{verifyResult.message}</span>
                </div>
                {verifyResult.success && verifyResult.available_models && verifyResult.available_models.length > 0 && (
                  <div className="pt-1 border-t border-emerald-500/20">
                    <div className="text-[11px] font-medium mb-1">
                      Discovered & Connected Models ({verifyResult.count}):
                    </div>
                    <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                      {verifyResult.available_models.map((m: any) => (
                        <span
                          key={m.model_name}
                          className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 text-[10px] font-mono"
                        >
                          {m.model_name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <DialogFooter className="flex items-center justify-between sm:justify-between w-full">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={verifyingProvider || !editingProvider.api_key}
              onClick={handleVerifyProvider}
              className="flex items-center gap-1.5 text-xs"
            >
              {verifyingProvider ? <RefreshCw className="size-3.5 animate-spin" /> : <Zap className="size-3.5 text-amber-500" />}
              {verifyingProvider ? 'Verifying...' : 'Test Connection'}
            </Button>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setIsProviderModalOpen(false)}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleSaveProvider}>
                Save Provider
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Model Add/Edit Modal */}
      <Dialog open={isModelModalOpen} onOpenChange={setIsModelModalOpen}>
        <DialogContent className="sm:max-w-lg bg-bg-card border-border-button">
          <DialogHeader>
            <DialogTitle className="text-base font-bold">
              {editingModel.id ? 'Edit Platform Model' : 'Add Platform AI Model'}
            </DialogTitle>
            <DialogDescription className="text-xs text-text-secondary">
              Configure model parameters, pricing, and subscription access.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-text-secondary">Provider</label>
                <Select
                  value={editingModel.provider || 'OpenAI'}
                  onValueChange={(val) => setEditingModel({ ...editingModel, provider: val })}
                >
                  <SelectTrigger className="bg-bg-base border-border-button text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {providers.map((p) => (
                      <SelectItem key={p.provider_name} value={p.provider_name}>
                        {p.provider_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-text-secondary">Model Type</label>
                <Select
                  value={editingModel.model_type || 'CHAT'}
                  onValueChange={(val: any) => setEditingModel({ ...editingModel, model_type: val })}
                >
                  <SelectTrigger className="bg-bg-base border-border-button text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="CHAT">CHAT</SelectItem>
                    <SelectItem value="EMBEDDING">EMBEDDING</SelectItem>
                    <SelectItem value="RERANK">RERANK</SelectItem>
                    <SelectItem value="IMAGE2TEXT">IMAGE2TEXT</SelectItem>
                    <SelectItem value="TTS">TTS</SelectItem>
                    <SelectItem value="SPEECH2TEXT">SPEECH2TEXT</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-text-secondary">Model Identifier / Name</label>
              <Input
                value={editingModel.model_name || ''}
                onChange={(e) => setEditingModel({ ...editingModel, model_name: e.target.value })}
                placeholder="gpt-4o, claude-3-5-sonnet-20241022, deepseek-chat..."
                className="bg-bg-base border-border-button text-xs font-mono"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-text-secondary">Input Token Price ($ / 1M)</label>
                <Input
                  type="number"
                  step="0.01"
                  value={editingModel.input_token_price || 0}
                  onChange={(e) => setEditingModel({ ...editingModel, input_token_price: parseFloat(e.target.value) || 0 })}
                  className="bg-bg-base border-border-button text-xs font-mono"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-text-secondary">Output Token Price ($ / 1M)</label>
                <Input
                  type="number"
                  step="0.01"
                  value={editingModel.output_token_price || 0}
                  onChange={(e) => setEditingModel({ ...editingModel, output_token_price: parseFloat(e.target.value) || 0 })}
                  className="bg-bg-base border-border-button text-xs font-mono"
                />
              </div>
            </div>

            {/* Allowed Subscription Plans */}
            <div className="space-y-2 pt-2 border-t border-border-button">
              <label className="text-xs font-medium text-text-secondary">Authorized Subscription Plans</label>
              <div className="flex gap-4">
                {['free', 'plus', 'pro'].map((plan) => {
                  const currentPlans = editingModel.allowed_plans || [];
                  const isChecked = currentPlans.includes(plan);
                  return (
                    <label key={plan} className="flex items-center gap-2 cursor-pointer text-xs font-bold uppercase">
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setEditingModel({ ...editingModel, allowed_plans: [...currentPlans, plan] });
                          } else {
                            setEditingModel({ ...editingModel, allowed_plans: currentPlans.filter((p) => p !== plan) });
                          }
                        }}
                        className="rounded border-border-button text-accent-primary"
                      />
                      {plan}
                    </label>
                  );
                })}
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setIsModelModalOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleSaveModel}>
              Save Model
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Replace Key Modal */}
      <Dialog open={isReplaceKeyModalOpen} onOpenChange={setIsReplaceKeyModalOpen}>
        <DialogContent className="sm:max-w-md bg-bg-card border-border-button shadow-lg">
          <DialogHeader>
            <DialogTitle className="text-base font-bold flex items-center gap-2">
              <Key className="size-4 text-accent-primary" /> Replace API Key: {replaceTargetProvider?.provider_name}
            </DialogTitle>
            <DialogDescription className="text-xs text-text-secondary">
              Update credentials for this provider. All models previously cascaded to disabled will be automatically reactivated.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3.5 py-2 text-xs">
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400">
              <div className="font-semibold flex items-center gap-1.5">
                <CheckCircle2 className="size-4 shrink-0" /> Auto-Reactivation Guarantee
              </div>
              <p className="text-[11px] mt-1 text-text-secondary">
                Entering a new valid key restores the provider to Active and un-disables its models in the system.
              </p>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-text-secondary">New Secret API Key</label>
              <div className="relative">
                <Input
                  type={showReplaceKey ? 'text' : 'password'}
                  value={newApiKeyInput}
                  onChange={(e) => setNewApiKeyInput(e.target.value)}
                  placeholder="sk-..."
                  className="bg-bg-base border-border-button text-xs font-mono pr-8"
                />
                <button
                  type="button"
                  onClick={() => setShowReplaceKey(!showReplaceKey)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary"
                >
                  {showReplaceKey ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
                </button>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-text-secondary">Base URL (Optional Override)</label>
              <Input
                value={newBaseUrlInput}
                onChange={(e) => setNewBaseUrlInput(e.target.value)}
                placeholder="https://api.openai.com/v1"
                className="bg-bg-base border-border-button text-xs font-mono"
              />
            </div>
          </div>

          <DialogFooter className="flex items-center justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setIsReplaceKeyModalOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" disabled={replacingKey || !newApiKeyInput.trim()} onClick={handleExecuteReplaceKey}>
              {replacingKey ? <RefreshCw className="size-3.5 animate-spin mr-1.5" /> : <Save className="size-3.5 mr-1.5" />}
              {replacingKey ? 'Saving...' : 'Replace & Reactivate'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
