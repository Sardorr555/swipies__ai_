import React, { useState, useEffect } from 'react';
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
import { CreditCard, CheckCircle2, AlertCircle, ShieldCheck, Lock, ArrowLeft, Loader2, Sparkles, Zap } from 'lucide-react';
import paymentService, { PaymentOrderCreatePayload } from '@/services/payment-service';
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
  const [step, setStep] = useState<'card' | 'otp' | 'success'>('card');
  const [cardNumber, setCardNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [orderId, setOrderId] = useState('');
  const [phoneMasked, setPhoneMasked] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [successData, setSuccessData] = useState<any>(null);

  // Computed amounts
  const computedUsd = purpose === 'subscription_upgrade'
    ? (planId === 'plus' ? 9.99 : planId === 'enterprise' ? 99.0 : 29.99)
    : (amountUsd || 50.0);

  const computedUzs = Math.round(computedUsd * EXCHANGE_RATE);

  useEffect(() => {
    if (open) {
      setStep('card');
      setCardNumber('');
      setExpiry('');
      setOtp('');
      setErrorMessage('');
      setOrderId('');
      setSuccessData(null);
    }
  }, [open]);

  // Card formatting
  const handleCardChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let val = e.target.value.replace(/\D/g, '').substring(0, 16);
    let formatted = val.match(/.{1,4}/g)?.join(' ') || val;
    setCardNumber(formatted);
    setErrorMessage('');
  };

  // Expiry formatting MM/YY
  const handleExpiryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let val = e.target.value.replace(/\D/g, '').substring(0, 4);
    if (val.length >= 3) {
      val = val.substring(0, 2) + '/' + val.substring(2, 4);
    }
    setExpiry(val);
    setErrorMessage('');
  };

  // Detect card network
  const cleanCard = cardNumber.replace(/\s/g, '');
  const getCardNetwork = () => {
    if (cleanCard.startsWith('8600')) return 'Uzcard';
    if (cleanCard.startsWith('9860')) return 'Humo';
    if (cleanCard.startsWith('4')) return 'Visa';
    if (cleanCard.startsWith('5')) return 'Mastercard';
    return null;
  };
  const cardNetwork = getCardNetwork();

  // Step 1: Create transaction & pre-apply
  const handlePay = async () => {
    if (cleanCard.length !== 16) {
      setErrorMessage('Введите полный 16-значный номер карты.');
      return;
    }
    const cleanExp = expiry.replace(/\//g, '');
    if (cleanExp.length !== 4) {
      setErrorMessage('Введите корректный срок действия карты (ММ/ГГ).');
      return;
    }

    setLoading(true);
    setErrorMessage('');

    try {
      // 1. Create order
      const createRes = await paymentService.createAtmosPayment({
        purpose,
        plan_id: purpose === 'subscription_upgrade' ? planId : undefined,
        advertiser_id: advertiserId,
        amount_usd: computedUsd,
        amount_uzs: computedUzs,
        lang: 'ru',
      });

      if (createRes.data.code !== 0 || !createRes.data.data?.order_id) {
        setErrorMessage(createRes.data.message || 'Ошибка создания платежа');
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
        setErrorMessage(preRes.data.message || 'Ошибка верификации карты или отправки СМС.');
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

  // Step 2: Confirm OTP
  const handleConfirmOtp = async () => {
    const cleanOtp = otp.trim();
    if (cleanOtp.length < 4) {
      setErrorMessage('Введите код из СМС.');
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
        setErrorMessage(applyRes.data.message || 'Неверный СМС-код.');
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
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-1">
            <div className="h-8 w-8 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-sm shadow-md">
              A
            </div>
            <div>
              <DialogTitle className="text-base font-bold flex items-center gap-1.5">
                Оплата через Atmos
                <Badge variant="outline" className="text-[10px] bg-blue-50 text-blue-700 border-blue-200">
                  Uzcard • Humo • Visa
                </Badge>
              </DialogTitle>
              <DialogDescription className="text-xs">
                Безопасный эквайринг национальных и международных карт
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Order Summary Pill */}
        <div className="rounded-xl border border-blue-100 bg-gradient-to-r from-blue-50/70 to-indigo-50/70 p-3.5 space-y-1.5">
          <div className="flex justify-between items-center text-xs">
            <span className="text-muted-foreground font-medium flex items-center gap-1">
              {purpose === 'subscription_upgrade' ? (
                <>
                  <Sparkles className="h-3.5 w-3.5 text-blue-600" />
                  Подписка Swipies {planId?.toUpperCase()}
                </>
              ) : (
                <>
                  <Zap className="h-3.5 w-3.5 text-emerald-600" />
                  Пополнение рекламного баланса
                </>
              )}
            </span>
            <span className="font-semibold text-foreground">${computedUsd.toFixed(2)} USD</span>
          </div>
          <div className="flex justify-between items-baseline pt-1 border-t border-blue-100/80">
            <span className="text-xs text-muted-foreground">К списанию:</span>
            <span className="text-lg font-bold text-blue-700">
              {computedUzs.toLocaleString()} <span className="text-xs font-normal">UZS</span>
            </span>
          </div>
          {purpose === 'subscription_upgrade' && (
            <div className="text-[11px] text-emerald-700 font-medium flex items-center gap-1 pt-0.5">
              <ShieldCheck className="h-3.5 w-3.5" /> 100% отключение рекламы и водяных знаков Swipies
            </div>
          )}
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-xs text-red-700 flex items-start gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-semibold">Ошибка проведения платежа</p>
              <p className="text-[11px] leading-relaxed">{errorMessage}</p>
            </div>
          </div>
        )}

        {/* STEP 1: Card Details Input */}
        {step === 'card' && (
          <div className="space-y-3.5 py-1">
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-xs font-semibold flex items-center gap-1">
                  <CreditCard className="h-3.5 w-3.5 text-muted-foreground" /> Номер карты
                </label>
                {cardNetwork && (
                  <Badge variant="secondary" className="text-[10px] font-semibold">
                    {cardNetwork}
                  </Badge>
                )}
              </div>
              <Input
                placeholder="8600 0000 0000 0000"
                value={cardNumber}
                onChange={handleCardChange}
                maxLength={19}
                className="font-mono text-sm tracking-wide"
                autoFocus
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Срок действия (ММ/ГГ)</label>
                <Input
                  placeholder="12/28"
                  value={expiry}
                  onChange={handleExpiryChange}
                  maxLength={5}
                  className="font-mono text-sm"
                />
              </div>
              <div className="space-y-1.5 flex flex-col justify-end">
                <div className="text-[11px] text-muted-foreground leading-tight flex items-center gap-1 py-1">
                  <Lock className="h-3 w-3 text-emerald-600 shrink-0" />
                  Шифрование SSL 256-bit
                </div>
              </div>
            </div>

            <DialogFooter className="pt-2">
              <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
                Отмена
              </Button>
              <Button
                onClick={handlePay}
                disabled={loading || cleanCard.length !== 16 || expiry.length !== 5}
                className="bg-blue-600 hover:bg-blue-700 text-white font-semibold flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Отправка запроса...
                  </>
                ) : (
                  `Оплатить ${computedUzs.toLocaleString()} UZS`
                )}
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* STEP 2: SMS OTP Verification */}
        {step === 'otp' && (
          <div className="space-y-3.5 py-1">
            <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-xs text-amber-900 space-y-1">
              <p className="font-semibold flex items-center gap-1">
                <Lock className="h-3.5 w-3.5 text-amber-700" /> Введите проверочный код из СМС
              </p>
              <p className="text-[11px] text-amber-800">
                Код подтверждения отправлен банком на номер <strong>{phoneMasked}</strong>
              </p>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">СМС-код подтверждения</label>
              <Input
                placeholder="123456"
                value={otp}
                onChange={(e) => {
                  setOtp(e.target.value.replace(/\D/g, '').substring(0, 8));
                  setErrorMessage('');
                }}
                maxLength={8}
                className="font-mono text-center text-lg tracking-widest"
                autoFocus
              />
            </div>

            <DialogFooter className="pt-2 flex justify-between">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setStep('card')}
                disabled={loading}
                className="text-xs"
              >
                <ArrowLeft className="h-3.5 w-3.5 mr-1" /> Назад к карте
              </Button>
              <Button
                onClick={handleConfirmOtp}
                disabled={loading || otp.length < 4}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Проверка кода...
                  </>
                ) : (
                  'Подтвердить оплату'
                )}
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* STEP 3: Success Screen */}
        {step === 'success' && (
          <div className="py-4 text-center space-y-3">
            <div className="h-12 w-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
              <CheckCircle2 className="h-7 w-7" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-bold text-foreground">Оплата прошла успешно!</h3>
              <p className="text-xs text-muted-foreground">
                {purpose === 'subscription_upgrade'
                  ? `Ваш тариф успешно обновлен до ${planId?.toUpperCase()}. Реклама и брендинг отключены.`
                  : `Баланс рекламодателя успешно пополнен на $${computedUsd.toFixed(2)} USD.`}
              </p>
            </div>

            <div className="rounded-lg bg-muted/40 border p-2.5 text-xs text-left font-mono space-y-1 text-muted-foreground">
              <div className="flex justify-between">
                <span>Сумма:</span>
                <span className="font-semibold text-foreground">{computedUzs.toLocaleString()} UZS (${computedUsd.toFixed(2)})</span>
              </div>
              <div className="flex justify-between">
                <span>Номер заказа:</span>
                <span className="text-foreground">#{orderId.substring(0, 12)}</span>
              </div>
            </div>

            <Button
              onClick={() => onOpenChange(false)}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white mt-2"
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
