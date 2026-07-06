import Spotlight from '@/components/spotlight';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import message from '@/components/ui/message';
import request from '@/utils/request';
import { Key, ShieldCheck, ShieldAlert, Sparkles, HelpCircle, Calendar, User } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ProfileSettingWrapperCard } from '../components/user-setting-header';

interface LicensePayload {
  owner: string;
  expiry: string;
  type: string;
}

interface LicenseData {
  is_valid: boolean;
  message: string;
  payload: LicensePayload | null;
  license_key: string;
}

const LicensePage = () => {
  const { t } = useTranslation();
  const [licenseData, setLicenseData] = useState<LicenseData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activating, setActivating] = useState(false);
  const [newKey, setNewKey] = useState('');

  const fetchLicense = async () => {
    try {
      setLoading(true);
      const res = await request.get('/system/license');
      if (res.data && res.data.code === 0) {
        setLicenseData(res.data.data);
        if (res.data.data?.license_key) {
          setNewKey(res.data.data.license_key);
        }
      }
    } catch (err) {
      console.error('Failed to load license', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLicense();
  }, []);

  const handleActivate = async () => {
    const trimmedKey = newKey.trim();
    if (!trimmedKey) {
      message.error(t('setting.apiKeyMessage', 'Please enter the license key'));
      return;
    }

    try {
      setActivating(true);
      const res = await request.post('/system/license', {
        data: { license_key: trimmedKey },
      });
      if (res.data && res.data.code === 0) {
        message.success(res.data.data.message || 'License activated successfully!');
        fetchLicense();
      } else {
        message.error(res.data.message || 'Invalid license key.');
      }
    } catch (err: any) {
      const errMsg = err?.response?.data?.message || err?.message || 'Activation failed';
      message.error(errMsg);
    } finally {
      setActivating(false);
    }
  };

  // Calculate days remaining
  const getDaysRemaining = () => {
    if (!licenseData?.payload?.expiry) return 0;
    const expiryDate = new Date(licenseData.payload.expiry);
    const today = new Date();
    const diffTime = expiryDate.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays > 0 ? diffDays : 0;
  };

  const daysRemaining = getDaysRemaining();

  return (
    <ProfileSettingWrapperCard
      header={
        <header className="flex flex-col gap-1">
          <h2 className="text-2xl font-bold tracking-tight text-text-primary flex items-center gap-2">
            <Key className="text-accent-primary animate-pulse" size={24} />
            {t('setting.license', 'License & Billing')}
          </h2>
          <p className="text-text-secondary text-sm">
            Manage your Swipies AI commercial license keys, billing status, and system limits.
          </p>
        </header>
      }
    >
      <Spotlight />

      <div className="h-full overflow-x-hidden overflow-y-auto space-y-6 pb-8 pr-1">
        {/* Status Card */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="md:col-span-2 border border-border-default bg-bg-component/40 backdrop-blur-md relative overflow-hidden">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                  {licenseData?.is_valid ? (
                    <>
                      <ShieldCheck className="text-emerald-500" size={22} />
                      <span className="text-emerald-500 font-bold">Licensed Version Active</span>
                    </>
                  ) : (
                    <>
                      <ShieldAlert className="text-amber-500 animate-bounce" size={22} />
                      <span className="text-amber-500 font-bold">Base Version (Unlicensed)</span>
                    </>
                  )}
                </CardTitle>
                <CardDescription>
                  {licenseData?.is_valid
                    ? 'All platform features are unlocked and verified successfully.'
                    : 'Running under standard community limitations. Upgrade to activate premium features.'}
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                {licenseData?.is_valid && licenseData.payload && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm bg-bg-base/30 p-4 rounded-lg border border-border-default/50">
                    <div className="flex items-center gap-3">
                      <User className="text-text-secondary" size={18} />
                      <div>
                        <p className="text-xs text-text-secondary font-medium">Licensee / Owner</p>
                        <p className="font-semibold text-text-primary">{licenseData.payload.owner}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Calendar className="text-text-secondary" size={18} />
                      <div>
                        <p className="text-xs text-text-secondary font-medium">Expiration Date</p>
                        <p className="font-semibold text-text-primary">{licenseData.payload.expiry}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Sparkles className="text-text-secondary" size={18} />
                      <div>
                        <p className="text-xs text-text-secondary font-medium">License Plan</p>
                        <p className="font-semibold text-accent-primary capitalize">
                          {licenseData.payload.type === 'yearly' ? 'Yearly Plan ($199/yr)' : '6-Month Plan ($129/6mo)'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <ShieldCheck className="text-text-secondary" size={18} />
                      <div>
                        <p className="text-xs text-text-secondary font-medium">Time Remaining</p>
                        <p className="font-semibold text-emerald-500">
                          {daysRemaining} Days Left
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="space-y-2 pt-2">
                  <label className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                    Activate / Change License Key
                  </label>
                  <div className="flex flex-col sm:flex-row gap-3">
                    <textarea
                      placeholder="Paste your base64-encoded Swipies License Key here..."
                      value={newKey}
                      onChange={(e) => setNewKey(e.target.value)}
                      className="flex-1 min-h-[80px] bg-bg-base text-text-primary border border-border-default rounded-md p-3 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-accent-primary resize-none"
                    />
                  </div>
                  <div className="flex justify-end pt-2">
                    <Button
                      onClick={handleActivate}
                      disabled={activating}
                      className="bg-accent-primary hover:bg-accent-primary/95 text-white"
                    >
                      {activating ? 'Activating...' : 'Activate License'}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Pricing Info Card */}
            <Card className="border border-border-default bg-bg-component/40 backdrop-blur-md flex flex-col justify-between">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold">Buy Commercial License</CardTitle>
                <CardDescription>Get unlimited features for your team.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-xs">
                <div className="space-y-2">
                  <div className="border border-border-default/80 p-3 rounded bg-bg-base/20">
                    <p className="font-bold text-sm text-text-primary">Yearly License</p>
                    <p className="text-accent-primary font-bold text-lg">$199 <span className="text-xs text-text-secondary font-normal">/ year</span></p>
                    <p className="text-text-secondary mt-1">Best value for long term deployments.</p>
                  </div>

                  <div className="border border-border-default/80 p-3 rounded bg-bg-base/20">
                    <p className="font-bold text-sm text-text-primary">6-Month License</p>
                    <p className="text-accent-primary font-bold text-lg">$129 <span className="text-xs text-text-secondary font-normal">/ 6 months</span></p>
                    <p className="text-text-secondary mt-1">Flexible choice for testing and pilot stages.</p>
                  </div>
                </div>

                <div className="bg-accent-primary/10 p-3 rounded-lg border border-accent-primary/20 text-text-primary">
                  <p className="font-semibold flex items-center gap-1.5 mb-1">
                    <HelpCircle size={14} className="text-accent-primary" />
                    How to get a key?
                  </p>
                  <p className="text-text-secondary leading-relaxed">
                    Please contact our licensing team at <a href="mailto:licensing@swipies.io" className="text-accent-primary underline hover:text-accent-primary/80">licensing@swipies.io</a> to purchase a key.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Feature Comparison Table */}
        <Card className="border border-border-default bg-bg-component/40 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Plan Limits & Capabilities</CardTitle>
            <CardDescription>Compare capabilities between the unlicensed base version and the full premium version.</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left border-collapse">
                <thead>
                  <tr className="border-b border-border-default bg-bg-base/25">
                    <th className="p-4 font-semibold text-text-secondary">Feature / Limit</th>
                    <th className="p-4 font-semibold text-amber-500">Base Version</th>
                    <th className="p-4 font-semibold text-emerald-500">Licensed Version</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-default/50">
                  <tr>
                    <td className="p-4 font-medium text-text-primary">Maximum Active Agents</td>
                    <td className="p-4 text-text-secondary">1 Agent Maximum</td>
                    <td className="p-4 text-text-primary font-semibold">Unlimited Agents</td>
                  </tr>
                  <tr>
                    <td className="p-4 font-medium text-text-primary">Model API Providers</td>
                    <td className="p-4 text-text-secondary">Google & OpenAI APIs Only</td>
                    <td className="p-4 text-text-primary font-semibold">All Supported Providers (Ollama, DeepSeek, Anthropic, Bedrock, etc.)</td>
                  </tr>
                  <tr>
                    <td className="p-4 font-medium text-text-primary">Local / Self-Hosted Models</td>
                    <td className="p-4 text-text-secondary">Blocked</td>
                    <td className="p-4 text-text-primary font-semibold">Supported (Ollama, local HuggingFace Embeddings, etc.)</td>
                  </tr>
                  <tr>
                    <td className="p-4 font-medium text-text-primary">License verification status</td>
                    <td className="p-4 text-text-secondary">Offline limit reminder display</td>
                    <td className="p-4 text-text-primary font-semibold">Automatic background verification</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </ProfileSettingWrapperCard>
  );
};

export default LicensePage;
