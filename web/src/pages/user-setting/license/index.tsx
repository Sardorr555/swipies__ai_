import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import message from '@/components/ui/message';
import {
  Key,
  CreditCard,
  CheckCircle2,
  Copy,
  ArrowRight,
  LockKeyhole,
} from 'lucide-react';
import { ProfileSettingWrapperCard } from '../components/user-setting-header';
import {
  createLicensePay,
  preApplyLicensePay,
  applyLicensePay,
  getUserLicensePricing,
} from '@/services/license-service';

// ─── Types ────────────────────────────────────────────────────────────────────

interface PricingConfig {
  price_6_months: number;
  price_12_months: number;
  price_per_month_custom?: number;
}

type Step = 'plan' | 'card' | 'otp' | 'done';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  new Intl.NumberFormat('uz-UZ').format(n) + ' UZS';

// ─── Sub-components ───────────────────────────────────────────────────────────

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={copy}
      title="Copy"
      className="text-text-secondary hover:text-accent-primary transition-colors shrink-0"
    >
      {copied ? (
        <CheckCircle2 size={15} className="text-emerald-400" />
      ) : (
        <Copy size={15} />
      )}
    </button>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

const LicensePurchasePage = () => {
  const [step, setStep] = useState<Step>('plan');
  const [pricing, setPricing] = useState<PricingConfig>({
    price_6_months: 300000,
    price_12_months: 500000,
  });

  // Plan step
  const [selectedMonths, setSelectedMonths] = useState<6 | 12>(12);
  const [licenseName, setLicenseName] = useState('My Swipies License');

  // Card step
  const [transactionId, setTransactionId] = useState('');
  const [cardNumber, setCardNumber] = useState('');
  const [cardExpiry, setCardExpiry] = useState('');
  const [loadingCard, setLoadingCard] = useState(false);

  // OTP step
  const [otp, setOtp] = useState('');
  const [loadingOtp, setLoadingOtp] = useState(false);

  // Done
  const [finalKey, setFinalKey] = useState('');
  const [isMock, setIsMock] = useState(false);

  // ── Load data ──────────────────────────────────────────────────────────────

  useEffect(() => {
    getUserLicensePricing()
      .then((res: any) => {
        if (res?.data?.code === 0) setPricing(res.data.data);
      })
      .catch(() => {});
  }, []);

  // ── Step: Plan → create transaction ───────────────────────────────────────

  const handleStartPurchase = async () => {
    if (!licenseName.trim()) {
      message.error('Please enter a license name.');
      return;
    }
    setLoadingCard(true);
    try {
      const res = await createLicensePay(licenseName.trim(), selectedMonths);
      if (res?.data?.code === 0) {
        setTransactionId(res.data.data.transaction_id);
        setIsMock(res.data.data.mock ?? false);
        setStep('card');
      } else {
        message.error(res?.data?.message || 'Failed to initiate payment.');
      }
    } catch {
      message.error('Network error. Please try again.');
    } finally {
      setLoadingCard(false);
    }
  };

  // ── Step: Card → pre-apply → get OTP ──────────────────────────────────────

  const handleCardSubmit = async () => {
    const cleanCard = cardNumber.replace(/\s/g, '');
    if (cleanCard.length < 16) {
      message.error('Please enter a valid 16-digit card number.');
      return;
    }
    if (!cardExpiry.match(/^\d{4}$/)) {
      message.error('Card expiry must be in MMYY format (4 digits).');
      return;
    }
    setLoadingCard(true);
    try {
      const res = await preApplyLicensePay(transactionId, cleanCard, cardExpiry);
      if (res?.data?.code === 0) {
        setStep('otp');
      } else {
        message.error(res?.data?.message || 'Card verification failed.');
      }
    } catch {
      message.error('Network error. Please try again.');
    } finally {
      setLoadingCard(false);
    }
  };

  // ── Step: OTP → confirm payment → get license key ─────────────────────────

  const handleOtpSubmit = async () => {
    if (!otp.trim()) {
      message.error('Please enter the OTP code.');
      return;
    }
    setLoadingOtp(true);
    try {
      const res = await applyLicensePay(transactionId, otp.trim());
      if (res?.data?.code === 0 && res.data.data?.license_key) {
        setFinalKey(res.data.data.license_key);
        setStep('done');
        loadLicenses();
      } else {
        message.error(res?.data?.message || 'OTP verification failed.');
      }
    } catch {
      message.error('Network error. Please try again.');
    } finally {
      setLoadingOtp(false);
    }
  };

  // ── Card input formatter ───────────────────────────────────────────────────

  const formatCardNumber = (val: string) => {
    const digits = val.replace(/\D/g, '').slice(0, 16);
    return digits.replace(/(.{4})/g, '$1 ').trim();
  };

  // ── Price ──────────────────────────────────────────────────────────────────

  const price = selectedMonths === 12 ? pricing.price_12_months : pricing.price_6_months;

  // ─────────────────────────────────────────────────────────────────────────

  return (
    <ProfileSettingWrapperCard
      header={
        <header className="flex flex-col gap-1 w-full">
          <h2 className="text-2xl font-bold tracking-tight text-text-primary flex items-center gap-2">
            <Key className="text-accent-primary" size={24} />
            License Key Purchase
          </h2>
          <p className="text-text-secondary text-sm">
            Buy a license key compatible with your Swipies AI deployment.
          </p>
        </header>
      }
    >
      <div className="h-full overflow-x-hidden overflow-y-auto pb-8 pr-1 mt-6 space-y-6 px-5">

        {/* ── Step: Plan ───────────────────────────────────────────── */}
        {step === 'plan' && (
          <div className="space-y-5 max-w-lg">
            <h3 className="text-base font-semibold text-text-primary">Choose a plan</h3>

            {/* Plan cards */}
            <div className="grid grid-cols-2 gap-4">
              {([6, 12] as const).map((m) => {
                const p = m === 12 ? pricing.price_12_months : pricing.price_6_months;
                const selected = selectedMonths === m;
                return (
                  <button
                    key={m}
                    onClick={() => setSelectedMonths(m)}
                    className={`rounded-xl border p-4 text-left transition-all space-y-1 ${
                      selected
                        ? 'border-accent-primary bg-accent-primary/8 ring-1 ring-accent-primary/40'
                        : 'border-border-default bg-bg-card/20 hover:border-accent-primary/40'
                    }`}
                  >
                    <div className="text-sm font-semibold text-text-primary">{m} months</div>
                    <div className="text-lg font-bold text-accent-primary">{fmt(p)}</div>
                    {m === 12 && (
                      <span className="text-[10px] bg-emerald-500/15 text-emerald-400 px-1.5 py-0.5 rounded font-semibold uppercase tracking-wide">
                        Best value
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* License name */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-text-primary">License label</label>
              <Input
                value={licenseName}
                onChange={(e) => setLicenseName(e.target.value)}
                placeholder="My Swipies License"
              />
              <p className="text-xs text-text-secondary">Used to identify this license.</p>
            </div>

            {/* Total */}
            <div className="flex items-center justify-between rounded-xl border border-border-default bg-bg-card/20 px-4 py-3">
              <span className="text-sm text-text-secondary">Total</span>
              <span className="font-bold text-text-primary">{fmt(price)}</span>
            </div>

            <Button
              className="bg-accent-primary hover:bg-accent-primary/90 text-white w-full gap-2"
              onClick={handleStartPurchase}
              loading={loadingCard}
            >
              <CreditCard size={16} /> Pay with Atmos
            </Button>

            {isMock && (
              <p className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
                ⚠ Sandbox mode — real Atmos credentials not configured. Any 6-digit OTP will work.
              </p>
            )}
          </div>
        )}

        {/* ── Step: Card ───────────────────────────────────────────── */}
        {step === 'card' && (
          <div className="space-y-5 max-w-lg">
            <h3 className="text-base font-semibold text-text-primary flex items-center gap-2">
              <CreditCard size={18} className="text-accent-primary" />
              Enter card details
            </h3>

            {isMock && (
              <p className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
                ⚠ Sandbox mode — any card number and expiry will be accepted. Use any 6-digit OTP next.
              </p>
            )}

            <div className="space-y-3">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-text-primary">Card number</label>
                <Input
                  value={cardNumber}
                  onChange={(e) => setCardNumber(formatCardNumber(e.target.value))}
                  placeholder="0000 0000 0000 0000"
                  maxLength={19}
                  inputMode="numeric"
                />
              </div>
              <div className="space-y-1.5 max-w-[140px]">
                <label className="text-xs font-semibold text-text-primary">Expiry (MMYY)</label>
                <Input
                  value={cardExpiry}
                  onChange={(e) => setCardExpiry(e.target.value.replace(/\D/g, '').slice(0, 4))}
                  placeholder="1228"
                  maxLength={4}
                  inputMode="numeric"
                />
              </div>
            </div>

            <div className="flex items-center justify-between rounded-xl border border-border-default bg-bg-card/20 px-4 py-3">
              <span className="text-sm text-text-secondary">Amount</span>
              <span className="font-bold text-text-primary">{fmt(price)}</span>
            </div>

            <div className="flex gap-3">
              <Button variant="ghost" onClick={() => setStep('plan')}>
                Back
              </Button>
              <Button
                className="bg-accent-primary hover:bg-accent-primary/90 text-white flex-1"
                onClick={handleCardSubmit}
                loading={loadingCard}
              >
                Send OTP
              </Button>
            </div>
          </div>
        )}

        {/* ── Step: OTP ────────────────────────────────────────────── */}
        {step === 'otp' && (
          <div className="space-y-5 max-w-sm">
            <h3 className="text-base font-semibold text-text-primary flex items-center gap-2">
              <LockKeyhole size={18} className="text-accent-primary" />
              Enter OTP
            </h3>
            <p className="text-sm text-text-secondary">
              An SMS confirmation code was sent to your registered phone number.
              {isMock && ' (Sandbox: enter any 6-digit code.)'}
            </p>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-text-primary">OTP code</label>
              <Input
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="123456"
                maxLength={6}
                inputMode="numeric"
                className="text-center text-xl tracking-widest font-mono"
              />
            </div>

            <div className="flex gap-3">
              <Button variant="ghost" onClick={() => setStep('card')}>
                Back
              </Button>
              <Button
                className="bg-accent-primary hover:bg-accent-primary/90 text-white flex-1"
                onClick={handleOtpSubmit}
                loading={loadingOtp}
                disabled={otp.length !== 6}
              >
                Confirm &amp; Get License
              </Button>
            </div>
          </div>
        )}

        {/* ── Step: Done ───────────────────────────────────────────── */}
        {step === 'done' && (
          <div className="space-y-5 max-w-lg">
            {/* Success banner */}
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-6 space-y-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-500/20 rounded-full text-emerald-400">
                  <CheckCircle2 size={24} />
                </div>
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                    Payment Successful
                  </div>
                  <h3 className="text-lg font-bold text-text-primary mt-0.5">
                    License Key Generated!
                  </h3>
                </div>
              </div>
              <p className="text-sm text-text-secondary">
                Your RSA-signed license key is ready. Copy it and activate it on your deployment.
              </p>
            </div>

            {/* Key display */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-text-primary">Your License Key</span>
                <CopyButton value={finalKey} />
              </div>
              <div className="bg-bg-base/80 rounded-xl border border-border-default p-4 font-mono text-xs text-text-secondary break-all leading-relaxed">
                {finalKey}
              </div>
              <p className="text-xs text-text-secondary">
                ⚠ Save this key somewhere safe. It cannot be recovered later.
              </p>
            </div>

            <Button
              variant="ghost"
              className="gap-2"
              onClick={() => {
                setStep('plan');
                setOtp('');
                setCardNumber('');
                setCardExpiry('');
                setTransactionId('');
                setFinalKey('');
                setLicenseName('My Swipies License');
              }}
            >
              <ArrowRight size={14} /> Buy Another License
            </Button>
          </div>
        )}
      </div>
    </ProfileSettingWrapperCard>
  );
};

export default LicensePurchasePage;
