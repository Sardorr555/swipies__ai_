import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import message from '@/components/ui/message';
import { 
  Key, 
  ArrowRight, 
  Copy, 
  Check, 
  ShieldCheck, 
  Clock, 
  Edit2, 
  Trash2, 
  Plus, 
  Loader2, 
  CheckCircle2 
} from 'lucide-react';
import { ProfileSettingWrapperCard } from '../components/user-setting-header';
import { 
  getUserLicensePricing, 
  listLicenses, 
  renameLicense, 
  revokeLicense 
} from '@/services/license-service';
import { useNavigate } from 'react-router';

interface PricingConfig {
  price_6_months: number;
  price_12_months: number;
  price_per_month_custom?: number;
}

interface LicenseItem {
  id: string;
  name: string;
  license_key: string;
  duration_months: number;
  expiry_date?: string;
  status: 'active' | 'pending' | 'revoked' | 'expired';
  is_paid: boolean;
  create_time?: string | number;
}

const fmtUZS = (n: number) =>
  new Intl.NumberFormat('uz-UZ').format(n) + ' UZS';

const LicensePurchasePage = () => {
  const navigate = useNavigate();
  const [selectedMonths, setSelectedMonths] = useState<6 | 12>(12);
  const [pricing, setPricing] = useState<PricingConfig>({
    price_6_months: 300000,
    price_12_months: 500000,
  });

  const [licenses, setLicenses] = useState<LicenseItem[]>([]);
  const [loadingLicenses, setLoadingLicenses] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Rename state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  const fetchUserLicenses = () => {
    setLoadingLicenses(true);
    listLicenses()
      .then((res: any) => {
        if (res?.data?.code === 0 && Array.isArray(res.data.data)) {
          // Filter to show active/paid or user licenses
          setLicenses(res.data.data.filter((l: LicenseItem) => l.is_paid || l.status === 'active' || l.license_key));
        }
      })
      .catch((err) => console.error('Failed to load user licenses', err))
      .finally(() => setLoadingLicenses(false));
  };

  useEffect(() => {
    getUserLicensePricing()
      .then((res: any) => {
        if (res?.data?.code === 0 && res.data.data) {
          setPricing(res.data.data);
        }
      })
      .catch(() => {});

    fetchUserLicenses();
  }, []);

  const handleProceedToCheckout = () => {
    navigate(`/checkout?plan=license&period=${selectedMonths}`);
  };

  const handleCopyKey = (key: string, id: string) => {
    if (!key) return;
    navigator.clipboard.writeText(key);
    setCopiedId(id);
    message.success('License key copied to clipboard!');
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleStartRename = (license: LicenseItem) => {
    setEditingId(license.id);
    setEditingName(license.name || '');
  };

  const handleSaveRename = async (licenseId: string) => {
    if (!editingName.trim()) return;
    try {
      const res: any = await renameLicense(licenseId, editingName.trim());
      if (res?.data?.code === 0) {
        message.success('License name updated!');
        setEditingId(null);
        fetchUserLicenses();
      }
    } catch {
      message.error('Failed to rename license');
    }
  };

  const handleRevoke = async (licenseId: string) => {
    if (!window.confirm('Are you sure you want to revoke this license key?')) return;
    try {
      const res: any = await revokeLicense(licenseId);
      if (res?.data?.code === 0) {
        message.success('License key revoked');
        fetchUserLicenses();
      }
    } catch {
      message.error('Failed to revoke license');
    }
  };

  return (
    <ProfileSettingWrapperCard
      header={
        <header className="flex flex-col gap-1 w-full">
          <h2 className="text-2xl font-bold tracking-tight text-text-primary flex items-center gap-2">
            <Key className="text-accent-primary" size={24} />
            License Keys & Purchases
          </h2>
          <p className="text-text-secondary text-sm">
            Manage your purchased self-hosted Swipies AI license keys or buy new keys.
          </p>
        </header>
      }
    >
      <div className="h-full overflow-x-hidden overflow-y-auto pb-12 pr-1 mt-6 space-y-10 px-5 max-w-5xl">
        
        {/* SECTION 1: MY PURCHASED LICENSES */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-text-primary flex items-center gap-2">
              <ShieldCheck className="text-emerald-500" size={20} />
              My Purchased License Keys
            </h3>
            <span className="text-xs text-text-secondary font-medium">
              {licenses.length} {licenses.length === 1 ? 'Key' : 'Keys'} active
            </span>
          </div>

          {loadingLicenses ? (
            <div className="flex items-center justify-center py-10 rounded-2xl border border-border-default bg-bg-card/10 text-text-secondary gap-2 text-sm">
              <Loader2 className="animate-spin text-accent-primary" size={18} />
              Loading your license keys...
            </div>
          ) : licenses.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 rounded-2xl border border-dashed border-border-default bg-bg-card/10 text-center p-6 space-y-3">
              <div className="p-3 bg-accent-primary/10 rounded-full text-accent-primary">
                <Key size={28} />
              </div>
              <div className="space-y-1">
                <p className="text-base font-semibold text-text-primary">No license keys purchased yet</p>
                <p className="text-xs text-text-secondary max-w-sm">
                  Select a duration below to purchase your first self-hosted license key for Swipies AI.
                </p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {licenses.map((lic) => (
                <div
                  key={lic.id}
                  className="rounded-2xl border border-border-default bg-bg-card/30 p-5 backdrop-blur-md space-y-4 transition-all hover:border-accent-primary/40 shadow-sm"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-default/50 pb-3">
                    <div className="flex items-center gap-2">
                      {editingId === lic.id ? (
                        <div className="flex items-center gap-2">
                          <Input
                            value={editingName}
                            onChange={(e) => setEditingName(e.target.value)}
                            className="h-8 text-sm bg-bg-base border-accent-primary max-w-[200px]"
                            placeholder="License Name"
                          />
                          <Button
                            size="sm"
                            className="h-8 text-xs bg-accent-primary text-white"
                            onClick={() => handleSaveRename(lic.id)}
                          >
                            Save
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-8 text-xs"
                            onClick={() => setEditingId(null)}
                          >
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-base text-text-primary">
                            {lic.name || 'Swipies Self-Hosted License'}
                          </span>
                          <button
                            onClick={() => handleStartRename(lic)}
                            className="text-text-secondary hover:text-accent-primary transition-colors p-1"
                            title="Rename"
                          >
                            <Edit2 size={14} />
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Status Badge */}
                    <div className="flex items-center gap-2">
                      {lic.status === 'active' || lic.is_paid ? (
                        <span className="flex items-center gap-1 text-[11px] font-semibold bg-emerald-500/15 text-emerald-400 px-2.5 py-1 rounded-full border border-emerald-500/20">
                          <CheckCircle2 size={12} /> Active
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-[11px] font-semibold bg-amber-500/15 text-amber-400 px-2.5 py-1 rounded-full border border-amber-500/20">
                          <Clock size={12} /> {lic.status}
                        </span>
                      )}
                      
                      <button
                        onClick={() => handleRevoke(lic.id)}
                        className="text-rose-400 hover:text-rose-300 transition-colors p-1 ml-2"
                        title="Revoke License"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>

                  {/* Key Display */}
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold tracking-wider uppercase text-text-secondary">
                      License Key
                    </label>
                    <div className="flex items-center gap-2 bg-bg-base/80 border border-border-default rounded-xl p-3 font-mono text-xs text-accent-primary break-all">
                      <span className="flex-1 truncate">{lic.license_key || 'Processing generation...'}</span>
                      {lic.license_key && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleCopyKey(lic.license_key, lic.id)}
                          className="h-7 px-2.5 text-xs text-text-primary hover:bg-accent-primary/20 gap-1.5 shrink-0"
                        >
                          {copiedId === lic.id ? (
                            <>
                              <Check size={14} className="text-emerald-400" /> Copied
                            </>
                          ) : (
                            <>
                              <Copy size={14} /> Copy Key
                            </>
                          )}
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* License Info footer */}
                  <div className="flex flex-wrap items-center justify-between text-xs text-text-secondary pt-1 gap-2">
                    <div className="flex items-center gap-4">
                      <span>Duration: <strong className="text-text-primary">{lic.duration_months} months</strong></span>
                      {lic.expiry_date && (
                        <span>Expires: <strong className="text-text-primary">{String(lic.expiry_date).split('T')[0]}</strong></span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <hr className="border-border-default/60" />

        {/* SECTION 2: PURCHASE NEW LICENSE KEY */}
        <div className="space-y-5 max-w-lg">
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-text-primary flex items-center gap-2">
              <Plus className="text-accent-primary" size={20} />
              Buy a New License Key
            </h3>
            <p className="text-xs text-text-secondary">
              Select the desired license duration. Your new license key will be generated instantly upon payment confirmation.
            </p>
          </div>

          {/* Plan cards */}
          <div className="grid grid-cols-2 gap-4">
            {([6, 12] as const).map((m) => {
              const p = m === 12 ? pricing.price_12_months : pricing.price_6_months;
              const selected = selectedMonths === m;
              return (
                <button
                  key={m}
                  onClick={() => setSelectedMonths(m)}
                  className={`rounded-2xl border p-5 text-left transition-all space-y-2 relative overflow-hidden ${
                    selected
                      ? 'border-accent-primary bg-accent-primary/10 ring-1 ring-accent-primary/50 shadow-lg shadow-accent-primary/5'
                      : 'border-border-default bg-bg-card/20 hover:border-accent-primary/40'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div className="text-sm font-bold text-text-primary">{m} Months</div>
                    {m === 12 && (
                      <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">
                        Best Value
                      </span>
                    )}
                  </div>
                  <div className="text-xl font-extrabold text-accent-primary">{fmtUZS(p)}</div>
                  <div className="text-[11px] text-text-secondary">Self-hosted Deployment</div>
                </button>
              );
            })}
          </div>

          {/* Total Summary */}
          <div className="flex items-center justify-between rounded-xl border border-border-default bg-bg-card/30 px-5 py-4">
            <span className="text-sm font-semibold text-text-secondary">Total Price</span>
            <span className="text-lg font-extrabold text-text-primary">
              {fmtUZS(selectedMonths === 12 ? pricing.price_12_months : pricing.price_6_months)}
            </span>
          </div>

          <Button
            className="bg-accent-primary hover:bg-accent-primary/90 text-white w-full py-6 text-base font-bold rounded-xl gap-2 shadow-lg shadow-accent-primary/20"
            onClick={handleProceedToCheckout}
          >
            Proceed to Secure Checkout <ArrowRight size={18} />
          </Button>
        </div>

      </div>
    </ProfileSettingWrapperCard>
  );
};

export default LicensePurchasePage;
