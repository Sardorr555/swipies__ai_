import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Copy, Download, Share2, Trash2, X } from 'lucide-react';
import PeriodPicker from './period';
import { CreatedShare, Share, WidgetSettings, Snapshot, endpoint, privateRequest, metricLabels, downloadCard, dateTime } from './service';

export default function SharePanel({ channel, data, close }: { channel: string; data: Snapshot; close: () => void }) {
  const cache=useQueryClient();
  const [settings,setSettings]=useState<WidgetSettings>({ ...data.period, title: data.bot.name,
    metrics: ['users_total','users_active','users_new','messages_in','messages_out'], show_revenue: false, include_link: true, expires_days: 7 });
  const [created,setCreated]=useState<CreatedShare>();
  const [error,setError]=useState(''); const [busy,setBusy]=useState(false); const [notice,setNotice]=useState('');
  const [format,setFormat]=useState('story');
  const { data: shares=[] }=useQuery({ queryKey: ['telegram-shares',channel], queryFn: () => privateRequest<Share[]>(endpoint(channel,'/shares')) });
  const url=created ? new URL(created.path,window.location.origin).toString() : '';
  const run=async (work: () => Promise<void>) => { setError(''); setNotice(''); setBusy(true); try { await work(); } catch (e) { if ((e as Error).name !== 'AbortError') setError((e as Error).message); } finally { setBusy(false); } };
  const update=(next: Partial<WidgetSettings>) => { setSettings(current => ({ ...current,...next })); setCreated(undefined); };
  const card=async (system=false) => downloadCard(channel,created ? { token: created.token, format } : { ...settings, format },`swipies-telegram-${format}.png`,system);
  return <section role="dialog" aria-modal="true" aria-labelledby="share-title" className="fixed inset-0 z-50 bg-black/60 p-2 sm:p-6 overflow-y-auto" data-telemetry-private>
    <div className="mx-auto max-w-3xl rounded-2xl border border-border-button bg-bg-base p-4 sm:p-6 shadow-xl space-y-5">
      <header className="flex justify-between gap-3"><div><h2 id="share-title" className="text-xl font-semibold">Поделиться аналитикой</h2><p className="mt-1 text-xs text-text-secondary">Только выбранные агрегаты, без переписок и данных пользователей</p></div><Button variant="ghost" aria-label="Закрыть" onClick={close}><X size={18} /></Button></header>
      <label className="grid gap-2 text-sm">Название виджета<Input value={settings.title} maxLength={120} onChange={event => update({ title: event.target.value })} /></label>
      <fieldset><legend className="mb-2 text-sm font-medium">Показатели</legend><div className="grid sm:grid-cols-2 gap-2">{Object.entries(metricLabels).map(([key,label]) => <label key={key} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={settings.metrics.includes(key)} disabled={['revenue','refunds'].includes(key) && !settings.show_revenue} onChange={event => update({ metrics: event.target.checked ? [...settings.metrics,key] : settings.metrics.filter(value => value !== key) })} />{label}</label>)}</div></fieldset>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={settings.show_revenue} onChange={event => update({ show_revenue: event.target.checked, ...(!event.target.checked ? { metrics: settings.metrics.filter(key => !['revenue','refunds'].includes(key)) } : {}) })} />Разрешить показ выручки и возвратов</label>
      <PeriodPicker value={settings} onChange={value => update(value)} compact />
      <div className="grid gap-3 sm:grid-cols-2"><label className="grid gap-1 text-sm">Срок ссылки<select className="rounded-lg border border-border-button bg-bg-base p-2" value={settings.expires_days ?? 'forever'} onChange={event => update({ expires_days: event.target.value === 'forever' ? null : Number(event.target.value) })}><option value="1">1 день</option><option value="7">7 дней</option><option value="30">30 дней</option><option value="forever">Бессрочно</option></select></label><label className="grid gap-1 text-sm">Карточка PNG<select className="rounded-lg border border-border-button bg-bg-base p-2" value={format} onChange={event => setFormat(event.target.value)}><option value="story">Stories, 1080×1920</option><option value="square">Публикация, 1080×1080</option></select></label></div>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={settings.include_link} onChange={event => update({ include_link: event.target.checked })} />Добавить ссылку на живой виджет в PNG</label>
      <div className="flex flex-wrap gap-2"><Button disabled={busy || !settings.metrics.length} onClick={() => void run(async () => { setCreated(await privateRequest<CreatedShare>(endpoint(channel,'/shares'),'POST',settings)); await cache.invalidateQueries({ queryKey: ['telegram-shares',channel] }); })}>Создать живую ссылку</Button>
        <Button variant="outline" disabled={busy || !settings.metrics.length} onClick={() => void run(() => card())}><Download size={16} />Скачать карточку</Button>
        {'share' in navigator && <Button variant="outline" disabled={busy} onClick={() => void run(() => card(true))}><Share2 size={16} />Поделиться PNG</Button>}</div>
      {settings.include_link && !created && <p className="text-xs text-text-secondary">Чтобы добавить ссылку в PNG, сначала создайте живую ссылку</p>}
      {created && <div className="space-y-3 rounded-xl border border-border-button p-3"><p className="text-xs text-text-secondary">Сохраните ссылку сейчас, её токен не хранится в открытом виде</p><Input aria-label="Живая ссылка" readOnly value={url} />
        <div className="flex flex-wrap gap-2"><Button variant="outline" onClick={() => void run(async () => { await navigator.clipboard.writeText(url); setNotice('Ссылка скопирована'); })}><Copy size={16} />Скопировать ссылку</Button>{'share' in navigator && <Button variant="outline" onClick={() => void run(async () => { await navigator.share({ title: created.title, url }); })}><Share2 size={16} />Поделиться ссылкой</Button>}<a href={url} target="_blank" rel="noreferrer" className="text-sm underline self-center">Открыть виджет</a></div>
        <label className="grid gap-1 text-xs text-text-secondary">Код для сайта<textarea className="w-full rounded-lg border border-border-button bg-bg-base p-2 text-xs" readOnly rows={3} value={`<iframe src="${url}" title="Аналитика Telegram-бота" width="100%" height="900" loading="lazy" referrerpolicy="no-referrer" sandbox="allow-scripts allow-same-origin" style="border:0"></iframe>`} /></label>
      </div>}
      <p className="text-xs text-text-secondary">Instagram: скачайте PNG или передайте его через системное меню. Автоматическая публикация не выполняется.</p>
      {error && <p role="alert" className="text-sm text-state-error">{error}</p>}{notice && <p role="status" className="text-sm text-green-500">{notice}</p>}
      <section className="space-y-2 border-t border-border-button pt-4"><h3 className="font-medium">Действующие и отозванные ссылки</h3>{shares.length === 0 && <p className="text-sm text-text-secondary">Ссылок пока нет</p>}{shares.map(share => <div key={share.id} className="flex items-center justify-between gap-2 rounded-lg bg-bg-card p-3"><div className="min-w-0"><p className="truncate text-sm">{share.title}</p><p className="text-xs text-text-secondary">{share.revoked_at ? 'Отозвана' : share.expires_at && new Date(share.expires_at) < new Date() ? 'Истекла' : share.expires_at ? 'До '+dateTime(share.expires_at,settings.timezone) : 'Бессрочно'}</p></div>{!share.revoked_at && <Button variant="outline" disabled={busy} aria-label={`Отозвать ${share.title}`} onClick={() => void run(async () => { await privateRequest(endpoint(channel,`/shares/${share.id}`),'DELETE'); if (created?.id === share.id) setCreated(undefined); await cache.invalidateQueries({ queryKey: ['telegram-shares',channel] }); })}><Trash2 size={14} />Отозвать</Button>}</div>)}</section>
    </div>
  </section>;
}
