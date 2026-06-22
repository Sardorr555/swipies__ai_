import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Coins,
  LucideLoader2,
  Mail,
  Save,
  Settings,
  ShieldCheck,
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
          </Tabs>
        </CardContent>
      </ScrollArea>
    </Card>
  );
}
