import React, { useState, useEffect, useRef } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  CreditCard,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  Lock,
  ArrowLeft,
  Loader2,
  Sparkles,
  Zap,
  RefreshCw,
  Clock,
  Check,
  ExternalLink,
  Tag,
  RadioGroup,
} from 'lucide-react';
import paymentService from '@/services/payment-service';
import adService from '@/services/ad-service';
import message from '@/components/ui/message';

export interface AtmosPaymentModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  purpose: 'subscription_upgrade' | 'advertiser_deposit';
  planId?: 'plus' | 'pro' | 'enterprise';
  advertiserId?: string;
  amountUsd?: number;
  onSuccess?: (result: any) => void;
}

const EXCHANGE_RATE = 12800; // 1 USD = 12,800 UZS

export function AtmosPaymentModal({
  open,
  onOpenChange,
  purpose,
  planId = 'pro',
  advertiserId,
  amountUsd = 29.99,
  onSuccess,
}: AtmosPaymentModalProps) {
  // Navigation: 'choice' (Hosted Checkout vs Direct) | 'direct_card' | 'direct_otp' | 'waiting_hosted' | 'success'
  const [step, setStep] = useState<'checkout' | 'card' | 'otp' | 'waiting_hosted' | 'success'>('checkout');
  const [cardNumber, setCardNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [orderId, setOrderId] = useState('');
  const [checkoutUrl, setCheckoutUrl] = useState('');
  const [phoneMasked, setPhoneMasked] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [isSms102Error, setIsSms102Error] = useState(false);
  const [successData, setSuccessData] = useState<any>(null);

  // Promo Code State
  const [promoCodeInput, setPromoCodeInput] = useState('');
  const [isValidatingPromo, setIsValidatingPromo] = useState(false);
  const [appliedPromo, setAppliedPromo] = useState<any | null>(null);

  // OTP Countdown timer
  const [countdown, setCountdown] = useState(60);
  const timerRef = useRef<any>(null);
  const pollingRef = useRef<any>(null);

  // Computed amounts
  const baseUsd =
    purpose === 'subscription_upgrade'
      ? planId === 'plus'
        ? 9.99
        : planId === 'enterprise'
        ? 99.0
        : 29.99
      : amountUsd || 50.0;

  const finalUsd = appliedPromo ? appliedPromo.final_amount_usd : baseUsd;
  const computedUzs = Math.round(finalUsd * EXCHANGE_RATE);

  useEffect(() => {
    if (open) {
      setStep('checkout');
      setCardNumber('');
      setExpiry('');
      setOtp('');
      setErrorMessage('');
      setIsSms102Error(false);
      setOrderId('');
      setCheckoutUrl('');
      setSuccessData(null);
      setPromoCodeInput('');
      setAppliedPromo(null);
      setCountdown(60);
      if (timerRef.current) clearInterval(timerRef.current);
      if (pollingRef.current) clearInterval(pollingRef.current);
    } else {
      if (pollingRef.current) clearInterval(pollingRef.current);
    }
  }, [open]);

  // Countdown effect when in OTP step
  useEffect(() => {
    if (step === 'otp') {
      setCountdown(60);
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timerRef.current);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [step]);

  // Polling effect when waiting for Hosted Web Checkout completion
  useEffect(() => {
    if (step === 'waiting_hosted' && orderId) {
      if (pollingRef.current) clearInterval(pollingRef.current);
      pollingRef.current = setInterval(async () => {
        try {
          const res = await paymentService.getOrderStatus(orderId);
          if (res.data?.data?.status === 'paid') {
            clearInterval(pollingRef.current);
            setSuccessData(res.data.data);
            setStep('success');
            message.success('Оплата через Atmos успешно подтверждена!');
            if (onSuccess) {
              onSuccess(res.data.data);
            }
          }
        } catch (e) {
          // ignore transient polling network errors
        }
      }, 3000);
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [step, orderId]);

  // Card formatting
  const handleCardChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/\D/g, '').substring(0, 16);
    const formatted = val.match(/.{1,4}/g)?.join(' ') || val;
    setCardNumber(formatted);
    setErrorMessage('');
    setIsSms102Error(false);
  };

  // Expiry formatting MM/YY
  const handleExpiryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let val = e.target.value.replace(/\D/g, '').substring(0, 4);
    if (val.length >= 2) {
      let month = parseInt(val.substring(0, 2), 10);
      if (month > 12) month = 12;
      if (month < 1 && val.length === 2) month = 1;
      const monthStr = month < 10 ? `0${month}` : `${month}`;
      val = monthStr + (val.length > 2 ? '/' + val.substring(2, 4) : '');
    }
    setExpiry(val);
    setErrorMessage('');
  };

  // Detect card network with styling
  const cleanCard = cardNumber.replace(/\s/g, '');
  const getCardNetwork = () => {
    if (cleanCard.startsWith('8600')) {
      return {
        name: 'Uzcard',
        bg: 'bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950/40 dark:text-sky-300 dark:border-sky-800',
        badge: 'Uzcard',
      };
    }
    if (cleanCard.startsWith('9860')) {
      return {
        name: 'Humo',
        bg: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800',
        badge: 'Humo',
      };
    }
    if (cleanCard.startsWith('4')) {
      return {
        name: 'Visa',
        bg: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800',
        badge: 'Visa',
      };
    }
    if (cleanCard.startsWith('5')) {
      return {
        name: 'Mastercard',
        bg: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800',
        badge: 'Mastercard',
      };
    }
    return null;
  };
  const cardNetwork = getCardNetwork();

  const handleApplyPromo = async () => {
    if (!promoCodeInput.trim()) return;
    setIsValidatingPromo(true);
    setErrorMessage('');
    try {
      const res = await adService.validatePromo({
        code: promoCodeInput.trim().toUpperCase(),
        purpose,
        amount_usd: baseUsd,
        plan_id: planId,
      });
      if (res.data?.data) {
        setAppliedPromo(res.data.data);
        message.success(`Промокод "${res.data.data.code}" успешно применен!`);
      } else {
        setErrorMessage(res.data?.message || 'Недействительный промокод');
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Ошибка валидации промокода');
    } finally {
      setIsValidatingPromo(false);
    }
  };

  // Launch Atmos Hosted Web Checkout (checkout.atmos.uz)
  const handleLaunchHostedCheckout = async () => {
    setLoading(true);
    setErrorMessage('');
    setIsSms102Error(false);

    try {
      const createRes = await paymentService.createAtmosPayment({
        purpose,
        plan_id: purpose === 'subscription_upgrade' ? planId : undefined,
        advertiser_id: advertiserId,
        amount_usd: finalUsd,
        amount_uzs: computedUzs,
        promo_code: appliedPromo?.code,
        lang: 'ru',
      });

      if (createRes.data.code !== 0 || !createRes.data.data?.order_id) {
        setErrorMessage(createRes.data.message || 'Ошибка создания платежного заказа');
        setLoading(false);
        return;
      }

      const createdOrderId = createRes.data.data.order_id;
      const url = createRes.data.data.checkout_url || `https://checkout.atmos.uz/invoice/get?storeId=100506&transactionId=${createRes.data.data.transaction_id}&redirectLink=https://demo.swipies.app/ads?payment_success=${createdOrderId}`;

      setOrderId(createdOrderId);
      setCheckoutUrl(url);
      setStep('waiting_hosted');

      // Open in a new tab for frictionless security and 3DS compliance
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch (err: any) {
      setErrorMessage(err.message || 'Не удалось связаться со шлюзом Atmos.');
    } finally {
      setLoading(false);
    }
  };

  // Manual Check Button in Waiting Hosted state
  const handleManualCheckStatus = async () => {
    if (!orderId) return;
    setLoading(true);
    try {
      const res = await paymentService.getOrderStatus(orderId);
      if (res.data?.data?.status === 'paid') {
        setSuccessData(res.data.data);
        setStep('success');
        message.success('Оплата через Atmos успешно подтверждена!');
        if (onSuccess) {
          onSuccess(res.data.data);
        }
      } else {
        message.info('Транзакция пока в процессе оплаты на странице Atmos. Завершите оплату в открытой вкладке.');
      }
    } catch (err: any) {
      message.error(err.message || 'Ошибка проверки статуса.');
    } finally {
      setLoading(false);
    }
  };

  // Step: Create transaction & pre-apply (Direct In-App)
  const handleDirectPay = async () => {
    if (cleanCard.length !== 16) {
      setErrorMessage('Пожалуйста, введите полный 16-значный номер карты.');
      return;
    }
    const cleanExp = expiry.replace(/\//g, '');
    if (cleanExp.length !== 4) {
      setErrorMessage('Укажите корректный срок действия карты (ММ/ГГ).');
      return;
    }

    setLoading(true);
    setErrorMessage('');
    setIsSms102Error(false);

    try {
      // 1. Create order
      const createRes = await paymentService.createAtmosPayment({
        purpose,
        plan_id: purpose === 'subscription_upgrade' ? planId : undefined,
        advertiser_id: advertiserId,
        amount_usd: finalUsd,
        amount_uzs: computedUzs,
        promo_code: appliedPromo?.code,
        lang: 'ru',
      });

      if (createRes.data.code !== 0 || !createRes.data.data?.order_id) {
        setErrorMessage(createRes.data.message || 'Ошибка создания платежного заказа');
        setLoading(false);
        return;
      }

      const createdOrderId = createRes.data.data.order_id;
      setOrderId(createdOrderId);

      // 2. Pre-apply card (dispatch OTP)
      const preRes = await paymentService.preApplyCard({
        order_id: createdOrderId,
        card_number: cleanCard,
        expiry: cleanExp,
      });

      if (preRes.data.code !== 0 || !preRes.data.data) {
        const msgStr = preRes.data.message || 'Ошибка при отправке СМС-кода.';
        setErrorMessage(msgStr);
        if (msgStr.includes('102') || msgStr.toLowerCase().includes('смс')) {
          setIsSms102Error(true);
        }
        setLoading(false);
        return;
      }

      setPhoneMasked(preRes.data.data.phone_masked || '+998 9* *** ** **');
      setStep('otp');
    } catch (err: any) {
      setErrorMessage(err.message || 'Не удалось связаться со шлюзом Atmos.');
    } finally {
      setLoading(false);
    }
  };

  // Resend OTP
  const handleResendOtp = async () => {
    if (countdown > 0 || !orderId) return;
    setLoading(true);
    setErrorMessage('');
    setIsSms102Error(false);

    try {
      const cleanExp = expiry.replace(/\//g, '');
      const preRes = await paymentService.preApplyCard({
        order_id: orderId,
        card_number: cleanCard,
        expiry: cleanExp,
      });

      if (preRes.data.code !== 0) {
        setErrorMessage(preRes.data.message || 'Ошибка повторной отправки кода.');
      } else {
        message.success('Новый СМС-код отправлен на ваш номер');
        setCountdown(60);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Не удалось отправить повторный СМС-код');
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Confirm OTP
  const handleConfirmOtp = async () => {
    const cleanOtp = otp.trim();
    if (cleanOtp.length < 4) {
      setErrorMessage('Пожалуйста, введите проверочный код из СМС.');
      return;
    }

    setLoading(true);
    setErrorMessage('');

    try {
      const applyRes = await paymentService.applyOtp({
        order_id: orderId,
        otp: cleanOtp,
      });

      if (applyRes.data.code !== 0 || applyRes.data.data?.status !== 'paid') {
        setErrorMessage(applyRes.data.message || 'Неверный СМС-код. Проверьте код и повторите.');
        setLoading(false);
        return;
      }

      setSuccessData(applyRes.data.data);
      setStep('success');
      message.success('Оплата успешно подтверждена!');
      if (onSuccess) {
        onSuccess(applyRes.data.data);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Ошибка подтверждения платежа.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md p-6 overflow-hidden">
        <DialogHeader className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex items-center justify-center font-black text-base shadow-md shadow-blue-500/20">
                A
              </div>
              <div>
                <DialogTitle className="text-base font-bold flex items-center gap-2">
                  Atmos Эквайринг
                  <Badge variant="outline" className="text-[10px] bg-blue-50/80 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800">
                    Мгновенно
                  </Badge>
                </DialogTitle>
                <DialogDescription className="text-xs text-muted-foreground">
                  Безопасная оплата картами Uzcard, Humo, Visa, Mastercard
                </DialogDescription>
              </div>
            </div>
          </div>
        </DialogHeader>

        {/* Order Summary Card */}
        <div className="rounded-xl border border-blue-100 bg-gradient-to-br from-blue-50/80 via-indigo-50/40 to-slate-50 p-4 space-y-2 dark:from-blue-950/30 dark:via-indigo-950/20 dark:to-slate-900/50 dark:border-blue-900/40">
          <div className="flex justify-between items-center text-xs">
            <span className="text-muted-foreground font-medium flex items-center gap-1.5">
              {purpose === 'subscription_upgrade' ? (
                <>
                  <Sparkles className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  <span>Тариф: <strong>Swipies {planId?.toUpperCase()}</strong></span>
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  <span>Пополнение рекламного баланса</span>
                </>
              )}
            </span>
            <div className="text-right">
              {appliedPromo && appliedPromo.discount_usd > 0 ? (
                <div className="flex items-center gap-1.5">
                  <span className="line-through text-muted-foreground text-xs">${baseUsd.toFixed(2)}</span>
                  <span className="font-bold text-emerald-600 text-sm">${finalUsd.toFixed(2)} USD</span>
                </div>
              ) : (
                <span className="font-bold text-foreground text-sm">${baseUsd.toFixed(2)} USD</span>
              )}
            </div>
          </div>

          {appliedPromo && (
            <div className="flex items-center justify-between text-xs pt-1 border-t border-blue-100/60 dark:border-blue-900/40">
              <span className="text-emerald-700 dark:text-emerald-400 font-semibold flex items-center gap-1">
                <Tag className="h-3.5 w-3.5" /> Промокод: {appliedPromo.code}
              </span>
              <span className="text-emerald-700 dark:text-emerald-400 font-bold">
                {appliedPromo.discount_usd > 0
                  ? `-$${appliedPromo.discount_usd.toFixed(2)}`
                  : `+$${appliedPromo.bonus_usd} Бонус`}
              </span>
            </div>
          )}

          <div className="flex justify-between items-baseline pt-2 border-t border-blue-100/90 dark:border-blue-900/50">
            <span className="text-xs text-muted-foreground font-medium">К списанию в UZS:</span>
            <div className="text-right">
              <span className="text-xl font-extrabold text-blue-700 dark:text-blue-400 tracking-tight">
                {computedUzs.toLocaleString()} <span className="text-xs font-semibold">UZS</span>
              </span>
              <div className="text-[10px] text-muted-foreground">Курс: 1 USD = {EXCHANGE_RATE.toLocaleString()} UZS</div>
            </div>
          </div>

          {purpose === 'subscription_upgrade' && (
            <div className="text-[11px] text-emerald-700 dark:text-emerald-400 font-medium flex items-center gap-1.5 pt-1">
              <ShieldCheck className="h-3.5 w-3.5 shrink-0" />
              <span>100% отключение рекламы и удаление водяного знака</span>
            </div>
          )}
        </div>

        {/* Promo Code Input Row */}
        {(step === 'checkout' || step === 'card') && !appliedPromo && (
          <div className="flex gap-2 items-center">
            <Input
              placeholder="Есть промокод? (например, WELCOME20)"
              value={promoCodeInput}
              onChange={(e) => setPromoCodeInput(e.target.value.toUpperCase())}
              className="h-9 text-xs font-mono uppercase bg-background"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-9 text-xs font-semibold shrink-0"
              onClick={handleApplyPromo}
              disabled={isValidatingPromo || !promoCodeInput.trim()}
            >
              {isValidatingPromo ? 'Проверка...' : 'Применить'}
            </Button>
          </div>
        )}

        {/* Error Alert */}
        {errorMessage && (
          <div className="rounded-xl bg-red-50/90 border border-red-200 p-3.5 text-xs text-red-800 space-y-1.5 dark:bg-red-950/40 dark:border-red-800 dark:text-red-300">
            <div className="flex items-center gap-2 font-bold text-red-900 dark:text-red-200">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
              <span>Не удалось завершить операцию</span>
            </div>
            <p className="text-[11px] leading-relaxed pl-6">{errorMessage}</p>
            {isSms102Error && (
              <div className="mt-2 p-2 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-[11px] dark:bg-amber-950/40 dark:border-amber-800 dark:text-amber-200">
                💡 <strong>Совет:</strong> Убедитесь, что на вашей карте Uzcard/Humo подключена услуга СМС-информирования через банкомат или мобильное приложение вашего банка.
              </div>
            )}
          </div>
        )}

        {/* STEP: Hosted Web Checkout Option (checkout.atmos.uz) */}
        {step === 'checkout' && (
          <div className="space-y-4 pt-1">
            <div className="rounded-xl border border-blue-200 bg-blue-50/40 p-3.5 space-y-2 dark:bg-blue-950/20 dark:border-blue-900/40">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-blue-950 dark:text-blue-200 flex items-center gap-1.5">
                  <CreditCard className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  Официальная платежная страница Atmos
                </span>
                <Badge className="bg-blue-600 text-white text-[10px] font-bold">
                  checkout.atmos.uz
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Вы будете перенаправлены на официальную защищенную страницу Atmos для ввода реквизитов карты (Uzcard, Humo, Visa, Mastercard) и подтверждения по SMS.
              </p>
              <div className="flex items-center gap-2 pt-1">
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white dark:bg-slate-900 border text-muted-foreground">
                  Uzcard
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white dark:bg-slate-900 border text-muted-foreground">
                  Humo
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white dark:bg-slate-900 border text-muted-foreground">
                  Visa
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white dark:bg-slate-900 border text-muted-foreground">
                  Mastercard
                </span>
              </div>
            </div>

            <Button
              onClick={handleLaunchHostedCheckout}
              disabled={loading}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-extrabold h-11 text-xs flex items-center justify-center gap-2 shadow-lg shadow-blue-500/25"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Генерация ссылки Atmos...
                </>
              ) : (
                <>
                  <ExternalLink className="h-4 w-4" />
                  Перейти на страницу оплаты Atmos ({computedUzs.toLocaleString()} UZS)
                </>
              )}
            </Button>

            <div className="relative my-3">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border/60" />
              </div>
              <div className="relative flex justify-center text-[10px] uppercase">
                <span className="bg-background px-2 text-muted-foreground font-semibold">или</span>
              </div>
            </div>

            <Button
              type="button"
              variant="outline"
              onClick={() => setStep('card')}
              className="w-full h-9 text-xs font-semibold text-muted-foreground hover:text-foreground flex items-center justify-center gap-1.5"
            >
              <CreditCard className="h-3.5 w-3.5" />
              Оплатить прямо на сайте (In-App)
            </Button>
          </div>
        )}

        {/* STEP: Waiting for Hosted Checkout Completion */}
        {step === 'waiting_hosted' && (
          <div className="py-4 text-center space-y-4">
            <div className="relative mx-auto h-16 w-16">
              <div className="absolute inset-0 rounded-full bg-blue-500/20 animate-ping" />
              <div className="relative h-16 w-16 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20 dark:bg-blue-950/60 dark:text-blue-400">
                <Loader2 className="h-8 w-8 animate-spin" />
              </div>
            </div>

            <div className="space-y-1">
              <h3 className="text-base font-bold text-foreground">
                Ожидание завершения оплаты...
              </h3>
              <p className="text-xs text-muted-foreground max-w-xs mx-auto">
                Страница оплаты открыта на <strong>checkout.atmos.uz</strong>. Введите реквизиты карты и код из СМС.
              </p>
            </div>

            <div className="rounded-xl bg-muted/40 border p-3 text-xs text-left font-mono space-y-1 text-muted-foreground">
              <div className="flex justify-between">
                <span>Сумма к оплате:</span>
                <span className="font-bold text-foreground">
                  {computedUzs.toLocaleString()} UZS (${finalUsd.toFixed(2)})
                </span>
              </div>
              <div className="flex justify-between">
                <span>Заказ:</span>
                <span className="text-foreground font-semibold">#{orderId.substring(0, 14)}</span>
              </div>
            </div>

            <div className="flex flex-col gap-2 pt-1">
              <Button
                onClick={handleManualCheckStatus}
                disabled={loading}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold h-10 text-xs flex items-center justify-center gap-1.5 shadow-md shadow-emerald-500/20"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
                Проверить статус оплаты
              </Button>

              {checkoutUrl && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => window.open(checkoutUrl, '_blank', 'noopener,noreferrer')}
                  className="w-full h-9 text-xs font-semibold flex items-center justify-center gap-1.5"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  Открыть страницу оплаты заново
                </Button>
              )}

              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setStep('checkout')}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                <ArrowLeft className="h-3.5 w-3.5 mr-1" />
                Вернуться назад
              </Button>
            </div>
          </div>
        )}

        {/* STEP: Direct Card Input */}
        {step === 'card' && (
          <div className="space-y-4 pt-1">
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-xs font-bold text-foreground flex items-center gap-1.5">
                  <CreditCard className="h-3.5 w-3.5 text-muted-foreground" /> Номер банковской карты
                </label>
                {cardNetwork && (
                  <Badge variant="outline" className={`text-[10px] font-bold px-2 py-0.5 ${cardNetwork.bg}`}>
                    {cardNetwork.badge}
                  </Badge>
                )}
              </div>
              <Input
                placeholder="8600 0000 0000 0000"
                value={cardNumber}
                onChange={handleCardChange}
                maxLength={19}
                className="font-mono text-sm tracking-widest h-11 bg-background"
                autoFocus
              />
              <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-0.5">
                <span className="flex items-center gap-1">
                  Поддерживаются: Uzcard, Humo, Visa, MC
                </span>
                <span className="font-mono text-[10px]">{cleanCard.length}/16</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-foreground">Срок действия (ММ/ГГ)</label>
                <Input
                  placeholder="12/28"
                  value={expiry}
                  onChange={handleExpiryChange}
                  maxLength={5}
                  className="font-mono text-sm h-11 text-center bg-background"
                />
              </div>
              <div className="space-y-1.5 flex flex-col justify-end">
                <div className="text-[11px] text-muted-foreground leading-tight flex items-center gap-1.5 p-2 rounded-lg bg-muted/40 border border-border/50">
                  <Lock className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                  <span>256-bit SSL шифрование</span>
                </div>
              </div>
            </div>

            <DialogFooter className="pt-3 flex items-center justify-between gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setStep('checkout')}
                disabled={loading}
                className="text-xs font-semibold"
              >
                <ArrowLeft className="h-3.5 w-3.5 mr-1" />
                Atmos Web
              </Button>
              <Button
                onClick={handleDirectPay}
                disabled={loading || cleanCard.length !== 16 || expiry.length !== 5}
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold h-10 text-xs flex items-center gap-2 shadow-md shadow-blue-500/20"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Запрос в банк...
                  </>
                ) : (
                  <>
                    <CreditCard className="h-4 w-4" />
                    Оплатить {computedUzs.toLocaleString()} UZS
                  </>
                )}
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* STEP: OTP Verification */}
        {step === 'otp' && (
          <div className="space-y-4 pt-1">
            <div className="rounded-xl bg-amber-50/90 border border-amber-200 p-3.5 text-xs text-amber-900 space-y-1.5 dark:bg-amber-950/40 dark:border-amber-800 dark:text-amber-200">
              <div className="flex items-center gap-2 font-bold">
                <Lock className="h-4 w-4 text-amber-700 dark:text-amber-400" />
                <span>Подтверждение через СМС</span>
              </div>
              <p className="text-[11px] leading-relaxed">
                Банк отправил 6-значный код подтверждения на ваш привязанный номер <strong>{phoneMasked}</strong>.
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-foreground">Код из СМС-сообщения</label>
              <Input
                placeholder="123456"
                value={otp}
                onChange={(e) => {
                  setOtp(e.target.value.replace(/\D/g, '').substring(0, 8));
                  setErrorMessage('');
                }}
                maxLength={8}
                className="font-mono text-center text-xl tracking-[0.4em] font-extrabold h-12 bg-background shadow-inner"
                autoFocus
              />
              <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
                <span className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  {countdown > 0 ? `Повтор через ${countdown}с` : 'Код не пришел?'}
                </span>
                <Button
                  type="button"
                  variant="link"
                  size="sm"
                  disabled={countdown > 0 || loading}
                  onClick={handleResendOtp}
                  className="h-auto p-0 text-xs font-semibold text-blue-600 dark:text-blue-400"
                >
                  Отправить повторно
                </Button>
              </div>
            </div>

            <DialogFooter className="pt-3 flex items-center justify-between gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setStep('card')}
                disabled={loading}
                className="text-xs font-semibold"
              >
                <ArrowLeft className="h-3.5 w-3.5 mr-1" /> Назад
              </Button>
              <Button
                onClick={handleConfirmOtp}
                disabled={loading || otp.length < 4}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold h-10 text-xs flex items-center gap-2 shadow-md shadow-emerald-500/20"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Подтверждение...
                  </>
                ) : (
                  <>
                    <Check className="h-4 w-4" />
                    Подтвердить и активировать
                  </>
                )}
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* STEP: Success Screen */}
        {step === 'success' && (
          <div className="py-3 text-center space-y-4">
            <div className="h-14 w-14 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-lg shadow-emerald-500/20 dark:bg-emerald-950/60 dark:text-emerald-400">
              <CheckCircle2 className="h-8 w-8" />
            </div>

            <div className="space-y-1">
              <h3 className="text-lg font-extrabold text-foreground">Оплата успешно проведена!</h3>
              <p className="text-xs text-muted-foreground">
                {purpose === 'subscription_upgrade'
                  ? `Ваш тариф успешно обновлен до ${planId?.toUpperCase()}. Все привилегии активированы.`
                  : `Баланс рекламодателя успешно пополнен на $${finalUsd.toFixed(2)} USD.`}
              </p>
            </div>

            {/* Perks unlocked list */}
            {purpose === 'subscription_upgrade' && (
              <div className="rounded-xl border bg-emerald-50/40 p-3 text-left text-xs space-y-1.5 dark:bg-emerald-950/20 dark:border-emerald-900/40">
                <div className="font-bold text-emerald-800 dark:text-emerald-300 flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-emerald-600" /> Активированные преимущества:
                </div>
                <ul className="space-y-1 text-[11px] text-muted-foreground pl-1">
                  <li className="flex items-center gap-1.5">
                    <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span><strong>100% Ad-Free AI:</strong> Реклама в ответах LLM полностью отключена</span>
                  </li>
                  <li className="flex items-center gap-1.5">
                    <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span><strong>Clean Output:</strong> Водяной знак Swipies удален из ответов</span>
                  </li>
                  <li className="flex items-center gap-1.5">
                    <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span><strong>BYOK доступ:</strong> Разблокированы все премиальные модели</span>
                  </li>
                </ul>
              </div>
            )}

            <div className="rounded-xl bg-muted/40 border p-3 text-xs text-left font-mono space-y-1.5 text-muted-foreground">
              <div className="flex justify-between">
                <span>Сумма списания:</span>
                <span className="font-bold text-foreground">
                  {computedUzs.toLocaleString()} UZS (${finalUsd.toFixed(2)})
                </span>
              </div>
              <div className="flex justify-between">
                <span>Номер заказа:</span>
                <span className="text-foreground font-semibold">#{orderId.substring(0, 14)}</span>
              </div>
            </div>

            <Button
              onClick={() => onOpenChange(false)}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold h-11 text-xs shadow-md shadow-blue-500/20"
            >
              Отлично, продолжить
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default AtmosPaymentModal;
