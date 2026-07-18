import { useEffect, useState } from 'react';
import Spotlight from '@/components/spotlight';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import message from '@/components/ui/message';
import request from '@/utils/request';
import { 
  Key, 
  ShieldCheck, 
  Info,
  AlertTriangle,
  LucideExternalLink
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { ProfileSettingWrapperCard } from '../components/user-setting-header';

interface LicenseStatus {
  is_valid: boolean;
  message: string;
  payload?: {
    owner: string;
    expiry: string;
    type: string;
  };
  license_key?: string;
  db_record?: {
    id: string;
    name: string;
    amount: number;
    duration_months: number;
    expiry_date: string;
    payment_id: string;
    is_paid: boolean;
    status: string;
    create_date: string;
  };
}

const LicensePage = () => {
  const { t } = useTranslation();
  const [status, setStatus] = useState<LicenseStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [licenseInput, setLicenseInput] = useState('');
  const [updating, setUpdating] = useState(false);

  const fetchLicenseStatus = async () => {
    setLoading(true);
    try {
      const res = await request.get('/api/v1/system/license');
      if (res?.data?.code === 0) {
        setStatus(res.data.data);
        if (res.data.data?.license_key) {
          setLicenseInput(res.data.data.license_key);
        }
      }
    } catch (err) {
      console.error(err);
      message.error('Failed to load license details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLicenseStatus();
  }, []);

  const handleActivate = async () => {
    const trimmedKey = licenseInput.trim();
    if (!trimmedKey) {
      message.error('License key cannot be empty.');
      return;
    }
    setUpdating(true);
    try {
      const res = await request.post('/api/v1/system/license', {
        data: { license_key: trimmedKey },
      });
      if (res && res.data && res.data.code === 0) {
        message.success('License activated successfully!');
        setStatus(res.data.data);
      } else {
        message.error(res?.data?.message || 'Failed to activate license.');
      }
    } catch (err: any) {
      const errMsg = err?.response?.data?.message || err?.message || 'Error occurred during activation.';
      message.error(errMsg);
    } finally {
      setUpdating(false);
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    try {
      const formattedStr = dateStr.includes(' ') ? dateStr.replace(' ', 'T') : dateStr;
      const date = new Date(formattedStr);
      return date.toLocaleDateString(undefined, { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  const formatPrice = (amount?: number) => {
    if (amount === undefined || amount === null) return 'N/A';
    if (amount === 0) return 'Free / Promo / System';
    return `${amount.toLocaleString()} UZS`;
  };

  return (
    <ProfileSettingWrapperCard
      header={
        <header className="flex flex-col gap-1 w-full">
          <div className="flex justify-between items-center w-full">
            <h2 className="text-2xl font-bold tracking-tight text-text-primary flex items-center gap-2">
              <Key className="text-accent-primary" size={24} />
              {t('setting.license', 'License & Activation')}
            </h2>
          </div>
          <p className="text-text-secondary text-sm">
            Activate Swipies AI premium commercial features on this deployment.
          </p>
        </header>
      }
    >
      <Spotlight />

      <div className="h-full overflow-x-hidden overflow-y-auto space-y-6 pb-8 pr-1 mt-6">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-accent-primary"></div>
          </div>
        ) : (
          <div className="grid gap-6">
            {/* License Status Hero */}
            {status?.is_valid ? (
              <Card className="border border-emerald-500/20 bg-emerald-500/5 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-6 opacity-[0.05] pointer-events-none text-emerald-500">
                  <ShieldCheck size={140} />
                </div>
                <CardContent className="p-6 space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-emerald-500/20 rounded-full text-emerald-400 border border-emerald-500/25">
                      <ShieldCheck size={24} />
                    </div>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                        Active License
                      </span>
                      <h3 className="text-lg font-bold text-text-primary mt-1">Premium Commercial Edition</h3>
                    </div>
                  </div>

                  <p className="text-sm text-text-secondary">
                    {status.message || 'This system is running with a valid commercial license key.'}
                  </p>

                  {status.payload && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4 border-t border-emerald-500/10 text-sm">
                      <div className="space-y-1">
                        <span className="text-text-secondary block text-xs">Licensed To:</span>
                        <span className="font-semibold text-text-primary font-mono">{status.payload.owner}</span>
                      </div>
                      <div className="space-y-1">
                        <span className="text-text-secondary block text-xs">License Type / Duration:</span>
                        <span className="font-semibold text-text-primary capitalize">
                          {status.db_record 
                            ? `${status.db_record.duration_months} Months (${status.db_record.name})` 
                            : status.payload.type === 'yearly' ? 'Yearly (12 Months)' : status.payload.type === '6_months' ? '6 Months' : status.payload.type || 'Custom'}
                        </span>
                      </div>
                      <div className="space-y-1">
                        <span className="text-text-secondary block text-xs">Expiration Date:</span>
                        <span className="font-semibold text-text-primary">
                          {status.db_record ? formatDate(status.db_record.expiry_date) : formatDate(status.payload.expiry)}
                        </span>
                      </div>

                      {status.db_record && (
                        <>
                          <div className="space-y-1">
                            <span className="text-text-secondary block text-xs">Activation Date:</span>
                            <span className="font-semibold text-text-primary">
                              {formatDate(status.db_record.create_date)}
                            </span>
                          </div>
                          <div className="space-y-1">
                            <span className="text-text-secondary block text-xs">Purchase Price:</span>
                            <span className="font-semibold text-emerald-400 font-mono">
                              {formatPrice(status.db_record.amount)}
                            </span>
                          </div>
                          <div className="space-y-1">
                            <span className="text-text-secondary block text-xs">Payment Transaction:</span>
                            <span className="font-semibold text-text-primary font-mono text-xs break-all">
                              {status.db_record.payment_id || 'N/A'}
                            </span>
                          </div>
                          <div className="space-y-1">
                            <span className="text-text-secondary block text-xs">License ID:</span>
                            <span className="font-semibold text-text-primary font-mono text-xs break-all">
                              {status.db_record.id}
                            </span>
                          </div>
                          <div className="space-y-1">
                            <span className="text-text-secondary block text-xs">Payment Status:</span>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                              status.db_record.is_paid ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
                            }`}>
                              {status.db_record.is_paid ? 'Paid' : 'Unpaid'}
                            </span>
                          </div>
                          <div className="space-y-1">
                            <span className="text-text-secondary block text-xs">Activation Status:</span>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold capitalize ${
                              status.db_record.status === 'active' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                            }`}>
                              {status.db_record.status}
                            </span>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            ) : (
              <Card className="border border-amber-500/25 bg-amber-500/5 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-6 opacity-[0.05] pointer-events-none text-amber-500">
                  <AlertTriangle size={140} />
                </div>
                <CardContent className="p-6 space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-amber-500/20 rounded-full text-amber-400 border border-amber-500/25">
                      <AlertTriangle size={24} />
                    </div>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded">
                        No Active License
                      </span>
                      <h3 className="text-lg font-bold text-text-primary mt-1">Free / Base Edition</h3>
                    </div>
                  </div>
                  <p className="text-sm text-text-secondary leading-relaxed">
                    You are currently running the base edition of Swipies. To unlock full LLM providers, custom agent canvases, and remove API limits, please activate a valid commercial license key.
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Input & Activation Box */}
            <Card className="border border-border-default bg-bg-component/10">
              <CardContent className="p-6 space-y-4">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-semibold text-text-primary">
                    {status?.is_valid ? 'Update / Change License Key:' : 'Enter License Key:'}
                  </label>
                  <Textarea
                    placeholder="Paste your base64-encoded Swipies License Key here..."
                    value={licenseInput}
                    onChange={(e) => setLicenseInput(e.target.value)}
                    disabled={updating}
                    className="font-mono text-xs"
                    rows={6}
                  />
                </div>

                <div className="flex justify-between items-center pt-2">
                  <div className="flex items-center gap-2 text-xs text-text-secondary">
                    <Info size={16} className="text-accent-primary shrink-0" />
                    <span>Need a key? Buy it at </span>
                    <a
                      href="https://api.swipies.app/user-setting/license"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 font-semibold text-accent-primary hover:underline"
                    >
                      api.swipies.app <LucideExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                  <Button
                    className="bg-accent-primary hover:bg-accent-primary/95 text-white"
                    onClick={handleActivate}
                    loading={updating}
                  >
                    Activate / Update License
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </ProfileSettingWrapperCard>
  );
};

export default LicensePage;
