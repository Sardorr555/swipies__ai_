import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { useSystemConfig } from '@/hooks/use-system-request';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import { 
  getUserLicensePricing,
  createLicensePay,
  preApplyLicensePay,
  applyLicensePay 
} from '@/services/license-service';
import { getAuthorization } from '@/utils/authorization-util';
import { Routes } from '@/routes';
import {
  ArrowLeft,
  Calendar,
  Check,
  CheckCircle2,
  Copy,
  CreditCard,
  Loader2,
  Lock,
  Sparkles,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router';
import message from '@/components/ui/message';

// UZS Formatter
const formatUZS = (amount: number) => {
  return new Intl.NumberFormat('uz-UZ', {
    style: 'currency',
    currency: 'UZS',
    maximumFractionDigits: 0,
  }).format(amount);
};

// USD Formatter
const formatUSD = (amount: number) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount);
};

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

const safeFetchJson = async (url: string, options?: RequestInit) => {
  let res: Response;
  try {
    res = await fetch(url, options);
  } catch (err: any) {
    throw new Error(`Не удалось подключиться к серверу (${err.message || 'Network Error'}). Проверьте подключение.`);
  }

  const text = await res.text();
  let data: any = null;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    if (!res.ok) {
      throw new Error(`Платежный шлюз временно недоступен (Код ${res.status}: ${res.statusText || 'Bad Gateway'}). Убедитесь, что сервис оплаты запущен.`);
    }
    throw new Error(`Некорректный ответ от сервера (${res.status}): ${text.slice(0, 120)}`);
  }

  if (!res.ok) {
    throw new Error(data?.error || data?.result?.description || data?.message || `Ошибка запроса (${res.status})`);
  }
  return data;
};

const checkoutTranslations: Record<string, any> = {
  en: {
    back: 'Go Back',
    checkoutTitle: 'Secure Checkout',
    checkoutSubtitle: 'Complete your purchase securely via card using our local and international gateways.',
    plan: 'Plan',
    duration: 'Duration',
    licenseNameLabel: 'License Name',
    licenseNamePlaceholder: 'e.g. Production Server, Dev Environment',
    price: 'Price',
    months: '{{count}} month',
    months_plural: '{{count}} months',
    totalPrice: 'Total Price',
    securePayment: 'Secure Payment Processing',
    cardNumber: 'Card Number',
    expiryDate: 'Expiry Date',
    cvc: 'CVC / CVV',
    cardholderName: 'Cardholder Name',
    payButton: 'Pay Now',
    processing: 'Processing transaction...',
    otpTitle: 'Verify Payment',
    otpSubtitle: 'An SMS verification code has been sent to your phone',
    otpLabel: 'Verification Code',
    otpPlaceholder: '000 000',
    verifyButton: 'Verify & Complete',
    cancelUseAnother: 'Cancel payment',
    successTitle: 'Payment Successful!',
    successSubtitle: 'Your transaction has been processed securely. Your plan has been updated.',
    licenseKeyLabel: 'Your License Key',
    licenseCopySuccess: 'License key copied to clipboard!',
    licenseCopyBtn: 'Copy License Key',
    continueBtn: 'Continue to Dashboard',
    unlimited: 'Unlimited',
    selfHostedUnlimited: 'Self-hosted (Unlimited)',
    periodDiscount: 'Billed total ({{discount}}% discount applied)',
  },
  ru: {
    back: 'Назад',
    checkoutTitle: 'Безопасная оплата',
    checkoutSubtitle: 'Завершите покупку безопасно картой через наши локальные и международные шлюзы.',
    plan: 'Тариф',
    duration: 'Срок действия',
    licenseNameLabel: 'Имя лицензии',
    licenseNamePlaceholder: 'например, Основной сервер, Разработка',
    price: 'Цена',
    months: '{{count}} месяц',
    months_plural: '{{count}} мес.',
    totalPrice: 'Итого к оплате',
    securePayment: 'Защищенная обработка карт',
    cardNumber: 'Номер карты',
    expiryDate: 'Срок действия',
    cvc: 'CVC / CVV код',
    cardholderName: 'Имя держателя карты',
    payButton: 'Оплатить сейчас',
    processing: 'Обработка транзакции...',
    otpTitle: 'Подтверждение платежа',
    otpSubtitle: 'SMS-код подтверждения был отправлен на ваш номер телефона',
    otpLabel: 'Код подтверждения',
    otpPlaceholder: '000 000',
    verifyButton: 'Подтвердить и завершить',
    cancelUseAnother: 'Отменить платеж',
    successTitle: 'Оплата прошла успешно!',
    successSubtitle: 'Ваша транзакция была безопасно обработана. Тариф обновлен.',
    licenseKeyLabel: 'Ваш лицензионный ключ',
    licenseCopySuccess: 'Лицензионный ключ скопирован в буфер обмена!',
    licenseCopyBtn: 'Копировать ключ',
    continueBtn: 'Перейти в личный кабинет',
    unlimited: 'Без ограничений',
    selfHostedUnlimited: 'Локальное хранилище (Без лимита)',
    periodDiscount: 'Итого (скидка {{discount}}% учтена)',
  },
  uz: {
    back: 'Orqaga',
    checkoutTitle: 'Xavfsiz to‘lov',
    checkoutSubtitle: 'Mahalliy va xalqaro to‘lov tizimlari orqali karta bilan xavfsiz to‘lovni bajaring.',
    plan: 'Tarif',
    duration: 'Amal qilish muddati',
    licenseNameLabel: 'Litsenziya nomi',
    licenseNamePlaceholder: 'masalan, Asosiy server, Sinov muhiti',
    price: 'Narxi',
    months: '{{count}} oy',
    months_plural: '{{count}} oy',
    totalPrice: 'Jami to‘lov',
    securePayment: 'Xavfsiz karta to‘lovlari',
    cardNumber: 'Karta raqami',
    expiryDate: 'Amal qilish muddati',
    cvc: 'CVC / CVV kodi',
    cardholderName: 'Karta egasining ismi',
    payButton: 'Hozir to‘lash',
    processing: 'Tranzaksiya bajarilmoqda...',
    otpTitle: 'To‘lovni tasdiqlash',
    otpSubtitle: 'Telefoningizga tasdiqlash kodi yozilgan SMS yuborildi',
    otpLabel: 'Tasdiqlash kodi',
    otpPlaceholder: '000 000',
    verifyButton: 'Tasdiqlash va yakunlash',
    cancelUseAnother: 'To‘lovni bekor qilish',
    successTitle: 'To‘lov muvaffaqiyatli bajarildi!',
    successSubtitle: 'Tranzaksiyangiz xavfsiz tarzda amalga oshirildi. Tarif yangilandi.',
    licenseKeyLabel: 'Litsenziya kalitingiz',
    licenseCopySuccess: 'Litsenziya kaliti nusxalandi!',
    licenseCopyBtn: 'Kalitni nusxalash',
    continueBtn: 'Boshqaruv paneliga o‘tish',
    unlimited: 'Cheksiz',
    selfHostedUnlimited: 'Lokal xotira (Cheksiz)',
    periodDiscount: 'Jami ({{discount}}% chegirma hisobga olindi)',
  },
};

export default function CheckoutPage() {
  const { i18n } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Route query parameters
  const planQuery = (searchParams.get('plan') || 'plus').toLowerCase() as 'plus' | 'pro' | 'license';
  const periodQuery = Number(searchParams.get('period') || '1');

  // Translation helpers
  const currentLang = i18n.language || 'en';
  const lang = checkoutTranslations[currentLang]
    ? currentLang
    : currentLang.startsWith('ru')
      ? 'ru'
      : currentLang.startsWith('uz')
        ? 'uz'
        : 'en';
  const tLocal = checkoutTranslations[lang];

  // User Data
  const { data: userInfo, loading: userLoading } = useFetchUserInfo();
  const userEmail = userInfo?.email || '';

  // Pricing configs
  const { config, loading: configLoading } = useSystemConfig();
  const [licensePricing, setLicensePricing] = useState<any>(null);
  const [pricingLoading, setPricingLoading] = useState(false);

  // States
  const [selectedPeriod, setSelectedPeriod] = useState(periodQuery);
  const [licenseName, setLicenseName] = useState('');
  const [cardNumber, setCardNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [cvc, setCvc] = useState('');
  const [cardName, setCardName] = useState('');
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [payingLoading, setPayingLoading] = useState(false);
  const [transactionId, setTransactionId] = useState<string | null>(null);
  const [maskedPhone, setMaskedPhone] = useState('');
  const [successResult, setSuccessResult] = useState<any>(null);
  const [step, setStep] = useState<'card' | 'otp' | 'success'>('card');
  const [copied, setCopied] = useState(false);

  // Fetch dynamic license prices
  useEffect(() => {
    if (planQuery === 'license') {
      setPricingLoading(true);
      getUserLicensePricing()
        .then((res) => {
          if (res?.data?.code === 0 && res.data.data) {
            setLicensePricing(res.data.data);
          }
        })
        .catch((err) => console.error('Failed to fetch license prices', err))
        .finally(() => setPricingLoading(false));
    }
  }, [planQuery]);

  // Uzbek user locale check
  const isUzbekistanUser = (() => {
    if (userLoading || !userInfo) return false;
    const phone = userInfo.phone || userInfo.phone_number || '';
    if (phone) {
      const cleanPhone = phone.replace(/[^\d+]/g, '');
      if (cleanPhone.startsWith('+998') || cleanPhone.startsWith('998')) {
        return true;
      }
    }
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (tz === 'Asia/Tashkent') return true;
    } catch {
      // Ignore
    }
    const langs = navigator.languages || [navigator.language];
    if (langs.some((l) => l.toLowerCase().includes('uz'))) return true;
    return false;
  })();

  // Calculate pricing values
  const getPlanBasePrice = () => {
    if (planQuery === 'license') {
      if (!licensePricing) return 0;
      if (selectedPeriod === 6) return Number(licensePricing.price_6_months || 2470000);
      if (selectedPeriod === 12) return Number(licensePricing.price_12_months || 4500000);
      return selectedPeriod * Number(licensePricing.price_per_month_custom || 450000);
    }

    const pricing = config?.pricing || {};
    if (planQuery === 'pro') {
      return isUzbekistanUser
        ? Number(pricing.pro_uzs || 400000)
        : Number(pricing.pro_usd || 40);
    }
    // plus
    return isUzbekistanUser
      ? Number(pricing.plus_uzs || 199000)
      : Number(pricing.plus_usd || 20);
  };

  const basePricePerMonth = getPlanBasePrice();

  const getDiscountRate = () => {
    if (planQuery === 'license') return 0; // license prices are flat/pre-calculated in admin
    if (selectedPeriod === 6) return 0.1; // 10%
    if (selectedPeriod === 12) return 0.2; // 20%
    return 0;
  };

  const discountRate = getDiscountRate();
  const subtotal = planQuery === 'license' ? basePricePerMonth : basePricePerMonth * selectedPeriod;
  const discountAmount = planQuery === 'license' ? 0 : subtotal * discountRate;
  const finalAmount = subtotal - discountAmount;

  // Formatting helper
  const renderPrice = (amount: number) => {
    if (planQuery === 'license') return formatUZS(amount); // License is always billed in UZS via Atmos
    return isUzbekistanUser ? formatUZS(amount) : formatUSD(amount);
  };

  // Card Brand Detection
  const cleanCardNumber = cardNumber.replace(/[^0-9]/g, '');
  const isLocalCard =
    cleanCardNumber.startsWith('8600') ||
    cleanCardNumber.startsWith('9860') ||
    cleanCardNumber.startsWith('5614') ||
    cleanCardNumber.startsWith('5440');
  
  const isVisaOrMastercard =
    !isUzbekistanUser ||
    (cleanCardNumber.length > 0 && !isLocalCard && (cleanCardNumber.startsWith('4') || cleanCardNumber.startsWith('5')));

  const getCardBrand = () => {
    if (cleanCardNumber.startsWith('8600')) return 'UZCARD';
    if (cleanCardNumber.startsWith('9860')) return 'HUMO';
    if (cleanCardNumber.startsWith('4')) return 'VISA';
    if (cleanCardNumber.startsWith('5')) return 'MASTERCARD';
    return 'CARD';
  };

  // Format Card Number
  const handleCardNumberChange = (val: string) => {
    const v = val.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    const parts = [];
    for (let i = 0; i < v.length; i += 4) {
      parts.push(v.substring(i, i + 4));
    }
    setCardNumber(parts.join(' '));
  };

  // Format Expiry
  const handleExpiryChange = (val: string) => {
    const v = val.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    if (v.length >= 2) {
      setExpiry(v.substring(0, 2) + '/' + v.substring(2, 4));
    } else {
      setExpiry(v);
    }
  };

  const handleCopy = () => {
    if (successResult?.licenseKey) {
      navigator.clipboard.writeText(successResult.licenseKey);
      setCopied(true);
      message.success(tLocal.licenseCopySuccess);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleCardSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (planQuery === 'license' && !licenseName.trim()) {
      setError(tLocal.licenseNameLabel + ' is required');
      return;
    }
    if (cleanCardNumber.length !== 16 || expiry.length < 5) {
      setError('Please enter a valid 16-digit card number and expiry date (MM/YY)');
      return;
    }
    setError('');
    setPayingLoading(true);

    try {
      const [month, year] = expiry.split('/');
      const formattedExpiry = `${year}${month}`;
      const USD_RATE = 13000;

      if (isVisaOrMastercard) {
        if (cvc.length < 3 || cardName.trim().length === 0) {
          setError('CVC and Cardholder Name are required for international cards');
          setPayingLoading(false);
          return;
        }

        // MPS Payment (Visa/Mastercard)
        const mpsAmount = isUzbekistanUser || planQuery === 'license'
          ? finalAmount
          : Math.round(finalAmount * USD_RATE);

        const txData = await safeFetchJson('/api/pay/mps', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pan: cleanCardNumber,
            expiry: formattedExpiry,
            amount: mpsAmount,
            card_name: cardName,
            cvc2: cvc,
            ext_id: generateUUID(),
          }),
        });

        if (txData.payload?.redirect_uri) {
          window.location.href = txData.payload.redirect_uri;
          return;
        }

        await triggerProvision();
      } else {
        // Local Uzcard / Humo payment via Atmos
        if (planQuery === 'license') {
          // Use Flask backend API
          const createRes = await createLicensePay(licenseName, selectedPeriod);
          if (createRes?.data?.code !== 0) {
            throw new Error(createRes?.data?.message || 'Payment init failed');
          }
          const txData = createRes.data.data;
          setTransactionId(txData.transaction_id);

          const preRes = await preApplyLicensePay(txData.transaction_id, cleanCardNumber, formattedExpiry);
          if (preRes?.data?.code !== 0) {
            throw new Error(preRes?.data?.message || 'Card validation failed');
          }
          const preData = preRes.data.data;
          const phone = preData.phone || preData.phone_number || preData.phoneMask || (preData.payload && preData.payload.phone) || '';
          setMaskedPhone(phone);
          setStep('otp');
        } else {
          // Use Node.js payment server
          const txData = await safeFetchJson('/api/pay/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              amount: finalAmount,
              account: userEmail || 'guest',
            }),
          });

          setTransactionId(txData.transaction_id);

          const preData = await safeFetchJson('/api/pay/pre-apply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              transaction_id: txData.transaction_id,
              card_number: cleanCardNumber,
              expiry: formattedExpiry,
            }),
          });

          const phone = preData.phone || preData.phone_number || preData.phoneMask || (preData.payload && preData.payload.phone) || '';
          setMaskedPhone(phone);
          setStep('otp');
        }
      }
    } catch (err: any) {
      setError(err.message || 'Payment processing failed. Please try again.');
    } finally {
      setPayingLoading(false);
    }
  };

  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.length < 6) {
      setError('Please enter the 6-digit confirmation code');
      return;
    }
    setError('');
    setPayingLoading(true);

    try {
      if (planQuery === 'license') {
        // Use Flask backend API
        const confirmRes = await applyLicensePay(transactionId || '', otp);
        if (confirmRes?.data?.code !== 0) {
          throw new Error(confirmRes?.data?.message || 'Payment verification failed');
        }
        const confirmData = confirmRes.data.data;
        // In Flask backend, when payment is successful it returns { success: true, license_key: key }
        setSuccessResult({
          success: true,
          licenseKey: confirmData.license_key
        });
        setStep('success');
        // Use Node.js payment server
        const applyRes = await safeFetchJson('/api/pay/apply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            transaction_id: transactionId,
            otp,
            email: userEmail,
            plan: planQuery,
            months: selectedPeriod,
            license_name: planQuery === 'license' ? licenseName : undefined,
          }),
        });

        setSuccessResult(applyRes.provision || { success: true });
        setStep('success');
      }
    } catch (err: any) {
      setError(err.message || 'Invalid verification code. Please try again.');
    } finally {
      setPayingLoading(false);
    }
  };

  const isLoading = userLoading || configLoading || pricingLoading;

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-100 gap-3">
        <Loader2 className="size-10 animate-spin text-indigo-400" />
        <span className="text-sm opacity-60">Preparing checkout environment...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500/30">
      {/* Background Mesh Gradients */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-900/10 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-violet-900/10 blur-[120px]" />
      </div>

      {/* Header Bar */}
      <header className="relative z-10 w-full max-w-7xl mx-auto px-6 py-5 flex items-center justify-between border-b border-slate-900/80 backdrop-blur-md">
        <button
          onClick={() => navigate(planQuery === 'license' ? `/user-setting${Routes.License}` : Routes.Pricing)}
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 transition-all group"
        >
          <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
          {tLocal.back}
        </button>
        <div className="flex items-center gap-1.5">
          <Sparkles className="text-indigo-400 size-5" />
          <span className="font-extrabold tracking-tight text-white text-base">SWIPIES <span className="text-indigo-400 text-xs font-medium">PAY</span></span>
        </div>
      </header>

      {/* Main Checkout container */}
      <main className="relative z-10 flex-1 w-full max-w-7xl mx-auto px-6 py-12 flex flex-col lg:flex-row gap-12 items-stretch">
        
        {step !== 'success' ? (
          <>
            {/* Left Column: Order Summary */}
            <div className="flex-1 space-y-8 flex flex-col justify-between">
              <div>
                <h1 className="text-3xl font-extrabold text-white tracking-tight">{tLocal.checkoutTitle}</h1>
                <p className="text-sm text-slate-400 mt-2 max-w-lg">{tLocal.checkoutSubtitle}</p>

                {/* Plan Info Card */}
                <Card className="border border-slate-900 bg-slate-900/20 backdrop-blur-md mt-8 overflow-hidden relative">
                  <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
                    <CreditCard size={120} className="text-indigo-400" />
                  </div>
                  <CardContent className="p-6 space-y-5">
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-[10px] font-bold tracking-widest text-indigo-400 uppercase bg-indigo-400/10 px-2.5 py-1 rounded-full">
                          {tLocal.plan}
                        </span>
                        <h3 className="text-2xl font-black text-white mt-2 capitalize">
                          {planQuery === 'license' ? 'Self-Hosted License' : `${planQuery} Plan`}
                        </h3>
                      </div>
                      <div className="text-right">
                        <span className="text-xs text-slate-400">{tLocal.price}</span>
                        <div className="text-xl font-bold text-white mt-0.5">
                          {renderPrice(basePricePerMonth)}
                          {planQuery !== 'license' && <span className="text-xs text-slate-500 font-normal">/mo</span>}
                        </div>
                      </div>
                    </div>

                    {/* Period Selector */}
                    <div className="space-y-2 pt-4 border-t border-slate-900">
                      <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{tLocal.duration}</label>
                      <div className="grid grid-cols-3 gap-2">
                        {planQuery === 'license' ? (
                          // License Durations
                          <>
                            <button
                              onClick={() => setSelectedPeriod(6)}
                              className={`py-2 px-3 rounded-lg border text-xs font-semibold transition-all ${
                                selectedPeriod === 6
                                  ? 'bg-indigo-600/10 border-indigo-500 text-indigo-400 shadow-md shadow-indigo-500/5'
                                  : 'bg-slate-900/40 border-slate-900 text-slate-400 hover:border-slate-800'
                              }`}
                            >
                              6 Months
                            </button>
                            <button
                              onClick={() => setSelectedPeriod(12)}
                              className={`py-2 px-3 rounded-lg border text-xs font-semibold transition-all ${
                                selectedPeriod === 12
                                  ? 'bg-indigo-600/10 border-indigo-500 text-indigo-400 shadow-md shadow-indigo-500/5'
                                  : 'bg-slate-900/40 border-slate-900 text-slate-400 hover:border-slate-800'
                              }`}
                            >
                              12 Months
                            </button>
                          </>
                        ) : (
                          // Subscription Durations
                          <>
                            <button
                              onClick={() => setSelectedPeriod(1)}
                              className={`py-2 px-3 rounded-lg border text-xs font-semibold transition-all ${
                                selectedPeriod === 1
                                  ? 'bg-indigo-600/10 border-indigo-500 text-indigo-400 shadow-md shadow-indigo-500/5'
                                  : 'bg-slate-900/40 border-slate-900 text-slate-400 hover:border-slate-800'
                              }`}
                            >
                              1 Month
                            </button>
                            <button
                              onClick={() => setSelectedPeriod(6)}
                              className={`py-2 px-3 rounded-lg border text-xs font-semibold transition-all relative ${
                                selectedPeriod === 6
                                  ? 'bg-indigo-600/10 border-indigo-500 text-indigo-400 shadow-md shadow-indigo-500/5'
                                  : 'bg-slate-900/40 border-slate-900 text-slate-400 hover:border-slate-800'
                              }`}
                            >
                              6 Months
                              <span className="absolute -top-2 right-1 px-1 py-0.5 text-[8px] font-bold bg-indigo-500 text-white rounded">
                                -10%
                              </span>
                            </button>
                            <button
                              onClick={() => setSelectedPeriod(12)}
                              className={`py-2 px-3 rounded-lg border text-xs font-semibold transition-all relative ${
                                selectedPeriod === 12
                                  ? 'bg-indigo-600/10 border-indigo-500 text-indigo-400 shadow-md shadow-indigo-500/5'
                                  : 'bg-slate-900/40 border-slate-900 text-slate-400 hover:border-slate-800'
                              }`}
                            >
                              12 Months
                              <span className="absolute -top-2 right-1 px-1 py-0.5 text-[8px] font-bold bg-indigo-500 text-white rounded">
                                -20%
                              </span>
                            </button>
                          </>
                        )}
                      </div>
                    </div>

                    {/* License key name (For license plan only) */}
                    {planQuery === 'license' && (
                      <div className="space-y-2 pt-4 border-t border-slate-900">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                          {tLocal.licenseNameLabel} <span className="text-rose-500">*</span>
                        </label>
                        <Input
                          placeholder={tLocal.licenseNamePlaceholder}
                          value={licenseName}
                          onChange={(e) => setLicenseName(e.target.value)}
                          className="bg-slate-950/60 border-slate-800/80 text-white placeholder:text-slate-600"
                        />
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Price Breakdown Footer */}
              <div className="border-t border-slate-900 pt-6 space-y-4">
                {planQuery !== 'license' && selectedPeriod > 1 && (
                  <div className="flex justify-between text-sm text-slate-400">
                    <span>
                      {tLocal.periodDiscount.replace('{{discount}}', (discountRate * 100).toString())}
                    </span>
                    <span className="line-through text-slate-600">
                      {renderPrice(subtotal)}
                    </span>
                  </div>
                )}
                <div className="flex justify-between items-baseline">
                  <span className="text-lg font-bold text-white">{tLocal.totalPrice}</span>
                  <span className="text-3xl font-black text-indigo-400 tracking-tight">
                    {renderPrice(finalAmount)}
                  </span>
                </div>
              </div>
            </div>

            {/* Right Column: Payment Form */}
            <div className="flex-1 flex flex-col justify-center">
              <Card className="border border-slate-900 bg-slate-900/10 backdrop-blur-md p-6 sm:p-8 space-y-6">
                <div className="flex items-center gap-2 border-b border-slate-900 pb-4">
                  <Lock size={16} className="text-emerald-500" />
                  <h2 className="text-sm font-bold tracking-wider text-slate-300 uppercase">{tLocal.securePayment}</h2>
                </div>

                {step === 'card' && (
                  <form onSubmit={handleCardSubmit} className="space-y-6">
                    {error && (
                      <div className="p-3 text-xs bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg">
                        {error}
                      </div>
                    )}

                    {/* Dynamic Virtual Card Preview */}
                    <div className="border border-slate-800 rounded-2xl p-6 bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-950 shadow-xl relative overflow-hidden aspect-[1.586/1] flex flex-col justify-between text-white">
                      <div className="flex justify-between items-center z-10">
                        <CreditCard size={32} className="text-indigo-400" />
                        <span className="text-[10px] tracking-widest opacity-80 font-extrabold text-slate-300">
                          {getCardBrand()}
                        </span>
                      </div>
                      
                      <div className="space-y-2 z-10">
                        <div className="text-[9px] tracking-widest text-slate-400 uppercase font-bold">Card Number</div>
                        <div className="font-mono text-xl sm:text-2xl tracking-widest text-white truncate min-h-[32px]">
                          {cardNumber || '•••• •••• •••• ••••'}
                        </div>
                      </div>

                      <div className="flex justify-between items-end z-10">
                        <div className="space-y-1">
                          <div className="text-[8px] tracking-widest text-slate-400 uppercase font-bold">Cardholder</div>
                          <div className="font-sans text-xs uppercase tracking-wider text-slate-200 truncate max-w-[200px]">
                            {cardName || 'YOUR NICKNAME'}
                          </div>
                        </div>
                        <div className="space-y-1 text-right">
                          <div className="text-[8px] tracking-widest text-slate-400 uppercase font-bold">Expiry</div>
                          <div className="font-mono text-sm text-slate-200">
                            {expiry || 'MM/YY'}
                          </div>
                        </div>
                      </div>

                      {/* Card Hologram chip decoration */}
                      <div className="absolute top-1/2 left-8 -translate-y-1/2 w-10 h-8 bg-gradient-to-br from-yellow-600/30 to-amber-500/10 rounded-md border border-amber-500/20 opacity-30" />
                    </div>

                    {/* Form Inputs */}
                    <div className="space-y-4">
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-slate-400 uppercase">{tLocal.cardNumber}</label>
                        <Input
                          placeholder="8600 0000 0000 0000"
                          value={cardNumber}
                          onChange={(e) => handleCardNumberChange(e.target.value)}
                          maxLength={19}
                          className="bg-slate-950/40 border-slate-800/80 text-white placeholder:text-slate-700 font-mono"
                          required
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1">
                          <label className="text-xs font-semibold text-slate-400 uppercase">{tLocal.expiryDate}</label>
                          <Input
                            placeholder="MM/YY"
                            value={expiry}
                            onChange={(e) => handleExpiryChange(e.target.value)}
                            maxLength={5}
                            className="bg-slate-950/40 border-slate-800/80 text-white placeholder:text-slate-700 font-mono text-center"
                            required
                          />
                        </div>
                        {isVisaOrMastercard && (
                          <div className="space-y-1">
                            <label className="text-xs font-semibold text-slate-400 uppercase">{tLocal.cvc}</label>
                            <Input
                              type="password"
                              placeholder="•••"
                              value={cvc}
                              onChange={(e) => setCvc(e.target.value.replace(/[^0-9]/g, ''))}
                              maxLength={4}
                              className="bg-slate-950/40 border-slate-800/80 text-white placeholder:text-slate-700 text-center"
                              required
                            />
                          </div>
                        )}
                      </div>

                      {isVisaOrMastercard && (
                        <div className="space-y-1">
                          <label className="text-xs font-semibold text-slate-400 uppercase">{tLocal.cardholderName}</label>
                          <Input
                            placeholder="JOHN DOE"
                            value={cardName}
                            onChange={(e) => setCardName(e.target.value.toUpperCase())}
                            className="bg-slate-950/40 border-slate-800/80 text-white placeholder:text-slate-700"
                            required
                          />
                        </div>
                      )}
                    </div>

                    <Button
                      type="submit"
                      disabled={payingLoading}
                      className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-900 text-white font-bold py-3 rounded-xl transition-all shadow-lg shadow-indigo-600/10 flex items-center justify-center gap-2"
                    >
                      {payingLoading ? (
                        <>
                          <Loader2 className="animate-spin size-4" />
                          {tLocal.processing}
                        </>
                      ) : (
                        <>
                          <Lock size={14} />
                          {tLocal.payButton}
                        </>
                      )}
                    </Button>
                  </form>
                )}

                {step === 'otp' && (
                  <form onSubmit={handleOtpSubmit} className="space-y-6">
                    <div className="text-center space-y-2">
                      <h3 className="text-lg font-bold text-white">{tLocal.otpTitle}</h3>
                      <p className="text-xs text-slate-400">{tLocal.otpSubtitle} {maskedPhone && <span className="font-semibold text-slate-300">{maskedPhone}</span>}</p>
                    </div>

                    {error && (
                      <div className="p-3 text-xs bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg">
                        {error}
                      </div>
                    )}

                    <div className="space-y-2">
                      <label className="text-xs font-semibold text-slate-400 uppercase block text-center">{tLocal.otpLabel}</label>
                      <div className="flex justify-center">
                        <Input
                          placeholder={tLocal.otpPlaceholder}
                          value={otp}
                          onChange={(e) => setOtp(e.target.value.replace(/[^0-9]/g, ''))}
                          maxLength={6}
                          className="bg-slate-950/40 border-slate-800/80 text-white placeholder:text-slate-700 font-mono text-center text-2xl tracking-widest max-w-[200px]"
                          required
                          autoFocus
                        />
                      </div>
                    </div>

                    <div className="space-y-3 pt-2">
                      <Button
                        type="submit"
                        disabled={payingLoading}
                        className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-900 text-white font-bold py-3 rounded-xl transition-all flex items-center justify-center gap-2"
                      >
                        {payingLoading ? (
                          <>
                            <Loader2 className="animate-spin size-4" />
                            {tLocal.processing}
                          </>
                        ) : (
                          tLocal.verifyButton
                        )}
                      </Button>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => {
                          setStep('card');
                          setOtp('');
                          setError('');
                        }}
                        className="w-full bg-transparent border border-slate-900 hover:bg-slate-900 text-slate-400 py-3 rounded-xl"
                      >
                        {tLocal.cancelUseAnother}
                      </Button>
                    </div>
                  </form>
                )}
              </Card>
            </div>
          </>
        ) : (
          /* SUCCESS STATE PANEL */
          <div className="w-full max-w-xl mx-auto flex flex-col items-center justify-center text-center py-12 space-y-8 relative">
            <div className="absolute inset-0 pointer-events-none overflow-hidden z-0 flex items-center justify-center">
              <div className="w-[300px] h-[300px] rounded-full bg-indigo-500/10 blur-[80px]" />
            </div>

            <div className="relative z-10 space-y-6">
              <div className="inline-flex items-center justify-center p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full animate-bounce">
                <CheckCircle2 size={48} />
              </div>

              <div className="space-y-2">
                <h1 className="text-3xl font-extrabold text-white tracking-tight">{tLocal.successTitle}</h1>
                <p className="text-sm text-slate-400">{tLocal.successSubtitle}</p>
              </div>

              {successResult?.licenseKey ? (
                /* License Key Success View */
                <div className="bg-slate-900/55 border border-slate-850 p-6 rounded-2xl space-y-4 max-w-lg mx-auto backdrop-blur-md">
                  <div className="text-left space-y-1">
                    <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">
                      {tLocal.licenseKeyLabel}
                    </span>
                    <div className="flex gap-2 mt-2">
                      <div className="flex-1 bg-slate-950 p-3 rounded-xl font-mono text-sm text-slate-200 select-all break-all border border-slate-900">
                        {successResult.licenseKey}
                      </div>
                      <Button
                        onClick={handleCopy}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white shrink-0 p-3 rounded-xl h-auto"
                      >
                        {copied ? <Check size={16} /> : <Copy size={16} />}
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                /* Account Subscription Upgrade View */
                <div className="bg-slate-900/20 border border-slate-900 p-6 rounded-2xl max-w-sm mx-auto backdrop-blur-sm">
                  <div className="flex items-center gap-3 text-left">
                    <div className="p-2.5 bg-indigo-500/10 rounded-xl text-indigo-400">
                      <Calendar size={20} />
                    </div>
                    <div>
                      <div className="text-[9px] font-bold text-indigo-400 uppercase tracking-wider">Plan Activated</div>
                      <div className="font-bold text-white text-base capitalize mt-0.5">{planQuery} Plan</div>
                    </div>
                  </div>
                </div>
              )}

              <div className="pt-4">
                <Button
                  onClick={() => navigate(planQuery === 'license' ? `/user-setting${Routes.License}` : `/user-setting${Routes.Subscription}`)}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-8 py-3.5 rounded-xl transition-all shadow-lg shadow-indigo-600/10 w-full sm:w-auto"
                >
                  {tLocal.continueBtn}
                </Button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer bar */}
      <footer className="relative z-10 w-full py-6 text-center border-t border-slate-900/80 bg-slate-950/40 text-[10px] sm:text-xs text-slate-500">
        All payments are protected and processed via Atmos secure gateway.
      </footer>
    </div>
  );
}
