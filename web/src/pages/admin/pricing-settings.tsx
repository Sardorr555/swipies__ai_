import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Coins,
  Gift,
  KeyRound,
  LucideLoader2,
  Mail,
  Save,
  Settings,
  ShieldCheck,
  Sliders,
} from 'lucide-react';
import { useEffect, useState } from 'react';

import Spotlight from '@/components/spotlight';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import message from '@/components/ui/message';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import { getVariables, updateVariable } from '@/services/admin-service';

export default function AdminPricingSettings() {
  const queryClient = useQueryClient();

  // Retrieve variables list from backend
  const { data: variablesRes, isLoading } = useQuery({
    queryKey: ['admin/getVariables'],
    queryFn: async () => (await getVariables()).data.data,
  });

  // State maps for local input editing
  const [pricingValues, setPricingValues] = useState({
    plusUsd: '20',
    plusUzs: '199000',
    proUsd: '40',
    proUzs: '400000',
  });

  const [oauthValues, setOauthValues] = useState({
    googleClientId: '',
    googleClientSecret: '',
    githubClientId: '',
    githubClientSecret: '',
  });

  const [planLimitValues, setPlanLimitValues] = useState({
    freeApps: '3',
    freeDatasets: '5',
    freeStorageGb: '0.5',
    freeTokens: '100000',
    freeTeam: '1',

    plusApps: '50',
    plusDatasets: '20',
    plusStorageGb: '5.0',
    plusTokens: '5000000',
    plusTeam: '5',

    proApps: '200',
    proDatasets: '50',
    proStorageGb: '15.0',
    proTokens: '20000000',
    proTeam: '15',

    enterpriseApps: '-1',
    enterpriseDatasets: '-1',
    enterpriseStorageGb: '-1',
    enterpriseTokens: '-1',
    enterpriseTeam: '-1',
  });

  const [smtpValues, setSmtpValues] = useState({
    server: '',
    port: '',
    useSsl: false,
    useTls: false,
    username: '',
    password: '',
    timeout: '10',
    defaultSender: '',
  });

  const [systemValues, setSystemValues] = useState({
    enableWhitelist: true,
    defaultRole: '',
  });

  const [referralValues, setReferralValues] = useState({
    enabled: true,
    storageGb: '1.0',
    agentsLimit: '5',
  });

  // Load backend variables into local states when queries succeed
  useEffect(() => {
    if (variablesRes && Array.isArray(variablesRes)) {
      const varsMap = new Map<string, string>();
      variablesRes.forEach((item) => {
        varsMap.set(item.name, item.value);
      });

      setPricingValues({
        plusUsd: varsMap.get('pricing.plus.usd') || '20',
        plusUzs: varsMap.get('pricing.plus.uzs') || '199000',
        proUsd: varsMap.get('pricing.pro.usd') || '40',
        proUzs: varsMap.get('pricing.pro.uzs') || '400000',
      });

      setSmtpValues({
        server: varsMap.get('mail.server') || '',
        port: varsMap.get('mail.port') || '',
        useSsl: varsMap.get('mail.use_ssl') === 'true',
        useTls: varsMap.get('mail.use_tls') === 'true',
        username: varsMap.get('mail.username') || '',
        password: varsMap.get('mail.password') || '',
        timeout: varsMap.get('mail.timeout') || '10',
        defaultSender: varsMap.get('mail.default_sender') || '',
      });

      setSystemValues({
        enableWhitelist: varsMap.get('enable_whitelist') !== 'false',
        defaultRole: varsMap.get('default_role') || '',
      });

      setPlanLimitValues({
        freeApps: varsMap.get('plan.free.apps_limit') || '3',
        freeDatasets: varsMap.get('plan.free.datasets_limit') || '5',
        freeStorageGb: varsMap.get('plan.free.storage_gb') || '0.5',
        freeTokens: varsMap.get('plan.free.token_limit') || '100000',
        freeTeam: varsMap.get('plan.free.team_limit') || '1',

        plusApps: varsMap.get('plan.plus.apps_limit') || '50',
        plusDatasets: varsMap.get('plan.plus.datasets_limit') || '20',
        plusStorageGb: varsMap.get('plan.plus.storage_gb') || '5.0',
        plusTokens: varsMap.get('plan.plus.token_limit') || '5000000',
        plusTeam: varsMap.get('plan.plus.team_limit') || '5',

        proApps: varsMap.get('plan.pro.apps_limit') || '200',
        proDatasets: varsMap.get('plan.pro.datasets_limit') || '50',
        proStorageGb: varsMap.get('plan.pro.storage_gb') || '15.0',
        proTokens: varsMap.get('plan.pro.token_limit') || '20000000',
        proTeam: varsMap.get('plan.pro.team_limit') || '15',

        enterpriseApps: varsMap.get('plan.enterprise.apps_limit') || '-1',
        enterpriseDatasets: varsMap.get('plan.enterprise.datasets_limit') || '-1',
        enterpriseStorageGb: varsMap.get('plan.enterprise.storage_gb') || '-1',
        enterpriseTokens: varsMap.get('plan.enterprise.token_limit') || '-1',
        enterpriseTeam: varsMap.get('plan.enterprise.team_limit') || '-1',
      });

      setOauthValues({
        googleClientId: varsMap.get('oauth.google.client_id') || '',
        googleClientSecret: varsMap.get('oauth.google.client_secret') || '',
        githubClientId: varsMap.get('oauth.github.client_id') || '',
        githubClientSecret: varsMap.get('oauth.github.client_secret') || '',
      });

      setReferralValues({
        enabled: varsMap.get('referral.enabled') !== 'false',
        storageGb: varsMap.get('referral.storage_gb') || '1.0',
        agentsLimit: varsMap.get('referral.agents_limit') || '5',
      });
    }
  }, [variablesRes]);

  // Mutation to save settings
  const saveVariableMutation = useMutation({
    mutationFn: async (params: { name: string; value: string }) => {
      return await updateVariable({
        var_name: params.name,
        var_value: params.value,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin/getVariables'] });
    },
  });

  const handleSaveOauth = async () => {
    try {
      await Promise.all([
        saveVariableMutation.mutateAsync({
          name: 'oauth.google.client_id',
          value: oauthValues.googleClientId,
        }),
        saveVariableMutation.mutateAsync({
          name: 'oauth.google.client_secret',
          value: oauthValues.googleClientSecret,
        }),
        saveVariableMutation.mutateAsync({
          name: 'oauth.github.client_id',
          value: oauthValues.githubClientId,
        }),
        saveVariableMutation.mutateAsync({
          name: 'oauth.github.client_secret',
          value: oauthValues.githubClientSecret,
        }),
      ]);
      message.success('OAuth credentials for Google and GitHub updated successfully!');
    } catch (e: any) {
      message.error(`Failed to update OAuth settings: ${e.message}`);
    }
  };

  const handleSavePlanLimits = async () => {
    try {
      await Promise.all([
        saveVariableMutation.mutateAsync({ name: 'plan.free.apps_limit', value: planLimitValues.freeApps }),
        saveVariableMutation.mutateAsync({ name: 'plan.free.datasets_limit', value: planLimitValues.freeDatasets }),
        saveVariableMutation.mutateAsync({ name: 'plan.free.storage_gb', value: planLimitValues.freeStorageGb }),
        saveVariableMutation.mutateAsync({ name: 'plan.free.token_limit', value: planLimitValues.freeTokens }),
        saveVariableMutation.mutateAsync({ name: 'plan.free.team_limit', value: planLimitValues.freeTeam }),

        saveVariableMutation.mutateAsync({ name: 'plan.plus.apps_limit', value: planLimitValues.plusApps }),
        saveVariableMutation.mutateAsync({ name: 'plan.plus.datasets_limit', value: planLimitValues.plusDatasets }),
        saveVariableMutation.mutateAsync({ name: 'plan.plus.storage_gb', value: planLimitValues.plusStorageGb }),
        saveVariableMutation.mutateAsync({ name: 'plan.plus.token_limit', value: planLimitValues.plusTokens }),
        saveVariableMutation.mutateAsync({ name: 'plan.plus.team_limit', value: planLimitValues.plusTeam }),

        saveVariableMutation.mutateAsync({ name: 'plan.pro.apps_limit', value: planLimitValues.proApps }),
        saveVariableMutation.mutateAsync({ name: 'plan.pro.datasets_limit', value: planLimitValues.proDatasets }),
        saveVariableMutation.mutateAsync({ name: 'plan.pro.storage_gb', value: planLimitValues.proStorageGb }),
        saveVariableMutation.mutateAsync({ name: 'plan.pro.token_limit', value: planLimitValues.proTokens }),
        saveVariableMutation.mutateAsync({ name: 'plan.pro.team_limit', value: planLimitValues.proTeam }),

        saveVariableMutation.mutateAsync({ name: 'plan.enterprise.apps_limit', value: planLimitValues.enterpriseApps }),
        saveVariableMutation.mutateAsync({ name: 'plan.enterprise.datasets_limit', value: planLimitValues.enterpriseDatasets }),
        saveVariableMutation.mutateAsync({ name: 'plan.enterprise.storage_gb', value: planLimitValues.enterpriseStorageGb }),
        saveVariableMutation.mutateAsync({ name: 'plan.enterprise.token_limit', value: planLimitValues.enterpriseTokens }),
        saveVariableMutation.mutateAsync({ name: 'plan.enterprise.team_limit', value: planLimitValues.enterpriseTeam }),
      ]);
      message.success('Subscription plan limits updated successfully!');
    } catch (e: any) {
      message.error(`Failed to update plan limits: ${e.message}`);
    }
  };

  const handleSaveReferral = async () => {
    try {
      await Promise.all([
        saveVariableMutation.mutateAsync({
          name: 'referral.enabled',
          value: referralValues.enabled ? 'true' : 'false',
        }),
        saveVariableMutation.mutateAsync({
          name: 'referral.storage_gb',
          value: referralValues.storageGb,
        }),
        saveVariableMutation.mutateAsync({
          name: 'referral.agents_limit',
          value: referralValues.agentsLimit,
        }),
      ]);
      message.success('Referral program settings updated successfully!');
    } catch (e: any) {
      message.error(`Failed to update referral settings: ${e.message}`);
    }
  };

  const handleSavePricing = async () => {
    try {
      await Promise.all([
        saveVariableMutation.mutateAsync({
          name: 'pricing.plus.usd',
          value: pricingValues.plusUsd,
        }),
        saveVariableMutation.mutateAsync({
          name: 'pricing.plus.uzs',
          value: pricingValues.plusUzs,
        }),
        saveVariableMutation.mutateAsync({
          name: 'pricing.pro.usd',
          value: pricingValues.proUsd,
        }),
        saveVariableMutation.mutateAsync({
          name: 'pricing.pro.uzs',
          value: pricingValues.proUzs,
        }),
      ]);
      message.success('Subscription pricing plans updated successfully!');
    } catch (e: any) {
      message.error(`Failed to update pricing: ${e.message}`);
    }
  };

  const handleSaveSmtp = async () => {
    try {
      await Promise.all([
        saveVariableMutation.mutateAsync({
          name: 'mail.server',
          value: smtpValues.server,
        }),
        saveVariableMutation.mutateAsync({
          name: 'mail.port',
          value: smtpValues.port,
        }),
        saveVariableMutation.mutateAsync({
          name: 'mail.use_ssl',
          value: smtpValues.useSsl ? 'true' : 'false',
        }),
        saveVariableMutation.mutateAsync({
          name: 'mail.use_tls',
          value: smtpValues.useTls ? 'true' : 'false',
        }),
        saveVariableMutation.mutateAsync({
          name: 'mail.username',
          value: smtpValues.username,
        }),
        saveVariableMutation.mutateAsync({
          name: 'mail.password',
          value: smtpValues.password,
        }),
        saveVariableMutation.mutateAsync({
          name: 'mail.timeout',
          value: smtpValues.timeout,
        }),
        saveVariableMutation.mutateAsync({
          name: 'mail.default_sender',
          value: smtpValues.defaultSender,
        }),
      ]);
      message.success('SMTP server settings updated successfully!');
    } catch (e: any) {
      message.error(`Failed to update SMTP settings: ${e.message}`);
    }
  };

  const handleSaveSystem = async () => {
    try {
      await Promise.all([
        saveVariableMutation.mutateAsync({
          name: 'enable_whitelist',
          value: systemValues.enableWhitelist ? 'true' : 'false',
        }),
        saveVariableMutation.mutateAsync({
          name: 'default_role',
          value: systemValues.defaultRole,
        }),
      ]);
      message.success('System policies updated successfully!');
    } catch (e: any) {
      message.error(`Failed to update system policies: ${e.message}`);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full w-full">
        <LucideLoader2 className="animate-spin size-8 text-accent-primary" />
      </div>
    );
  }

  return (
    <Card className="!shadow-none relative h-full bg-transparent overflow-hidden border-none">
      <Spotlight />
      <ScrollArea className="size-full">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold leading-10">
            System & Pricing Settings
          </CardTitle>
          <CardDescription className="text-text-secondary">
            Manage global Swipies platform configurations, plans, rates, and
            SMTP services.
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-2 pb-10">
          <Tabs defaultValue="pricing" className="space-y-6">
            <TabsList className="p-0 mb-4 gap-4 bg-transparent justify-start">
              <TabsTrigger
                value="pricing"
                className="flex items-center gap-2 text-text-secondary border-0.5 border-border-button data-[state=active]:bg-bg-card px-4 py-2 rounded-md"
              >
                <Coins className="size-4" />
                Pricing Plans
              </TabsTrigger>
              <TabsTrigger
                value="limits"
                className="flex items-center gap-2 text-text-secondary border-0.5 border-border-button data-[state=active]:bg-bg-card px-4 py-2 rounded-md"
              >
                <Sliders className="size-4" />
                Plan Tier Limits
              </TabsTrigger>
              <TabsTrigger
                value="oauth"
                className="flex items-center gap-2 text-text-secondary border-0.5 border-border-button data-[state=active]:bg-bg-card px-4 py-2 rounded-md"
              >
                <KeyRound className="size-4" />
                OAuth Login
              </TabsTrigger>
              <TabsTrigger
                value="smtp"
                className="flex items-center gap-2 text-text-secondary border-0.5 border-border-button data-[state=active]:bg-bg-card px-4 py-2 rounded-md"
              >
                <Mail className="size-4" />
                SMTP & Mail
              </TabsTrigger>
              <TabsTrigger
                value="system"
                className="flex items-center gap-2 text-text-secondary border-0.5 border-border-button data-[state=active]:bg-bg-card px-4 py-2 rounded-md"
              >
                <Settings className="size-4" />
                Policies & System
              </TabsTrigger>
              <TabsTrigger
                value="referrals"
                className="flex items-center gap-2 text-text-secondary border-0.5 border-border-button data-[state=active]:bg-bg-card px-4 py-2 rounded-md"
              >
                <Gift className="size-4" />
                Referrals
              </TabsTrigger>
            </TabsList>

            {/* Pricing Tabs Content */}
            <TabsContent value="pricing" className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Plus Plan Card */}
                <Card className="border border-border-button dark:bg-bg-card/30">
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold text-accent-primary">
                      Plus Plan
                    </CardTitle>
                    <CardDescription>
                      Monthly rate and allowances definition.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="plus-usd">Price per Month (USD)</Label>
                      <Input
                        id="plus-usd"
                        className="bg-bg-input border-border-button h-10"
                        value={pricingValues.plusUsd}
                        onChange={(e) =>
                          setPricingValues({
                            ...pricingValues,
                            plusUsd: e.target.value,
                          })
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="plus-uzs">Price per Month (UZS)</Label>
                      <Input
                        id="plus-uzs"
                        className="bg-bg-input border-border-button h-10"
                        value={pricingValues.plusUzs}
                        onChange={(e) =>
                          setPricingValues({
                            ...pricingValues,
                            plusUzs: e.target.value,
                          })
                        }
                      />
                    </div>
                  </CardContent>
                </Card>

                {/* Pro Plan Card */}
                <Card className="border border-border-button dark:bg-bg-card/30">
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold text-accent-primary">
                      Pro Plan
                    </CardTitle>
                    <CardDescription>
                      Monthly rate and allowances definition.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="pro-usd">Price per Month (USD)</Label>
                      <Input
                        id="pro-usd"
                        className="bg-bg-input border-border-button h-10"
                        value={pricingValues.proUsd}
                        onChange={(e) =>
                          setPricingValues({
                            ...pricingValues,
                            proUsd: e.target.value,
                          })
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="pro-uzs">Price per Month (UZS)</Label>
                      <Input
                        id="pro-uzs"
                        className="bg-bg-input border-border-button h-10"
                        value={pricingValues.proUzs}
                        onChange={(e) =>
                          setPricingValues({
                            ...pricingValues,
                            proUzs: e.target.value,
                          })
                        }
                      />
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="flex justify-end pt-4">
                <Button
                  className="flex items-center gap-2 h-10 px-6"
                  disabled={saveVariableMutation.isPending}
                  onClick={handleSavePricing}
                >
                  {saveVariableMutation.isPending ? (
                    <LucideLoader2 className="animate-spin size-4" />
                  ) : (
                    <Save className="size-4" />
                  )}
                  Save Pricing Plans
                </Button>
              </div>
            </TabsContent>

            {/* Plan Tier Limits Tab Content */}
            <TabsContent value="limits" className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Free Plan */}
                <Card className="border border-border-button dark:bg-bg-card/30">
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold text-text-primary">
                      Free Plan Limits
                    </CardTitle>
                    <CardDescription>
                      Resource limits for free tier tenants. (-1 for Unlimited)
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="free-apps">Max Apps (Chatbots + Agents)</Label>
                      <Input
                        id="free-apps"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.freeApps}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, freeApps: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="free-datasets">Max Datasets (Knowledge Bases)</Label>
                      <Input
                        id="free-datasets"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.freeDatasets}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, freeDatasets: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="free-storage">Storage Limit (GB)</Label>
                      <Input
                        id="free-storage"
                        type="number"
                        step="0.1"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.freeStorageGb}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, freeStorageGb: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="free-tokens">Monthly Token Limit</Label>
                      <Input
                        id="free-tokens"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.freeTokens}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, freeTokens: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="free-team">Max Team Members</Label>
                      <Input
                        id="free-team"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.freeTeam}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, freeTeam: e.target.value })}
                      />
                    </div>
                  </CardContent>
                </Card>

                {/* Plus Plan */}
                <Card className="border border-border-button dark:bg-bg-card/30">
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold text-accent-primary">
                      Plus Plan Limits
                    </CardTitle>
                    <CardDescription>
                      Resource limits for Plus tier subscribers. (-1 for Unlimited)
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="plus-apps">Max Apps (Chatbots + Agents)</Label>
                      <Input
                        id="plus-apps"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.plusApps}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, plusApps: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="plus-datasets">Max Datasets (Knowledge Bases)</Label>
                      <Input
                        id="plus-datasets"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.plusDatasets}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, plusDatasets: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="plus-storage">Storage Limit (GB)</Label>
                      <Input
                        id="plus-storage"
                        type="number"
                        step="0.1"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.plusStorageGb}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, plusStorageGb: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="plus-tokens">Monthly Token Limit</Label>
                      <Input
                        id="plus-tokens"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.plusTokens}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, plusTokens: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="plus-team">Max Team Members</Label>
                      <Input
                        id="plus-team"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.plusTeam}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, plusTeam: e.target.value })}
                      />
                    </div>
                  </CardContent>
                </Card>

                {/* Pro Plan */}
                <Card className="border border-border-button dark:bg-bg-card/30">
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold text-accent-primary">
                      Pro Plan Limits
                    </CardTitle>
                    <CardDescription>
                      Resource limits for Pro tier subscribers. (-1 for Unlimited)
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="pro-apps">Max Apps (Chatbots + Agents)</Label>
                      <Input
                        id="pro-apps"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.proApps}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, proApps: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="pro-datasets">Max Datasets (Knowledge Bases)</Label>
                      <Input
                        id="pro-datasets"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.proDatasets}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, proDatasets: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="pro-storage">Storage Limit (GB)</Label>
                      <Input
                        id="pro-storage"
                        type="number"
                        step="0.1"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.proStorageGb}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, proStorageGb: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="pro-tokens">Monthly Token Limit</Label>
                      <Input
                        id="pro-tokens"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.proTokens}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, proTokens: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="pro-team">Max Team Members</Label>
                      <Input
                        id="pro-team"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.proTeam}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, proTeam: e.target.value })}
                      />
                    </div>
                  </CardContent>
                </Card>

                {/* Enterprise Plan */}
                <Card className="border border-border-button dark:bg-bg-card/30">
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold text-text-primary">
                      Enterprise Plan Limits
                    </CardTitle>
                    <CardDescription>
                      Resource limits for Enterprise tier subscribers. (-1 for Unlimited)
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="ent-apps">Max Apps (Chatbots + Agents)</Label>
                      <Input
                        id="ent-apps"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.enterpriseApps}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, enterpriseApps: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="ent-datasets">Max Datasets (Knowledge Bases)</Label>
                      <Input
                        id="ent-datasets"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.enterpriseDatasets}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, enterpriseDatasets: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="ent-storage">Storage Limit (GB)</Label>
                      <Input
                        id="ent-storage"
                        type="number"
                        step="0.1"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.enterpriseStorageGb}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, enterpriseStorageGb: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="ent-tokens">Monthly Token Limit</Label>
                      <Input
                        id="ent-tokens"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.enterpriseTokens}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, enterpriseTokens: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="ent-team">Max Team Members</Label>
                      <Input
                        id="ent-team"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={planLimitValues.enterpriseTeam}
                        onChange={(e) => setPlanLimitValues({ ...planLimitValues, enterpriseTeam: e.target.value })}
                      />
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="flex justify-end pt-4">
                <Button
                  className="flex items-center gap-2 h-10 px-6"
                  disabled={saveVariableMutation.isPending}
                  onClick={handleSavePlanLimits}
                >
                  {saveVariableMutation.isPending ? (
                    <LucideLoader2 className="animate-spin size-4" />
                  ) : (
                    <Save className="size-4" />
                  )}
                  Save Plan Tier Limits
                </Button>
              </div>
            </TabsContent>

            {/* OAuth Social Login Tab Content */}
            <TabsContent value="oauth" className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Google OAuth Card */}
                <Card className="border border-border-button dark:bg-bg-card/30">
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold text-text-primary flex items-center gap-2">
                      Google OAuth Credentials
                    </CardTitle>
                    <CardDescription>
                      Configure Google OAuth 2.0 Client ID and Secret for 1-click Google Login & Registration.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="google-client-id">Google Client ID</Label>
                      <Input
                        id="google-client-id"
                        className="bg-bg-input border-border-button h-10 font-mono text-xs"
                        placeholder="e.g. XXXXXXXXXX-XXXXXXXXXX.apps.googleusercontent.com"
                        value={oauthValues.googleClientId}
                        onChange={(e) =>
                          setOauthValues({
                            ...oauthValues,
                            googleClientId: e.target.value,
                          })
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="google-client-secret">Google Client Secret</Label>
                      <Input
                        id="google-client-secret"
                        type="password"
                        className="bg-bg-input border-border-button h-10 font-mono text-xs"
                        placeholder="GOCSPX-XXXXXXXXXXXXXXXXXXXXXXXX"
                        value={oauthValues.googleClientSecret}
                        onChange={(e) =>
                          setOauthValues({
                            ...oauthValues,
                            googleClientSecret: e.target.value,
                          })
                        }
                      />
                    </div>
                    <p className="text-xs text-text-secondary pt-2">
                      Authorized Redirect URIs to add in Google Cloud Console:<br />
                      <code className="bg-bg-input px-1.5 py-0.5 rounded text-accent-primary select-all">
                        http://{window.location.host}/v1/user/oauth/callback/google
                      </code>
                    </p>
                  </CardContent>
                </Card>

                {/* GitHub OAuth Card */}
                <Card className="border border-border-button dark:bg-bg-card/30">
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold text-text-primary flex items-center gap-2">
                      GitHub OAuth Credentials
                    </CardTitle>
                    <CardDescription>
                      Configure GitHub OAuth App Client ID and Secret for GitHub Login & Registration.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="github-client-id">GitHub Client ID</Label>
                      <Input
                        id="github-client-id"
                        className="bg-bg-input border-border-button h-10 font-mono text-xs"
                        placeholder="e.g. Ov23liXXXXXXXXXX"
                        value={oauthValues.githubClientId}
                        onChange={(e) =>
                          setOauthValues({
                            ...oauthValues,
                            githubClientId: e.target.value,
                          })
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="github-client-secret">GitHub Client Secret</Label>
                      <Input
                        id="github-client-secret"
                        type="password"
                        className="bg-bg-input border-border-button h-10 font-mono text-xs"
                        placeholder="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
                        value={oauthValues.githubClientSecret}
                        onChange={(e) =>
                          setOauthValues({
                            ...oauthValues,
                            githubClientSecret: e.target.value,
                          })
                        }
                      />
                    </div>
                    <p className="text-xs text-text-secondary pt-2">
                      Authorization Callback URL to set in GitHub Developer Settings:<br />
                      <code className="bg-bg-input px-1.5 py-0.5 rounded text-accent-primary select-all">
                        http://{window.location.host}/v1/user/oauth/callback/github
                      </code>
                    </p>
                  </CardContent>
                </Card>
              </div>

              <div className="flex justify-end pt-4">
                <Button
                  className="flex items-center gap-2 h-10 px-6"
                  disabled={saveVariableMutation.isPending}
                  onClick={handleSaveOauth}
                >
                  {saveVariableMutation.isPending ? (
                    <LucideLoader2 className="animate-spin size-4" />
                  ) : (
                    <Save className="size-4" />
                  )}
                  Save OAuth Credentials
                </Button>
              </div>
            </TabsContent>

            {/* SMTP Tab Content */}
            <TabsContent value="smtp" className="space-y-6">
              <Card className="border border-border-button dark:bg-bg-card/30">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold">
                    SMTP Connection Settings
                  </CardTitle>
                  <CardDescription>
                    Configure outgoing system email settings for invites and
                    password recoveries.
                  </CardDescription>
                </CardHeader>
                <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="smtp-server">SMTP Server</Label>
                    <Input
                      id="smtp-server"
                      className="bg-bg-input border-border-button h-10"
                      placeholder="smtp.example.com"
                      value={smtpValues.server}
                      onChange={(e) =>
                        setSmtpValues({ ...smtpValues, server: e.target.value })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="smtp-port">SMTP Port</Label>
                    <Input
                      id="smtp-port"
                      className="bg-bg-input border-border-button h-10"
                      placeholder="465 or 587"
                      value={smtpValues.port}
                      onChange={(e) =>
                        setSmtpValues({ ...smtpValues, port: e.target.value })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="smtp-username">SMTP Username</Label>
                    <Input
                      id="smtp-username"
                      className="bg-bg-input border-border-button h-10"
                      value={smtpValues.username}
                      onChange={(e) =>
                        setSmtpValues({
                          ...smtpValues,
                          username: e.target.value,
                        })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="smtp-password">SMTP Password</Label>
                    <Input
                      id="smtp-password"
                      type="password"
                      className="bg-bg-input border-border-button h-10"
                      value={smtpValues.password}
                      onChange={(e) =>
                        setSmtpValues({
                          ...smtpValues,
                          password: e.target.value,
                        })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="smtp-sender">Default Sender Address</Label>
                    <Input
                      id="smtp-sender"
                      className="bg-bg-input border-border-button h-10"
                      placeholder="noreply@swipies.app"
                      value={smtpValues.defaultSender}
                      onChange={(e) =>
                        setSmtpValues({
                          ...smtpValues,
                          defaultSender: e.target.value,
                        })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="smtp-timeout">Timeout (seconds)</Label>
                    <Input
                      id="smtp-timeout"
                      type="number"
                      className="bg-bg-input border-border-button h-10"
                      value={smtpValues.timeout}
                      onChange={(e) =>
                        setSmtpValues({
                          ...smtpValues,
                          timeout: e.target.value,
                        })
                      }
                    />
                  </div>

                  <div className="flex items-center space-x-8 pt-4">
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="smtp-ssl"
                        checked={smtpValues.useSsl}
                        onCheckedChange={(checked) =>
                          setSmtpValues({ ...smtpValues, useSsl: checked })
                        }
                      />
                      <Label htmlFor="smtp-ssl">Use SSL</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="smtp-tls"
                        checked={smtpValues.useTls}
                        onCheckedChange={(checked) =>
                          setSmtpValues({ ...smtpValues, useTls: checked })
                        }
                      />
                      <Label htmlFor="smtp-tls">Use TLS</Label>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <div className="flex justify-end pt-4">
                <Button
                  className="flex items-center gap-2 h-10 px-6"
                  disabled={saveVariableMutation.isPending}
                  onClick={handleSaveSmtp}
                >
                  {saveVariableMutation.isPending ? (
                    <LucideLoader2 className="animate-spin size-4" />
                  ) : (
                    <Save className="size-4" />
                  )}
                  Save SMTP Settings
                </Button>
              </div>
            </TabsContent>

            {/* System/Policies Tab Content */}
            <TabsContent value="system" className="space-y-6">
              <Card className="border border-border-button dark:bg-bg-card/30">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold flex items-center gap-2">
                    <ShieldCheck className="text-state-success size-5" />
                    Security & Registration Policies
                  </CardTitle>
                  <CardDescription>
                    Control signup rules and initial role assignment.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center justify-between border-b pb-4 border-border-button">
                    <div>
                      <Label
                        htmlFor="enable-whitelist"
                        className="text-base font-medium"
                      >
                        Enable Registration Whitelist
                      </Label>
                      <p className="text-xs text-text-secondary">
                        If active, only users whose emails are explicitly
                        whitelisted can register.
                      </p>
                    </div>
                    <Switch
                      id="enable-whitelist"
                      checked={systemValues.enableWhitelist}
                      onCheckedChange={(checked) =>
                        setSystemValues({
                          ...systemValues,
                          enableWhitelist: checked,
                        })
                      }
                    />
                  </div>

                  <div className="space-y-2 max-w-md">
                    <Label htmlFor="default-role">Default Assigned Role</Label>
                    <Input
                      id="default-role"
                      className="bg-bg-input border-border-button h-10"
                      placeholder="e.g. user"
                      value={systemValues.defaultRole}
                      onChange={(e) =>
                        setSystemValues({
                          ...systemValues,
                          defaultRole: e.target.value,
                        })
                      }
                    />
                    <p className="text-xs text-text-secondary">
                      Leave empty for standard registration default assignment.
                    </p>
                  </div>
                </CardContent>
              </Card>

              <div className="flex justify-end pt-4">
                <Button
                  className="flex items-center gap-2 h-10 px-6"
                  disabled={saveVariableMutation.isPending}
                  onClick={handleSaveSystem}
                >
                  {saveVariableMutation.isPending ? (
                    <LucideLoader2 className="animate-spin size-4" />
                  ) : (
                    <Save className="size-4" />
                  )}
                  Save System Policies
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="referrals" className="space-y-6">
              <Card className="border border-border-button dark:bg-bg-card/30">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold flex items-center gap-2">
                    <Gift className="text-accent-primary size-5" />
                    Referral Program Configuration
                  </CardTitle>
                  <CardDescription>
                    Configure the reward values granted to referrers when new
                    users sign up via their referral links.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center justify-between border-b pb-4 border-border-button">
                    <div>
                      <Label
                        htmlFor="referral-enabled"
                        className="text-base font-medium"
                      >
                        Enable Referral Program
                      </Label>
                      <p className="text-xs text-text-secondary">
                        Toggle to globally enable or disable referral rewards
                        and links across the platform.
                      </p>
                    </div>
                    <Switch
                      id="referral-enabled"
                      checked={referralValues.enabled}
                      onCheckedChange={(checked) =>
                        setReferralValues({
                          ...referralValues,
                          enabled: checked,
                        })
                      }
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <Label htmlFor="referral-storage">
                        Bonus Storage per Referral (GB)
                      </Label>
                      <Input
                        id="referral-storage"
                        type="number"
                        step="0.1"
                        className="bg-bg-input border-border-button h-10"
                        value={referralValues.storageGb}
                        onChange={(e) =>
                          setReferralValues({
                            ...referralValues,
                            storageGb: e.target.value,
                          })
                        }
                      />
                      <p className="text-xs text-text-secondary">
                        Extra storage space in gigabytes awarded to the
                        referrer.
                      </p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="referral-agents">
                        Bonus Agents/Apps per Referral
                      </Label>
                      <Input
                        id="referral-agents"
                        type="number"
                        className="bg-bg-input border-border-button h-10"
                        value={referralValues.agentsLimit}
                        onChange={(e) =>
                          setReferralValues({
                            ...referralValues,
                            agentsLimit: e.target.value,
                          })
                        }
                      />
                      <p className="text-xs text-text-secondary">
                        Extra chat dialogues/agent canvas limit awarded to the
                        referrer.
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <div className="flex justify-end pt-4">
                <Button
                  className="flex items-center gap-2 h-10 px-6"
                  disabled={saveVariableMutation.isPending}
                  onClick={handleSaveReferral}
                >
                  {saveVariableMutation.isPending ? (
                    <LucideLoader2 className="animate-spin size-4" />
                  ) : (
                    <Save className="size-4" />
                  )}
                  Save Referral Settings
                </Button>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </ScrollArea>
    </Card>
  );
}
