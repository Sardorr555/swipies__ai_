import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useState } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { Snapshot, metricLabels, number, dateTime } from './service';

const colors = ['#668cff', '#2ac5a2', '#f7b955'];
export function MetricValue({ data, metric, lifetime = false }: { data: Snapshot; metric: string; lifetime?: boolean }) {
  if (metric in (data.metrics || {})) return <>{number(data.metrics[metric])}</>;
  if (data.payment_tracking !== 'connected') return <span className="text-sm font-normal text-text-secondary">Учёт оплат не подключён</span>;
  const payment = lifetime ? data.payments_all_time : data.payments_period;
  if (!payment) return <span className="text-base">Нет данных</span>;
  if (metric === 'payers' || metric === 'payments') return <>{number(payment[metric])}</>;
  const key = metric === 'revenue' ? 'amount' : 'refund_amount';
  const values = payment.currencies || [];
  return values.length ? <span className="flex flex-col gap-1">{values.map(item => <span className="text-lg tabular-nums" key={item.currency}>{item[key] ?? '0'} <span className="text-sm font-normal">{item.currency}</span></span>)}</span> : <>0</>;
}

function Chart({ title, data, fields, money, currency }: { title: string; data: any[]; fields: [string,string][]; money?: boolean; currency?: string }) {
  return <Card className="min-w-0 bg-transparent"><CardHeader><CardTitle className="text-base">{title}</CardTitle></CardHeader>
    <CardContent><div className="h-64 w-full" aria-label={title}>
      <ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ top: 8, right: 12, bottom: 8, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" opacity={0.15} /><XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={28} />
        <YAxis allowDecimals={false} width={42} tick={{ fontSize: 11 }} />{money && <YAxis yAxisId="money" orientation="right" width={60} tick={{ fontSize: 11 }} label={{ value: currency, position: 'insideTopRight', fontSize: 10 }} />}
        <Tooltip contentStyle={{ background: 'var(--bg-base, #142035)', borderRadius: 12, border: '1px solid #41516a' }} /><Legend wrapperStyle={{ fontSize: 12 }} />
        {fields.map(([key,label],index) => <Line key={key} dataKey={key} name={label} stroke={colors[index % colors.length]} strokeWidth={2} dot={false} connectNulls={false} yAxisId={money && key === 'revenue' ? 'money' : 0} />)}
      </LineChart></ResponsiveContainer>
    </div></CardContent></Card>;
}

export default function AnalyticsDashboard({ data, publicView = false }: { data: Snapshot; publicView?: boolean }) {
  const selected = data.selected_metrics || Object.keys(metricLabels);
  const currencies = Array.from(new Set([...(data.payments_period?.currencies || []), ...(data.payments_all_time?.currencies || [])].map(row => row.currency)));
  const [chosenCurrency, setCurrency] = useState('');
  const currency = currencies.includes(chosenCurrency) ? chosenCurrency : currencies[0] || '';
  const paymentRows = (data.series || []).map(row => ({ date: row.date,
    payments: row.payments?.payments ?? null,
    revenue: row.payments == null ? null : Number(row.payments.currencies?.find(item => item.currency === currency)?.amount || '0'),
  }));
  const users = [['users_active','Активные'], ['users_new','Новые']].filter(([key]) => selected.includes(key)) as [string,string][];
  const messages = [['messages_in','Сообщения пользователей'], ['messages_out','Ответы бота']].filter(([key]) => selected.includes(key)) as [string,string][];
  const paymentFields: [string,string][] = [];
  if (selected.includes('payments')) paymentFields.push(['payments','Успешные платежи']);
  if (selected.includes('revenue')) paymentFields.push(['revenue','Выручка']);
  return <div className="space-y-5">
    {data.coverage !== 'available' && <p role="status" className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 text-sm text-amber-500">{data.coverage === 'unavailable' ? 'За этот период сбор ещё не вёлся, данные недоступны.' : 'Период включает время до начала сбора, показаны только реально сохранённые события.'}</p>}
    <p className="text-xs text-text-secondary">Сбор с {dateTime(data.collection_started_at, data.period.timezone)} · {data.audience_note}</p>
    {data.payment_tracking === 'connected' && <p className="text-xs text-text-secondary">Учёт оплат с {dateTime(data.payment_collection_started_at,data.period.timezone)}{data.payment_coverage === 'partial' ? ' · в выбранном периоде доступна только часть истории оплат' : data.payment_coverage === 'unavailable' ? ' · выбранный период находится до начала учёта оплат' : ''}</p>}
    {!!data.pending_events && <p className="text-sm text-amber-500">Обрабатываются события: {data.pending_events}, показатели будут обновлены</p>}
    {(!!data.unmatched_refunds || data.payment_data_incomplete) && <p className="text-sm text-amber-500">Есть возвраты, которые пока нельзя связать с подтверждённой оплатой. Они не включены в суммы.</p>}
    <section className="grid grid-cols-1 min-[420px]:grid-cols-2 xl:grid-cols-3 gap-3" aria-label="Показатели">
      {selected.map(metric => <Card key={metric} className="min-w-0 bg-bg-card"><CardContent className="p-4 sm:p-5">
        <h2 className="text-xs sm:text-sm text-text-secondary">{metricLabels[metric]}</h2>
        <div className="mt-3 text-3xl font-semibold break-words tabular-nums"><MetricValue data={data} metric={metric} /></div>
        {['payers','payments','revenue','refunds'].includes(metric) && <div className="mt-3 border-t border-border-button pt-2 text-xs text-text-secondary">За всё время сбора <div className="mt-1 text-sm"><MetricValue data={data} metric={metric} lifetime /></div></div>}
      </CardContent></Card>)}
    </section>
    {!publicView && data.conversion && <p className="text-sm text-text-secondary">Конверсия: {data.conversion.percent == null ? 'Нет данных' : `${data.conversion.percent}%`} · {data.conversion.formula}</p>}
    <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {!!users.length && <Chart title="Пользователи по дням" data={data.series || []} fields={users} />}
      {!!messages.length && <Chart title="Сообщения по дням" data={data.series || []} fields={messages} />}
    </section>
    {!!paymentFields.length && data.payment_tracking === 'connected' && <section className="space-y-2">
      {selected.includes('revenue') && currencies.length > 0 && <label className="text-sm flex flex-wrap items-center gap-2">Валюта графика <select className="rounded-md border border-border-button bg-bg-base p-2" value={currency} onChange={event => setCurrency(event.target.value)}>{currencies.map(value => <option key={value}>{value}</option>)}</select><span className="text-xs text-text-secondary">Валюты и Telegram Stars не суммируются</span></label>}
      <Chart title="Оплаты и выручка по дням" data={paymentRows} fields={paymentFields} money={selected.includes('revenue')} currency={currency} />
    </section>}
    <p className="text-xs text-text-secondary">Последняя обработка событий: {dateTime(data.last_processed_at, data.period.timezone)}</p>
  </div>;
}
