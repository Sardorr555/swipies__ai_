import { BRAND } from '@/constants/branding';
import { Button } from '@/components/ui/button';
import {
  LucideCheck,
  LucideZap,
  LucideArrowLeft,
  CreditCard,
  CheckCircle,
  ShieldCheck,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { Link } from 'react-router';
import { Routes } from '@/routes';
import { useState, useEffect } from 'react';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';

// UZS Formatter
const formatUZS = (amount: number) => {
  return new Intl.NumberFormat('uz-UZ', {
    style: 'currency',
    currency: 'UZS',
    maximumFractionDigits: 0,
  }).format(amount);
};

// Fallback UUID generator
const generateUUID = () => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

const PLANS = {
  free: {
    name: 'Free',
    priceUsd: 0,
    pricePerMonthUzs: 0,
    description: 'Get started with basic features',
    features: [
      '1 Knowledge Base',
      '50 MB Storage',
      '100 Queries/day',
      'Basic Chat Assistant',
      'Community Support',
    ],
    cta: 'Current Plan',
    disabled: true,
  },
  pro: {
    name: 'Pro',
    priceUsd: 29,
    pricePerMonthUzs: 370000,
    description: 'For professionals and small teams',
    features: [
      '10 Knowledge Bases',
      '5 GB Storage',
      'Unlimited Queries',
      'Advanced AI Agents',
      'Priority Support',
      'Custom Branding',
      'API Access',
    ],
    cta: 'Upgrade to Pro',
    disabled: false,
    popular: true,
  },
  enterprise: {
    name: 'Enterprise',
    priceUsd: 99,
    pricePerMonthUzs: 1260000,
    description: 'For organizations with advanced needs',
    features: [
      'Unlimited Knowledge Bases',
      '50 GB Storage',
      'Unlimited Queries',
      'Advanced AI Agents',
      'Dedicated Support',
      'Custom Branding',
      'API Access',
      'SSO & SAML',
      'Audit Logs',
      'SLA Guarantee',
    ],
    cta: 'Upgrade to Enterprise',
    disabled: false,
  },
};

const PERIODS = [
  { months: 1, label: '1 Month', discount: 0, badge: null },
  { months: 6, label: '6 Months', discount: 0.1, badge: '−10%' },
  { months: 12, label: '1 Year', discount: 0.2, badge: '−20%' },
];

export default function PricingPage() {
  const { data: userInfo } = useFetchUserInfo();
  const userEmail = userInfo?.email || '';

  const [selectedPeriod, setSelectedPeriod] = useState(1);
  const [activePlanKey, setActivePlanKey] = useState<'pro' | 'enterprise' | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [step, setStep] = useState<'card' | 'processing_card' | 'otp' | 'processing_otp' | 'success'>('card');
  const [cardNumber, setCardNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [cvc, setCvc] = useState('');
  const [cardName, setCardName] = useState('');
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [transactionId, setTransactionId] = useState<string | null>(null);
  const [maskedPhone, setMaskedPhone] = useState('');
  const [ragflowResult, setRagflowResult] = useState<any>(null);

  const activePlan = activePlanKey ? PLANS[activePlanKey] : null;
  const activePeriod = PERIODS.find((p) => p.months === selectedPeriod)!;

  // Calculations
  const baseAmount = activePlan ? activePlan.pricePerMonthUzs * selectedPeriod : 0;
  const discountAmount = Math.round(baseAmount * activePeriod.discount);
  const finalAmount = baseAmount - discountAmount;

  // Card check
  const cleanCardNumber = cardNumber.replace(/\s/g, '');
  const isLocalCard =
    cleanCardNumber.startsWith('8600') ||
    cleanCardNumber.startsWith('9860') ||
    cleanCardNumber.startsWith('5614') ||
    cleanCardNumber.startsWith('5440');
  const isVisaOrMastercard =
    !isLocalCard && (cleanCardNumber.startsWith('4') || cleanCardNumber.startsWith('5'));

  const handleOpenCheckout = (key: 'pro' | 'enterprise') => {
    setActivePlanKey(key);
    setIsModalOpen(true);
    setStep('card');
    setCardNumber('');
    setExpiry('');
    setCvc('');
    setCardName('');
    setOtp('');
    setError('');
    setRagflowResult(null);
  };

  const handleCardSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (cleanCardNumber.length < 16 || expiry.length < 5) {
      setError('Please enter a valid card number and expiry date');
      return;
    }
    setError('');
    setStep('processing_card');

    try {
      const [month, year] = expiry.split('/');
      const formattedExpiry = `${year}${month}`;

      if (isVisaOrMastercard) {
        if (cvc.length < 3 || cardName.trim().length === 0) {
          setError('CVC and Cardholder Name are required for international cards');
          setStep('card');
          return;
        }

        const res = await fetch('/api/pay/mps', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pan: cleanCardNumber,
            expiry: formattedExpiry,
            amount: finalAmount,
            card_name: cardName,
            cvc2: cvc,
            ext_id: generateUUID(),
          }),
        });
        const txData = await res.json();
        if (!res.ok) throw new Error(txData.error || 'International card payment error');

        if (txData.payload?.redirect_uri) {
          window.location.href = txData.payload.redirect_uri;
          return;
        }
        await triggerProvision();
      } else {
        // Uzcard / Humo
        const createRes = await fetch('/api/pay/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ amount: finalAmount, account: userEmail || 'guest' }),
        });
        const txData = await createRes.json();
        if (!createRes.ok) throw new Error(txData.error || txData.result?.description);

        setTransactionId(txData.transaction_id);

        const preRes = await fetch('/api/pay/pre-apply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            transaction_id: txData.transaction_id,
            card_number: cleanCardNumber,
            expiry: formattedExpiry,
          }),
        });
        const preData = await preRes.json();
        if (!preRes.ok) throw new Error(preData.error || preData.result?.description);

        const phone =
          preData.phone ||
          preData.phone_number ||
          preData.phoneMask ||
          (preData.payload && preData.payload.phone) ||
          '';
        setMaskedPhone(phone);
        setStep('otp');
      }
    } catch (err: any) {
      setError(err.message || 'Payment gateway error. Please try again.');
      setStep('card');
    }
  };

  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.length < 6) {
      setError('Please enter the 6-digit confirmation code');
      return;
    }
    setError('');
    setStep('processing_otp');

    try {
      const res = await fetch('/api/pay/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transaction_id: transactionId, otp }),
      });
      const confirmData = await res.json();
      if (!res.ok) throw new Error(confirmData.error || 'Payment confirmation failed');

      await triggerProvision();
    } catch (err: any) {
      setError(err.message || 'Invalid code or system error.');
      setStep('otp');
    }
  };

  const triggerProvision = async () => {
    try {
      const expiryDate = new Date();
      expiryDate.setDate(expiryDate.getDate() + selectedPeriod * 30);

      const res = await fetch('/api/ragflow/provision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: userEmail,
          plan: activePlan?.name,
          months: selectedPeriod,
          expiryDate: expiryDate.toISOString(),
        }),
      });
      const rfData = await res.json();
      setRagflowResult(rfData);
      setStep('success');
    } catch (err: any) {
      setRagflowResult({ success: false, error: err.message });
      setStep('success');
    }
  };

  const formatCardNumberInput = (val: string) => {
    const v = val.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    const parts = [];
    for (let i = 0; i < v.length; i += 4) {
      parts.push(v.substring(i, i + 4));
    }
    setCardNumber(parts.join(' '));
  };

  const formatExpiryInput = (val: string) => {
    const v = val.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    if (v.length >= 2) {
      setExpiry(v.substring(0, 2) + '/' + v.substring(2, 4));
    } else {
      setExpiry(v);
    }
  };

  return (
    <div className="min-h-screen bg-bg-body p-4 sm:p-6 md:p-8 overflow-y-auto">
      <div className="max-w-6xl mx-auto">
        {/* Back Link */}
        <Link
          to={Routes.Root}
          className="inline-flex items-center gap-2 text-text-secondary hover:text-text-primary mb-6 sm:mb-8 transition-colors text-sm font-medium"
        >
          <LucideArrowLeft className="size-4" />
          Back to Dashboard
        </Link>

        {/* Title Section */}
        <div className="text-center mb-8 sm:mb-12">
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold text-text-primary tracking-tight mb-4">
            Upgrade Your {BRAND.name} Plan
          </h1>
          <p className="text-sm sm:text-base md:text-lg text-text-secondary max-w-2xl mx-auto leading-relaxed">
            Choose the subscription that fits your workload. Pay securely via card using our local and international gateways.
          </p>

          {/* Billing Period Selector */}
          <div className="inline-flex items-center gap-2 bg-bg-component border border-border p-1.5 rounded-xl mt-6 sm:mt-8">
            {PERIODS.map((period) => (
              <button
                key={period.months}
                onClick={() => setSelectedPeriod(period.months)}
                className={`px-3 sm:px-4 py-2 text-xs sm:text-sm font-semibold rounded-lg transition-all relative ${
                  selectedPeriod === period.months
                    ? 'bg-[#478AF5] text-white shadow-sm'
                    : 'text-text-secondary hover:text-text-primary hover:bg-bg-body'
                }`}
              >
                {period.badge && (
                  <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-emerald-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full shadow-sm">
                    {period.badge}
                  </span>
                )}
                {period.label}
              </button>
            ))}
          </div>
        </div>

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8 items-stretch">
          {/* Free Card */}
          <div className="border border-border bg-bg-component rounded-2xl p-6 sm:p-8 flex flex-col justify-between transition-all hover:border-text-secondary">
            <div>
              <div className="mb-6">
                <h3 className="text-xl font-bold text-text-primary mb-1">{PLANS.free.name}</h3>
                <p className="text-sm text-text-secondary">{PLANS.free.description}</p>
              </div>
              <div className="mb-6">
                <span className="text-3xl sm:text-4xl font-extrabold text-text-primary">
                  ${PLANS.free.priceUsd}
                </span>
                <span className="text-text-secondary text-sm">/month</span>
              </div>
              <ul className="space-y-3 mb-8">
                {PLANS.free.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2.5 text-sm text-text-secondary">
                    <LucideCheck className="size-4.5 text-[#42D7E7] shrink-0 mt-0.5" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </div>
            <Button className="w-full" variant="outline" disabled>
              {PLANS.free.cta}
            </Button>
          </div>

          {/* Pro Card */}
          <div className="relative border-[#478AF5] bg-gradient-to-b from-[#478AF5]/5 to-[#42D7E7]/5 rounded-2xl p-6 sm:p-8 flex flex-col justify-between shadow-md transition-all hover:shadow-xl scale-[1.01] md:scale-[1.02]">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="inline-flex items-center gap-1 px-3 py-1 text-xs font-semibold text-white rounded-full bg-gradient-to-r from-[#478AF5] to-[#42D7E7] shadow-sm">
                <LucideZap className="size-3" />
                Most Popular
              </span>
            </div>
            <div>
              <div className="mb-6 mt-2">
                <h3 className="text-xl font-bold text-text-primary mb-1">{PLANS.pro.name}</h3>
                <p className="text-sm text-text-secondary">{PLANS.pro.description}</p>
              </div>
              <div className="mb-6">
                <span className="text-3xl sm:text-4xl font-extrabold text-text-primary">
                  {formatUZS(PLANS.pro.pricePerMonthUzs)}
                </span>
                <span className="text-text-secondary text-sm">/month</span>
                <div className="text-xs text-[#478AF5] font-medium mt-1">
                  ~ ${PLANS.pro.priceUsd} USD
                </div>
              </div>
              <ul className="space-y-3 mb-8">
                {PLANS.pro.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2.5 text-sm text-text-secondary">
                    <LucideCheck className="size-4.5 text-[#42D7E7] shrink-0 mt-0.5" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </div>
            <Button
              className="w-full bg-gradient-to-r from-[#478AF5] to-[#42D7E7] text-white hover:from-[#3a7ae0] hover:to-[#35c5d4] shadow-md border-0"
              onClick={() => handleOpenCheckout('pro')}
            >
              {PLANS.pro.cta}
            </Button>
          </div>

          {/* Enterprise Card */}
          <div className="border border-border bg-bg-component rounded-2xl p-6 sm:p-8 flex flex-col justify-between transition-all hover:border-[#478AF5]">
            <div>
              <div className="mb-6">
                <h3 className="text-xl font-bold text-text-primary mb-1">{PLANS.enterprise.name}</h3>
                <p className="text-sm text-text-secondary">{PLANS.enterprise.description}</p>
              </div>
              <div className="mb-6">
                <span className="text-3xl sm:text-4xl font-extrabold text-text-primary">
                  {formatUZS(PLANS.enterprise.pricePerMonthUzs)}
                </span>
                <span className="text-text-secondary text-sm">/month</span>
                <div className="text-xs text-text-secondary mt-1">
                  ~ ${PLANS.enterprise.priceUsd} USD
                </div>
              </div>
              <ul className="space-y-3 mb-8">
                {PLANS.enterprise.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2.5 text-sm text-text-secondary">
                    <LucideCheck className="size-4.5 text-[#42D7E7] shrink-0 mt-0.5" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </div>
            <Button className="w-full" variant="outline" onClick={() => handleOpenCheckout('enterprise')}>
              {PLANS.enterprise.cta}
            </Button>
          </div>
        </div>

        <p className="text-center text-xs sm:text-sm text-text-secondary mt-12">
          Secure bank processing by Atmos. Cancel or upgrade your plan anytime.
        </p>
      </div>

      {/* Checkout Modal */}
      {isModalOpen && activePlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-bg-component border border-border rounded-2xl w-full max-w-md p-6 sm:p-8 relative flex flex-col shadow-2xl overflow-y-auto max-h-[90vh]">
            {/* Close */}
            {(step === 'card' || step === 'otp') && (
              <button
                onClick={() => setIsModalOpen(false)}
                className="absolute top-4 right-4 text-text-secondary hover:text-text-primary text-2xl p-1 leading-none transition-colors"
              >
                &times;
              </button>
            )}

            {/* Step: Card Details Entry */}
            {(step === 'card' || step === 'processing_card') && (
              <div className="w-full">
                <div className="text-center mb-6">
                  <div className="w-12 h-12 rounded-full bg-[#478AF5]/10 flex items-center justify-center mx-auto mb-3">
                    <CreditCard className="w-6 h-6 text-[#478AF5]" />
                  </div>
                  <h3 className="text-xl sm:text-2xl font-bold text-text-primary">Pay via Atmos</h3>
                  <p className="text-text-secondary text-xs sm:text-sm mt-1">
                    Uzcard, Humo, Visa or Mastercard
                  </p>
                </div>

                {/* Summary Box */}
                <div className="bg-bg-body border border-border rounded-xl p-4 mb-6 text-sm">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-text-secondary">Plan:</span>
                    <span className="font-semibold text-text-primary">
                      {activePlan.name} ({activePeriod.label})
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">Total price:</span>
                    <span className="font-bold text-[#478AF5] text-base sm:text-lg">
                      {formatUZS(finalAmount)}
                    </span>
                  </div>
                </div>

                <form onSubmit={handleCardSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-text-secondary mb-1">
                      Card Number
                    </label>
                    <input
                      type="text"
                      placeholder="8600 0000 0000 0000"
                      value={cardNumber}
                      onChange={(e) => formatCardNumberInput(e.target.value)}
                      maxLength={19}
                      disabled={step === 'processing_card'}
                      className="w-full bg-bg-body border border-border rounded-xl px-4 py-2.5 text-text-primary text-sm sm:text-base focus:outline-none focus:border-[#478AF5] font-mono tracking-wider transition-colors"
                      required
                    />
                  </div>

                  <div className={isVisaOrMastercard ? 'grid grid-cols-2 gap-4' : 'w-full'}>
                    <div>
                      <label className="block text-xs font-semibold text-text-secondary mb-1">
                        Expiry Date
                      </label>
                      <input
                        type="text"
                        placeholder="MM/YY"
                        value={expiry}
                        onChange={(e) => formatExpiryInput(e.target.value)}
                        maxLength={5}
                        disabled={step === 'processing_card'}
                        className="w-full bg-bg-body border border-border rounded-xl px-4 py-2.5 text-text-primary text-sm sm:text-base focus:outline-none focus:border-[#478AF5] font-mono tracking-wider transition-colors"
                        required
                      />
                    </div>

                    {isVisaOrMastercard && (
                      <div>
                        <label className="block text-xs font-semibold text-text-secondary mb-1">
                          CVC
                        </label>
                        <input
                          type="password"
                          placeholder="123"
                          value={cvc}
                          onChange={(e) => setCvc(e.target.value.replace(/\D/g, '').slice(0, 3))}
                          disabled={step === 'processing_card'}
                          className="w-full bg-bg-body border border-border rounded-xl px-4 py-2.5 text-text-primary text-sm sm:text-base focus:outline-none focus:border-[#478AF5] font-mono tracking-wider transition-colors"
                          required
                        />
                      </div>
                    )}
                  </div>

                  {isVisaOrMastercard && (
                    <div>
                      <label className="block text-xs font-semibold text-text-secondary mb-1">
                        Cardholder Name
                      </label>
                      <input
                        type="text"
                        placeholder="JOHN DOE"
                        value={cardName}
                        onChange={(e) => setCardName(e.target.value.toUpperCase())}
                        disabled={step === 'processing_card'}
                        className="w-full bg-bg-body border border-border rounded-xl px-4 py-2.5 text-text-primary text-sm sm:text-base focus:outline-none focus:border-[#478AF5] font-mono tracking-wider transition-colors"
                        required
                      />
                    </div>
                  )}

                  {error && <p className="text-red-500 text-xs sm:text-sm text-center font-medium">{error}</p>}

                  <Button
                    type="submit"
                    disabled={step === 'processing_card'}
                    className="w-full bg-gradient-to-r from-[#478AF5] to-[#42D7E7] text-white py-2.5 sm:py-3 rounded-xl font-bold flex justify-center items-center gap-2 mt-4 hover:scale-[1.01] transition-transform"
                  >
                    {step === 'processing_card' ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      'Pay Now'
                    )}
                  </Button>
                </form>
              </div>
            )}

            {/* Step: OTP SMS Verification */}
            {(step === 'otp' || step === 'processing_otp') && (
              <div className="w-full text-center">
                <div className="w-12 h-12 rounded-full bg-[#478AF5]/10 flex items-center justify-center mx-auto mb-3">
                  <ShieldCheck className="w-6 h-6 text-[#478AF5]" />
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-text-primary">Confirm Payment</h3>
                <p className="text-text-secondary text-xs sm:text-sm mt-2 mb-6">
                  An SMS with a 6-digit verification code was sent to your phone
                  {maskedPhone ? ` (${maskedPhone})` : ''}.
                </p>

                <form onSubmit={handleOtpSubmit} className="space-y-4">
                  <div>
                    <input
                      type="text"
                      placeholder="000000"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').substring(0, 6))}
                      disabled={step === 'processing_otp'}
                      className="w-full bg-bg-body border border-border rounded-xl px-4 py-2.5 text-text-primary text-center text-lg sm:text-xl tracking-[0.3em] sm:tracking-[0.4em] focus:outline-none focus:border-[#478AF5] font-mono transition-colors"
                      required
                    />
                  </div>

                  {error && <p className="text-red-500 text-xs sm:text-sm font-medium">{error}</p>}

                  <Button
                    type="submit"
                    disabled={step === 'processing_otp'}
                    className="w-full bg-gradient-to-r from-[#478AF5] to-[#42D7E7] text-white py-2.5 sm:py-3 rounded-xl font-bold flex justify-center items-center gap-2 hover:scale-[1.01] transition-transform"
                  >
                    {step === 'processing_otp' ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Verifying...
                      </>
                    ) : (
                      'Confirm OTP'
                    )}
                  </Button>

                  {step === 'otp' && (
                    <button
                      type="button"
                      onClick={() => setStep('card')}
                      className="text-text-secondary hover:text-text-primary text-xs font-semibold mt-4 transition-colors"
                    >
                      Cancel and use another card
                    </button>
                  )}
                </form>
              </div>
            )}

            {/* Step: Success Screen */}
            {step === 'success' && (
              <div className="w-full text-center animate-in zoom-in-95 duration-300">
                <div className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mb-4 mx-auto">
                  <CheckCircle className="w-8 h-8 text-emerald-500" />
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-text-primary">Payment Successful!</h3>
                <p className="text-emerald-500 text-xs sm:text-sm font-medium mt-1 mb-6">
                  Your transaction has been processed securely.
                </p>

                {ragflowResult?.success ? (
                  <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4 mb-6 text-left text-xs sm:text-sm">
                    <p className="text-emerald-500 font-bold mb-1">✅ Subscription Activated</p>
                    <p className="text-text-secondary">
                      Plan: <span className="text-text-primary font-semibold">{activePlan.name}</span>
                    </p>
                    <p className="text-text-secondary">
                      Account: <span className="text-text-primary font-semibold">{userEmail}</span>
                    </p>
                  </div>
                ) : (
                  <div className="bg-yellow-500/5 border border-yellow-500/20 rounded-xl p-4 mb-6 text-left text-xs sm:text-sm text-yellow-600">
                    Payment was completed successfully, but there was an activation delay. Please contact support.
                  </div>
                )}

                <Button
                  onClick={() => setIsModalOpen(false)}
                  className="w-full bg-gradient-to-r from-[#478AF5] to-[#42D7E7] text-white py-2.5 sm:py-3 rounded-xl font-bold shadow-md hover:scale-[1.01] transition-transform"
                >
                  Continue to Swipies
                </Button>
              </div>
            )}

            <div className="mt-6 flex items-center justify-center gap-1.5 text-[10px] sm:text-xs text-text-secondary border-t border-border pt-4 w-full">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" /> Protected by Atmos Secure
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
