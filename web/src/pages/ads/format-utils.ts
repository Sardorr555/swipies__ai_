/**
 * Safe numeric formatting utilities to prevent runtime TypeError:
 * Cannot read properties of undefined (reading 'toFixed' / 'toLocaleString')
 */

export const toFixedSafe = (val: any, digits: number = 2): string => {
  if (val === null || val === undefined || val === '') return (0).toFixed(digits);
  const n = Number(val);
  return (Number.isFinite(n) ? n : 0).toFixed(digits);
};

export const toLocaleSafe = (val: any): string => {
  if (val === null || val === undefined || val === '') return '0';
  const n = Number(val);
  return (Number.isFinite(n) ? n : 0).toLocaleString();
};
