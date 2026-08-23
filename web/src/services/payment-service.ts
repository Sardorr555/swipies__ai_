import request from '@/utils/request';

export interface ResponseData<T = any> {
  code: number;
  message: string;
  data: T;
}

export interface PaymentOrderCreatePayload {
  purpose: 'subscription_upgrade' | 'advertiser_deposit';
  plan_id?: 'plus' | 'pro' | 'enterprise';
  advertiser_id?: string;
  amount_uzs?: number;
  amount_usd?: number;
  lang?: string;
}

export interface PaymentOrderCreateResult {
  order_id: string;
  transaction_id: string;
  amount_uzs: number;
  amount_usd: number;
  purpose: string;
  plan_id?: string;
  advertiser_id?: string;
  currency: string;
  status: string;
}

export interface PreApplyCardPayload {
  order_id: string;
  card_number: string;
  expiry: string;
}

export interface PreApplyCardResult {
  order_id: string;
  status: 'waiting_otp';
  phone_masked: string;
  card_masked: string;
}

export interface ApplyOtpPayload {
  order_id: string;
  otp: string;
}

export interface ApplyOtpResult {
  order_id: string;
  status: 'paid';
  purpose: string;
  plan_id?: string;
  amount_usd: number;
  amount_uzs: number;
  fulfillment?: {
    success: boolean;
    plan_type?: string;
    plan_expiry_date?: string;
    message?: string;
    deposit_amount_usd?: number;
    deposit_success?: boolean;
  };
}

export interface PaymentOrderItem {
  id: string;
  gateway: string;
  external_transaction_id: string;
  purpose: string;
  plan_id?: string;
  amount_uzs: number;
  amount_usd: number;
  currency: string;
  status: 'pending' | 'waiting_otp' | 'paid' | 'failed' | 'canceled';
  card_masked?: string;
  phone_masked?: string;
  created_at: number;
}

const paymentService = {
  createAtmosPayment: (payload: PaymentOrderCreatePayload) =>
    request.post<ResponseData<PaymentOrderCreateResult>>('/v1/payment/atmos/create', payload),

  preApplyCard: (payload: PreApplyCardPayload) =>
    request.post<ResponseData<PreApplyCardResult>>('/v1/payment/atmos/pre-apply', payload),

  applyOtp: (payload: ApplyOtpPayload) =>
    request.post<ResponseData<ApplyOtpResult>>('/v1/payment/atmos/apply', payload),

  listPaymentOrders: () =>
    request.get<ResponseData<PaymentOrderItem[]>>('/v1/payment/orders'),

  getOrderStatus: (orderId: string) =>
    request.get<ResponseData<PaymentOrderItem>>(`/v1/payment/orders/${orderId}`),
};

export default paymentService;
