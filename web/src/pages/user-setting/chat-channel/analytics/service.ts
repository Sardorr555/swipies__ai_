import { getAuthorization } from '@/utils/authorization-util';

export const metricLabels: Record<string, string> = {
  users_total: 'Всего пользователей', users_active: 'Активные за период',
  users_new: 'Новые пользователи', messages_in: 'Сообщения пользователей',
  messages_out: 'Ответы бота', payers: 'Оплатившие пользователи',
  payments: 'Успешные платежи', revenue: 'Выручка до возвратов', refunds: 'Возвраты',
};
export type Period = { period: string; timezone: string; start?: string; end?: string };
export type WidgetSettings = Period & { metrics: string[]; show_revenue: boolean; include_link: boolean; title?: string; expires_days?: number | null };
export type Money = { currency: string; amount?: string; refund_amount?: string; payments?: number };
export type PaymentData = { payers?: number; payments?: number; currencies?: Money[] };
export type Snapshot = {
  initialized?: boolean; message?: string; title?: string;
  bot: { id?: string; name: string; username: string };
  period: Period & { start: string; end: string };
  updated_at: string; last_processed_at: string | null; collection_started_at: string | null;
  coverage: string; metrics: Record<string, number | null>; selected_metrics?: string[];
  connection?: { enabled: boolean; polling_active: boolean; status: string };
  pending_events?: number; payment_tracking?: string; unmatched_refunds?: number; payment_data_incomplete?: boolean;
  payment_collection_started_at?: string | null; payment_coverage?: string;
  payments_period?: PaymentData | null; payments_all_time?: PaymentData | null;
  conversion?: { percent: number | null; formula: string; numerator: number; denominator: number | null };
  series: Array<Record<string, any> & { date: string; payments?: PaymentData | null }>;
  audience_note: string;
};
export type Share = { id: string; title: string; settings: WidgetSettings; expires_at: string | null; revoked_at: string | null };
export type CreatedShare = { id: string; token: string; path: string; title: string; settings: WidgetSettings };

export function endpoint(channel: string, suffix = '') {
  return `/api/v1/chat-channels/${encodeURIComponent(channel)}/analytics${suffix}`;
}
export async function privateRequest<T>(url: string, method = 'GET', body?: unknown, signal?: AbortSignal): Promise<T> {
  const auth = getAuthorization();
  const response = await fetch(url, { method, credentials: 'same-origin', cache: 'no-store', signal,
    headers: { ...(auth ? { Authorization: auth } : {}), ...(body ? { 'Content-Type': 'application/json' } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const value = await response.json();
  if (!response.ok || value.code !== 0) throw new Error(value.message || 'Запрос не выполнен');
  return value.data as T;
}
export async function publicSnapshot(token: string, signal?: AbortSignal): Promise<Snapshot> {
  const response = await fetch('/api/v1/telegram-analytics/public', { method: 'POST', cache: 'no-store',
    credentials: 'omit', referrerPolicy: 'no-referrer', signal,
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token }),
  });
  const value = await response.json();
  if (!response.ok || value.code !== 0) {
    const reasons: Record<string, string> = { revoked: 'Владелец отозвал эту ссылку', expired: 'Срок действия ссылки истёк', unavailable: 'Ссылка недоступна' };
    throw new Error(reasons[value.message] || value.message || 'Виджет временно недоступен');
  }
  return value.data;
}
export function periodQuery(period: Period) { return new URLSearchParams(Object.entries(period).filter(([,v]) => v != null) as [string,string][]).toString(); }
export function number(value: number | null | undefined) { return value == null ? 'Нет данных' : new Intl.NumberFormat('ru-RU').format(value); }
export function dateTime(value: string | null | undefined, timezone: string) {
  if (!value) return 'Нет данных';
  return new Intl.DateTimeFormat('ru-RU', { dateStyle: 'short', timeStyle: 'short', timeZone: timezone }).format(new Date(value));
}
export async function downloadCard(channel: string, body: unknown, filename: string, share = false) {
  const auth = getAuthorization();
  const response = await fetch(endpoint(channel, '/card'), { method: 'POST', cache: 'no-store', credentials: 'same-origin',
    headers: { Authorization: auth, 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (!response.ok || !response.headers.get('Content-Type')?.includes('image/png')) {
    const error = await response.json(); throw new Error(error.message || 'Карточка не создана');
  }
  const blob = await response.blob();
  const file = new File([blob], filename, { type: 'image/png' });
  if (share && navigator.canShare?.({ files: [file] })) { await navigator.share({ files: [file], title: 'Аналитика Telegram-бота' }); return; }
  const url = URL.createObjectURL(blob); const link = document.createElement('a');
  link.href = url; link.download = filename; document.body.appendChild(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
