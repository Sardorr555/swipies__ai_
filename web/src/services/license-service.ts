import api from '@/utils/api';
import request from '@/utils/request';

const {
  licenseList,
  licenseCreatePay,
  licensePreApplyPay,
  licenseApplyPay,
  licenseUpdate,
  licenseDelete,
  adminLicenseList,
  adminLicenseAction,
  adminLicensePricing,
  licensePricing,
  licenseRecoverPay,
} = api;

export const listLicenses = () => request.get(licenseList);

export const createLicensePay = (name: string, durationMonths: number) =>
  request.post(licenseCreatePay, { data: { name, duration_months: durationMonths } });

export const preApplyLicensePay = (
  transactionId: string,
  cardNumber: string,
  expiry: string,
) =>
  request.post(licensePreApplyPay, {
    data: {
      transaction_id: transactionId,
      card_number: cardNumber,
      expiry,
    },
  });

export const applyLicensePay = (transactionId: string, otp: string) =>
  request.post(licenseApplyPay, {
    data: {
      transaction_id: transactionId,
      otp,
    },
  });

export const recoverLicensePay = (transactionId: string) =>
  request.post(licenseRecoverPay, {
    data: {
      transaction_id: transactionId,
    },
  });

export const renameLicense = (licenseId: string, name: string) =>
  request.patch(licenseUpdate(licenseId), { data: { name } });

export const revokeLicense = (licenseId: string) =>
  request.delete(licenseDelete(licenseId));

export const getUserLicensePricing = () => request.get(licensePricing);

// Admin services
export const adminListLicenses = (params: {
  page?: number;
  size?: number;
  search?: string;
}) => request.get(adminLicenseList, { params });

export const adminIssueLicense = (
  userEmail: string,
  name: string,
  durationMonths: number,
) =>
  request.post(adminLicenseList, {
    data: {
      user_email: userEmail,
      name,
      duration_months: durationMonths,
    },
  });

export const adminRevokeLicense = (licenseId: string) =>
  request.delete(adminLicenseAction(licenseId));

export const getAdminLicensePricing = () => request.get(adminLicensePricing);

export const updateAdminLicensePricing = (pricing: {
  price_6_months: number;
  price_12_months: number;
  price_per_month_custom: number;
}) => request.post(adminLicensePricing, { data: pricing });
