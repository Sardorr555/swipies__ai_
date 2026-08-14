import React, { useEffect, useRef, useState } from 'react';
import {
  Bot,
  CheckCircle2,
  Cpu,
  Eye,
  EyeOff,
  Layers,
  Plus,
  RefreshCw,
  Save,
  Shield,
  Trash2,
  UserCheck,
  X,
  Zap,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import message from '@/components/ui/message';
import * as Dialog from '@radix-ui/react-dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import {
  AIModelItem,
  deleteAdminModel,
  getAdminModels,
  getAdminPlans,
  getAdminPolicies,
  getAdminUserLimit,
  saveAdminModel,
  setAdminUserLimit,
  SubscriptionAIPolicyItem,
  SubscriptionPlanItem,
  updateAdminPlan,
  updateAdminPolicies,
} from '@/services/ai-management-service';

export default function AIManagementPage() {
  const [activeTab, setActiveTab] = useState('models');
  const [loading, setLoading] = useState(false);

  // Data states
  const [plans, setPlans] = useState<SubscriptionPlanItem[]>([]);
  const [models, setModels] = useState<AIModelItem[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string>('plus');
  const [policies, setPolicies] = useState<SubscriptionAIPolicyItem[]>([]);
  
  // Model Modal
  const [isModelModalOpen, setIsModelModalOpen] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [editingModel, setEditingModel] = useState<Partial<AIModelItem>>({
    provider: 'OpenAI',
    model_name: '',
    model_type: 'CHAT',
    base_url: 'https://api.openai.com/v1',
    api_key: '',
    enabled: true,
    is_global: true,
  });

  // User Limit Override
  const [targetUserId, setTargetUserId] = useState('');
  const [userLimitValue, setUserLimitValue] = useState<number>(0);
  const [userLimitEnabled, setUserLimitEnabled] = useState(true);
  const [searchingUser, setSearchingUser] = useState(false);

  useEffect(() => {
    fetchPlans();
    fetchModels();
  }, []);

  useEffect(() => {
    if (selectedPlanId) {
      fetchPolicies(selectedPlanId);
    }
  }, [selectedPlanId]);

  const extractArray = (res: any): any[] => {
    if (!res) return [];
    if (Array.isArray(res)) return res;
    if (Array.isArray(res?.data)) return res.data;
    if (Array.isArray(res?.data?.data)) return res.data.data;
    return [];
  };

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const res = await getAdminPlans();
      setPlans(extractArray(res));
    } catch (e: any) {
      message.error(e?.message || 'Failed to fetch subscription plans');
    } finally {
      setLoading(false);
    }
  };

  const fetchModels = async () => {
    try {
      const res = await getAdminModels();
      setModels(extractArray(res));
    } catch (e: any) {
      message.error(e?.message || 'Failed to fetch AI models');
    }
  };

  const fetchPolicies = async (planId: string) => {
    try {
      const res = await getAdminPolicies(planId);
      setPolicies(extractArray(res));
    } catch (e: any) {
      message.error(e?.message || 'Failed to fetch policies');
    }
  };

  // Plan handlers
  const handlePlanChange = (planId: string, key: keyof SubscriptionPlanItem, value: any) => {
    setPlans((prev) =>
      prev.map((p) => (p.id === planId ? { ...p, [key]: value } : p))
    );
  };

  const handleSavePlan = async (plan: SubscriptionPlanItem) => {
    try {
      await updateAdminPlan(plan.id, plan);
      message.success(`Plan ${plan.name} updated successfully.`);
      fetchPlans();
    } catch (e: any) {
      message.error(e.message || 'Failed to update plan.');
    }
  };

  // Model handlers
  const handleOpenModelModal = (model?: AIModelItem) => {
    if (model) {
      setEditingModel(model);
    } else {
      setEditingModel({
        provider: 'OpenAI',
        model_name: '',
        model_type: 'CHAT',
        base_url: 'https://api.openai.com/v1',
        enabled: true,
        is_global: true,
      });
    }
    setIsModelModalOpen(true);
  };

  const handleSaveModel = async () => {
    if (!editingModel.provider || !editingModel.model_name) {
      message.error('Provider and Model Name are required.');
      return;
    }
    try {
      await saveAdminModel(editingModel);
      message.success('AI Model saved successfully.');
      setIsModelModalOpen(false);
      fetchModels();
    } catch (e: any) {
      message.error(e.message || 'Failed to save model.');
    }
  };

  const handleDeleteModel = async (modelId: string) => {
    try {
      await deleteAdminModel(modelId);
      message.success('Model deleted.');
      fetchModels();
    } catch (e: any) {
      message.error(e.message || 'Failed to delete model.');
    }
  };

  // Policy handlers
  const handlePolicyToggle = (modelId: string, enabled: boolean) => {
    setPolicies((prev) => {
      const existing = prev.find((p) => p.model_id === modelId);
      if (existing) {
        return prev.map((p) => (p.model_id === modelId ? { ...p, enabled } : p));
      } else {
        return [
          ...prev,
          {
            id: `${selectedPlanId}_${modelId}`,
            plan_id: selectedPlanId,
            model_id: modelId,
            model_token_limit: 0,
            is_default_llm: false,
            is_default_embd: false,
            enabled,
          },
        ];
      }
    });
  };

  const handlePolicyLimitChange = (modelId: string, limit: number) => {
    setPolicies((prev) =>
      prev.map((p) => (p.model_id === modelId ? { ...p, model_token_limit: limit } : p))
    );
  };

  const handleSavePolicies = async () => {
    try {
      await updateAdminPolicies(selectedPlanId, policies);
      message.success(`Policies for plan ${selectedPlanId.toUpperCase()} updated.`);
      fetchPolicies(selectedPlanId);
    } catch (e: any) {
      message.error(e.message || 'Failed to update policies.');
    }
  };

  // User Limit Override handlers
  const handleSearchUserLimit = async () => {
    if (!targetUserId.trim()) return;
    try {
      setSearchingUser(true);
      const res = await getAdminUserLimit(targetUserId.trim());
      const data = extractArray(res)[0] || (res as any)?.data || res;
      if (data) {
        setUserLimitValue(data.monthly_token_limit || 0);
        setUserLimitEnabled(data.enabled ?? true);
      }
    } catch (e: any) {
      message.error(e.message || 'User override limit not found.');
    } finally {
      setSearchingUser(false);
    }
  };

  const handleSaveUserLimit = async () => {
    if (!targetUserId.trim()) {
      message.error('Please enter a User ID.');
      return;
    }
    try {
      await setAdminUserLimit(targetUserId.trim(), Number(userLimitValue), userLimitEnabled);
      message.success(`Token limit override saved for user ${targetUserId}.`);
    } catch (e: any) {
      message.error(e.message || 'Failed to set user limit.');
    }
  };

  return (
    <div className="h-full w-full overflow-y-auto overflow-x-hidden p-6 flex-1 min-h-0 space-y-6">
      <div className="max-w-7xl mx-auto space-y-6 pb-16">
      {/* Page Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2 text-foreground">
            <Bot className="size-7 text-primary" />
            AI Models & Subscription Policies
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage global AI providers, model credentials, plan access rules, and token quota overrides.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => { fetchPlans(); fetchModels(); }} className="gap-2">
          <RefreshCw className="size-4" />
          Refresh Catalog
        </Button>
      </div>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid grid-cols-3 max-w-xl bg-muted/60 p-1 rounded-xl">
          <TabsTrigger value="models" className="gap-2">
            <Cpu className="size-4" />
            AI Models & Providers
          </TabsTrigger>
          <TabsTrigger value="policies" className="gap-2">
            <Shield className="size-4" />
            Subscription AI Policies
          </TabsTrigger>
          <TabsTrigger value="user-overrides" className="gap-2">
            <UserCheck className="size-4" />
            User Quota Overrides
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: GLOBAL AI MODELS */}
        <TabsContent value="models" className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-foreground">Registered System AI Models</h3>
              <p className="text-xs text-muted-foreground">Manage global AI providers, model endpoints, and system API keys.</p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={fetchModels} className="gap-2">
                <RefreshCw className="size-3.5" />
                Refresh
              </Button>
              <Button onClick={() => handleOpenModelModal()} className="gap-2">
                <Plus className="size-4" />
                Register AI Model
              </Button>
            </div>
          </div>

          <div className="border border-border rounded-xl overflow-hidden bg-card shadow-sm">
            <table className="w-full text-left text-sm border-collapse">
              <thead className="bg-muted/50 text-xs font-semibold uppercase text-muted-foreground border-b border-border">
                <tr>
                  <th className="p-3.5">Provider</th>
                  <th className="p-3.5">Model ID</th>
                  <th className="p-3.5">Model Name</th>
                  <th className="p-3.5">Type</th>
                  <th className="p-3.5">API Key</th>
                  <th className="p-3.5">Base URL</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {models.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-muted-foreground">
                      No models registered yet. Click "Register AI Model" to add your first AI provider.
                    </td>
                  </tr>
                ) : (
                  models.map((m) => (
                    <tr key={m.id} className="hover:bg-muted/30 transition-colors">
                      <td className="p-3.5 font-medium">{m.provider}</td>
                      <td className="p-3.5 font-mono text-xs text-primary">{m.id}</td>
                      <td className="p-3.5 font-mono text-xs">{m.model_name}</td>
                      <td className="p-3.5">
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-secondary text-secondary-foreground">
                          {m.model_type}
                        </span>
                      </td>
                      <td className="p-3.5 font-mono text-xs">
                        {m.api_key ? (
                          <span className="inline-flex items-center gap-1 text-emerald-600 font-semibold bg-emerald-500/10 px-2 py-0.5 rounded">
                            <CheckCircle2 className="size-3" /> Configured
                          </span>
                        ) : (
                          <span className="text-muted-foreground text-[11px]">Not Set</span>
                        )}
                      </td>
                      <td className="p-3.5 font-mono text-xs max-w-[200px] truncate text-muted-foreground">
                        {m.base_url || '-'}
                      </td>
                      <td className="p-3.5">
                        {m.enabled ? (
                          <span className="inline-flex items-center gap-1 text-xs text-emerald-600 font-medium">
                            <CheckCircle2 className="size-3.5" /> Enabled
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">Disabled</span>
                        )}
                      </td>
                      <td className="p-3.5 text-right space-x-2">
                        <Button variant="ghost" size="sm" onClick={() => handleOpenModelModal(m)}>
                          Edit
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDeleteModel(m.id)} className="text-destructive hover:text-destructive">
                          <Trash2 className="size-4" />
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </TabsContent>

        {/* TAB 3: POLICY MATRIX */}
        <TabsContent value="policies" className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-4">
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold">Select Subscription Plan:</span>
              <div className="flex gap-2">
                {['free', 'plus', 'pro', 'enterprise'].map((pid) => (
                  <Button
                    key={pid}
                    variant={selectedPlanId === pid ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSelectedPlanId(pid)}
                    className="capitalize"
                  >
                    {pid}
                  </Button>
                ))}
              </div>
            </div>

            <Button onClick={handleSavePolicies} className="gap-2">
              <Save className="size-4" />
              Save {selectedPlanId.toUpperCase()} Policies
            </Button>
          </div>

          <div className="border border-border rounded-xl overflow-hidden bg-card shadow-sm">
            <table className="w-full text-left text-sm border-collapse">
              <thead className="bg-muted/50 text-xs font-semibold uppercase text-muted-foreground border-b border-border">
                <tr>
                  <th className="p-3.5">Allowed</th>
                  <th className="p-3.5">Provider / Model</th>
                  <th className="p-3.5">Model Type</th>
                  <th className="p-3.5">Model Token Limit (0 = Shared Pool)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {models.map((m) => {
                  const pol = policies.find((p) => p.model_id === m.id || p.model_id === m.model_name);
                  const isEnabled = pol ? pol.enabled : false;
                  const tokenLimit = pol ? pol.model_token_limit : 0;

                  return (
                    <tr key={m.id} className="hover:bg-muted/30 transition-colors">
                      <td className="p-3.5">
                        <Switch
                          checked={isEnabled}
                          onCheckedChange={(val) => handlePolicyToggle(m.id, val)}
                        />
                      </td>
                      <td className="p-3.5">
                        <div className="font-semibold text-sm">{m.model_name}</div>
                        <div className="text-xs text-muted-foreground font-mono">{m.provider} • {m.id}</div>
                      </td>
                      <td className="p-3.5">
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-secondary text-secondary-foreground">
                          {m.model_type}
                        </span>
                      </td>
                      <td className="p-3.5 max-w-xs">
                        <Input
                          type="number"
                          disabled={!isEnabled}
                          value={tokenLimit}
                          onChange={(e) => handlePolicyLimitChange(m.id, Number(e.target.value))}
                          placeholder="0 for plan limit"
                          className="font-mono text-xs"
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </TabsContent>

        {/* TAB 4: USER QUOTA OVERRIDES */}
        <TabsContent value="user-overrides" className="space-y-6">
          <Card className="max-w-2xl border-border shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg font-bold flex items-center gap-2">
                <UserCheck className="size-5 text-primary" />
                Custom User Monthly Token Limit Override
              </CardTitle>
              <CardDescription className="text-xs">
                Override regular subscription plan token quotas for specific user accounts (e.g. enterprise VIPs or trial users).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Enter User ID"
                  value={targetUserId}
                  onChange={(e) => setTargetUserId(e.target.value)}
                  className="font-mono"
                />
                <Button onClick={handleSearchUserLimit} disabled={searchingUser} variant="secondary">
                  Fetch Config
                </Button>
              </div>

              <div className="pt-4 border-t border-border space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">Custom Monthly Token Limit (0 = Default Plan Quota)</label>
                  <Input
                    type="number"
                    value={userLimitValue}
                    onChange={(e) => setUserLimitValue(Number(e.target.value))}
                    className="font-mono text-sm"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Enable Custom Quota Override</span>
                  <Switch
                    checked={userLimitEnabled}
                    onCheckedChange={setUserLimitEnabled}
                  />
                </div>

                <Button onClick={handleSaveUserLimit} className="w-full gap-2 mt-4">
                  <Save className="size-4" />
                  Save User Override Limit
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Model Modal — using Radix Dialog directly to avoid overlay closing on Select portal click */}
      <Dialog.Root open={isModelModalOpen} onOpenChange={setIsModelModalOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-[1000] bg-black/40 backdrop-blur-sm flex items-center justify-center p-4" />
          <Dialog.Content
            className="fixed z-[1001] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-card rounded-2xl border border-border shadow-xl p-6 space-y-5 focus:outline-none"
            onPointerDownOutside={(e) => e.preventDefault()}
            onInteractOutside={(e) => e.preventDefault()}
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <Dialog.Title className="text-lg font-bold text-foreground flex items-center gap-2">
                <Bot className="size-5 text-primary" />
                {editingModel.id ? 'Edit AI Model' : 'Register Global AI Model'}
              </Dialog.Title>
              <button
                onClick={() => setIsModelModalOpen(false)}
                className="p-1.5 rounded-lg hover:bg-muted/60 text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="size-4" />
              </button>
            </div>

            {/* Form */}
            <div className="space-y-3.5 text-sm">
              {/* Provider */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Provider</label>
                <Input
                  value={editingModel.provider || ''}
                  onChange={(e) => setEditingModel((prev) => ({ ...prev, provider: e.target.value }))}
                  placeholder="e.g. OpenAI, DeepSeek, Google, Anthropic"
                />
              </div>

              {/* Model Name */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Model Name</label>
                <Input
                  value={editingModel.model_name || ''}
                  onChange={(e) => setEditingModel((prev) => ({ ...prev, model_name: e.target.value }))}
                  placeholder="e.g. gpt-4o, deepseek-chat, claude-sonnet"
                />
              </div>

              {/* Model Type */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Model Type</label>
                <Select
                  value={editingModel.model_type || 'CHAT'}
                  onValueChange={(val) =>
                    setEditingModel((prev) => ({ ...prev, model_type: val as AIModelItem['model_type'] }))
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select model type" />
                  </SelectTrigger>
                  <SelectContent position="popper" className="z-[1100]">
                    <SelectItem value="CHAT">💬 CHAT / LLM</SelectItem>
                    <SelectItem value="EMBEDDING">🔢 EMBEDDING</SelectItem>
                    <SelectItem value="RERANK">📊 RERANKER</SelectItem>
                    <SelectItem value="IMAGE2TEXT">🖼️ VISION / OCR</SelectItem>
                    <SelectItem value="SPEECH2TEXT">🎤 STT (Speech-to-Text)</SelectItem>
                    <SelectItem value="TTS">🔊 TTS (Text-to-Speech)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Base URL */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Base URL <span className="font-normal normal-case">(optional)</span></label>
                <Input
                  value={editingModel.base_url || ''}
                  onChange={(e) => setEditingModel((prev) => ({ ...prev, base_url: e.target.value }))}
                  placeholder="https://api.openai.com/v1"
                />
              </div>

              {/* API Key */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">API Key <span className="font-normal normal-case">(optional, stored encrypted)</span></label>
                <div className="relative">
                  <Input
                    type={showApiKey ? 'text' : 'password'}
                    value={editingModel.api_key || ''}
                    onChange={(e) => setEditingModel((prev) => ({ ...prev, api_key: e.target.value }))}
                    placeholder="sk-..."
                    className="pr-10 font-mono text-xs"
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showApiKey ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                  </button>
                </div>
              </div>

              {/* Enabled Toggle */}
              <div className="flex items-center justify-between pt-1 pb-1 border-t border-border/60">
                <div>
                  <span className="text-sm font-medium">Globally Enabled</span>
                  <p className="text-xs text-muted-foreground">When disabled, this model won't be accessible by any plan.</p>
                </div>
                <Switch
                  checked={editingModel.enabled ?? true}
                  onCheckedChange={(val) => setEditingModel((prev) => ({ ...prev, enabled: val }))}
                />
              </div>
            </div>

            {/* Footer */}
            <div className="flex justify-end gap-2 pt-2 border-t border-border">
              <Button variant="ghost" onClick={() => setIsModelModalOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSaveModel} className="gap-2">
                <Save className="size-4" />
                Save Model
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  </div>
);
}
