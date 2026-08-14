import React, { useEffect, useState } from 'react';
import {
  Bot,
  CheckCircle2,
  Cpu,
  Layers,
  Plus,
  RefreshCw,
  Save,
  Shield,
  Trash2,
  UserCheck,
  Zap,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import message from '@/components/ui/message';
import { Modal } from '@/components/ui/modal/modal';
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
  const [activeTab, setActiveTab] = useState('plans');
  const [loading, setLoading] = useState(false);

  // Data states
  const [plans, setPlans] = useState<SubscriptionPlanItem[]>([]);
  const [models, setModels] = useState<AIModelItem[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string>('plus');
  const [policies, setPolicies] = useState<SubscriptionAIPolicyItem[]>([]);
  
  // Model Modal
  const [isModelModalOpen, setIsModelModalOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<Partial<AIModelItem>>({
    provider: 'OpenAI',
    model_name: '',
    model_type: 'CHAT',
    base_url: 'https://api.openai.com/v1',
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

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const res = await getAdminPlans();
      const data = res?.data || (res as any)?.data?.data;
      if (data) {
        setPlans(Array.isArray(data) ? data : []);
      }
    } catch (e: any) {
      message.error(e.message || 'Failed to fetch subscription plans');
    } finally {
      setLoading(false);
    }
  };

  const fetchModels = async () => {
    try {
      const res = await getAdminModels();
      const data = res?.data || (res as any)?.data?.data;
      if (data) {
        setModels(Array.isArray(data) ? data : []);
      }
    } catch (e: any) {
      message.error(e.message || 'Failed to fetch AI models');
    }
  };

  const fetchPolicies = async (planId: string) => {
    try {
      const res = await getAdminPolicies(planId);
      const data = res?.data || (res as any)?.data?.data;
      if (data) {
        setPolicies(Array.isArray(data) ? data : []);
      }
    } catch (e: any) {
      message.error(e.message || 'Failed to fetch policies');
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
      message.success(`Policies for plan '${selectedPlanId.toUpperCase()}' saved.`);
      fetchPolicies(selectedPlanId);
    } catch (e: any) {
      message.error(e.message || 'Failed to save policies.');
    }
  };

  // User Limit Override Handlers
  const handleSearchUserLimit = async () => {
    if (!targetUserId.trim()) {
      message.error('Please enter a User ID.');
      return;
    }
    try {
      setSearchingUser(true);
      const res = await getAdminUserLimit(targetUserId.trim());
      const data = res?.data || (res as any)?.data?.data;
      if (data) {
        setUserLimitValue(data.monthly_token_limit || 0);
        setUserLimitEnabled(data.enabled ?? true);
        message.success('User limit configuration retrieved.');
      }
    } catch (e: any) {
      message.error(e.message || 'Failed to get user limit.');
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
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Page Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2 text-foreground">
            <Bot className="size-7 text-primary" />
            AI Models & Subscription Policies
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage database-driven subscription tiers, AI provider models, per-model access rules, and token limits.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => { fetchPlans(); fetchModels(); }} className="gap-2">
          <RefreshCw className="size-4" />
          Refresh Catalog
        </Button>
      </div>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid grid-cols-4 max-w-2xl bg-muted/60 p-1 rounded-xl">
          <TabsTrigger value="plans" className="gap-2">
            <Zap className="size-4" />
            Subscription Plans
          </TabsTrigger>
          <TabsTrigger value="models" className="gap-2">
            <Cpu className="size-4" />
            Global AI Models
          </TabsTrigger>
          <TabsTrigger value="policies" className="gap-2">
            <Shield className="size-4" />
            Policy Matrix
          </TabsTrigger>
          <TabsTrigger value="user-overrides" className="gap-2">
            <UserCheck className="size-4" />
            User Quota Overrides
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: SUBSCRIPTION PLANS */}
        <TabsContent value="plans" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {plans.map((plan) => (
              <Card key={plan.id} className="relative border-border/80 shadow-sm hover:shadow-md transition-all">
                <CardHeader className="border-b border-border/40 bg-muted/20 pb-4">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-xl font-bold capitalize flex items-center gap-2">
                      <span className="p-2 rounded-lg bg-primary/10 text-primary">
                        {plan.id === 'pro' ? <Zap className="size-5" /> : plan.id === 'plus' ? <Layers className="size-5" /> : <Bot className="size-5" />}
                      </span>
                      {plan.name} Plan
                    </CardTitle>
                    <span className="text-xs font-mono uppercase px-2 py-0.5 rounded bg-primary/10 text-primary font-semibold">
                      ID: {plan.id}
                    </span>
                  </div>
                  <CardDescription className="text-xs mt-1">
                    Configure limits and features for {plan.name} subscribers.
                  </CardDescription>
                </CardHeader>

                <CardContent className="p-5 space-y-4 text-sm">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-foreground">Monthly Token Limit</label>
                    <Input
                      type="number"
                      value={plan.monthly_token_limit}
                      onChange={(e) => handlePlanChange(plan.id, 'monthly_token_limit', Number(e.target.value))}
                      className="font-mono"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-foreground">Limit Mode</label>
                    <Select
                      value={plan.limit_mode}
                      onValueChange={(val) => handlePlanChange(plan.id, 'limit_mode', val)}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="shared">Shared (Total Token Pool)</SelectItem>
                        <SelectItem value="per_model">Per-Model Limits Supported</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-1">
                    <div>
                      <label className="text-[11px] font-semibold text-muted-foreground">Storage (GB)</label>
                      <Input
                        type="number"
                        value={plan.max_storage_gb}
                        onChange={(e) => handlePlanChange(plan.id, 'max_storage_gb', Number(e.target.value))}
                        className="text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-muted-foreground">Max Datasets</label>
                      <Input
                        type="number"
                        value={plan.max_datasets}
                        onChange={(e) => handlePlanChange(plan.id, 'max_datasets', Number(e.target.value))}
                        className="text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold text-muted-foreground">Max Agents</label>
                      <Input
                        type="number"
                        value={plan.max_agents}
                        onChange={(e) => handlePlanChange(plan.id, 'max_agents', Number(e.target.value))}
                        className="text-xs"
                      />
                    </div>
                  </div>

                  <div className="pt-2 space-y-2.5 border-t border-border/60">
                    <div className="flex items-center justify-between">
                      <span className="text-xs">Allow Custom Models</span>
                      <Switch
                        checked={plan.allow_custom_models}
                        onCheckedChange={(checked) => handlePlanChange(plan.id, 'allow_custom_models', checked)}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs">Allow Custom Providers</span>
                      <Switch
                        checked={plan.allow_custom_providers}
                        onCheckedChange={(checked) => handlePlanChange(plan.id, 'allow_custom_providers', checked)}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs">Allow Custom Endpoints</span>
                      <Switch
                        checked={plan.allow_custom_endpoints}
                        onCheckedChange={(checked) => handlePlanChange(plan.id, 'allow_custom_endpoints', checked)}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs">Private Server Connections</span>
                      <Switch
                        checked={plan.allow_private_servers}
                        onCheckedChange={(checked) => handlePlanChange(plan.id, 'allow_private_servers', checked)}
                      />
                    </div>
                  </div>

                  <Button
                    onClick={() => handleSavePlan(plan)}
                    className="w-full mt-4 gap-2"
                  >
                    <Save className="size-4" />
                    Save {plan.name} Plan
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* TAB 2: GLOBAL AI MODELS */}
        <TabsContent value="models" className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-foreground">Registered System AI Models</h3>
            <Button onClick={() => handleOpenModelModal()} className="gap-2">
              <Plus className="size-4" />
              Register AI Model
            </Button>
          </div>

          <div className="border border-border rounded-xl overflow-hidden bg-card shadow-sm">
            <table className="w-full text-left text-sm border-collapse">
              <thead className="bg-muted/50 text-xs font-semibold uppercase text-muted-foreground border-b border-border">
                <tr>
                  <th className="p-3.5">Provider</th>
                  <th className="p-3.5">Model ID</th>
                  <th className="p-3.5">Model Name</th>
                  <th className="p-3.5">Type</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {models.map((m) => (
                  <tr key={m.id} className="hover:bg-muted/30 transition-colors">
                    <td className="p-3.5 font-medium">{m.provider}</td>
                    <td className="p-3.5 font-mono text-xs text-primary">{m.id}</td>
                    <td className="p-3.5 font-mono text-xs">{m.model_name}</td>
                    <td className="p-3.5">
                      <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-secondary text-secondary-foreground">
                        {m.model_type}
                      </span>
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
                ))}
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
                {['free', 'plus', 'pro'].map((pid) => (
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

      {/* Model Modal */}
      <Modal open={isModelModalOpen} onOpenChange={setIsModelModalOpen}>
        <div className="p-6 space-y-4 max-w-lg bg-background rounded-xl border border-border">
          <h3 className="text-lg font-bold">Register / Edit Global AI Model</h3>

          <div className="space-y-3 text-sm">
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Provider</label>
              <Input
                value={editingModel.provider || ''}
                onChange={(e) => setEditingModel({ ...editingModel, provider: e.target.value })}
                placeholder="e.g. OpenAI, DeepSeek, Google"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Model Name</label>
              <Input
                value={editingModel.model_name || ''}
                onChange={(e) => setEditingModel({ ...editingModel, model_name: e.target.value })}
                placeholder="e.g. gpt-4o, deepseek-chat"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Model Type</label>
              <Select
                value={editingModel.model_type || 'CHAT'}
                onValueChange={(val: any) => setEditingModel({ ...editingModel, model_type: val })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CHAT">CHAT / LLM</SelectItem>
                  <SelectItem value="EMBEDDING">EMBEDDING</SelectItem>
                  <SelectItem value="RERANK">RERANKER</SelectItem>
                  <SelectItem value="IMAGE2TEXT">VISION / OCR</SelectItem>
                  <SelectItem value="SPEECH2TEXT">STT (Speech-to-Text)</SelectItem>
                  <SelectItem value="TTS">TTS (Text-to-Speech)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground">Base URL (Optional)</label>
              <Input
                value={editingModel.base_url || ''}
                onChange={(e) => setEditingModel({ ...editingModel, base_url: e.target.value })}
                placeholder="https://api.openai.com/v1"
              />
            </div>
            <div className="flex items-center justify-between pt-2">
              <span className="text-xs font-medium">Globally Enabled</span>
              <Switch
                checked={editingModel.enabled ?? true}
                onCheckedChange={(val) => setEditingModel({ ...editingModel, enabled: val })}
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-border">
            <Button variant="ghost" onClick={() => setIsModelModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveModel}>
              Save Model
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
