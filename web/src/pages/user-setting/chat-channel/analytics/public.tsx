import { useEffect,useState } from 'react';
import { RefreshCw,Share2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import AnalyticsDashboard from './dashboard';
import { Snapshot,publicSnapshot,dateTime } from './service';

export default function PublicTelegramAnalytics() {
  const [data,setData]=useState<Snapshot>(); const [error,setError]=useState(''); const [loading,setLoading]=useState(true);
  const [revision,setRevision]=useState(0);
  useEffect(() => {
    const robots=document.createElement('meta'); robots.name='robots'; robots.content='noindex,nofollow,noarchive'; document.head.appendChild(robots);
    const referrer=document.createElement('meta'); referrer.name='referrer'; referrer.content='no-referrer'; document.head.appendChild(referrer);
    return () => { robots.remove(); referrer.remove(); };
  },[]);
  useEffect(() => {
    const token=window.location.hash.slice(1); let stopped=false; let controller: AbortController | undefined;
    const load=async () => {
      controller?.abort(); controller=new AbortController();
      try { const value=await publicSnapshot(token,controller.signal); if (!stopped) { setData(value); setError(''); } }
      catch (e) { if (!stopped && (e as Error).name !== 'AbortError') { setData(undefined); setError((e as Error).message); } }
      finally { if (!stopped) setLoading(false); }
    };
    void load(); const timer=window.setInterval(() => { if (!document.hidden) void load(); },15000);
    const focus=() => void load(); window.addEventListener('focus',focus);
    return () => { stopped=true; controller?.abort(); clearInterval(timer); window.removeEventListener('focus',focus); };
  },[revision]);
  return <main className="h-dvh w-full overflow-y-auto overflow-x-hidden overscroll-y-contain bg-bg-base text-text-primary px-3 py-5 sm:p-8" tabIndex={0} aria-label="Аналитика Telegram-бота" data-telemetry-private><div className="mx-auto max-w-6xl space-y-5">
    <header className="flex flex-wrap justify-between gap-4 items-start"><div><p className="text-xs uppercase tracking-widest text-text-secondary">Swipies AI · Живая аналитика</p><h1 className="mt-2 text-2xl sm:text-3xl font-semibold break-words">{data?.title || 'Аналитика Telegram-бота'}</h1>{data?.bot.username && <p className="text-text-secondary mt-1">@{data.bot.username}</p>}</div><div className="flex gap-2"><Button variant="outline" aria-label="Обновить виджет" onClick={() => setRevision(value => value+1)}><RefreshCw size={16} /></Button>{'share' in navigator && <Button variant="outline" aria-label="Поделиться виджетом" onClick={() => void navigator.share({ title: data?.title || 'Аналитика бота',url:window.location.href }).catch(() => {})}><Share2 size={16} /></Button>}</div></header>
    {loading && <p role="status" className="py-16 text-center text-text-secondary">Загрузка…</p>}
    {error && <section role="alert" className="rounded-2xl border border-border-button p-8 text-center"><h2 className="text-xl font-medium">{error}</h2><p className="mt-3 text-sm text-text-secondary">Обратитесь к владельцу за новой ссылкой</p></section>}
    {data && <><div className="rounded-xl border border-border-button p-3 text-sm text-text-secondary">{data.period.start} — {data.period.end} · {data.period.timezone}<p className="mt-1 text-xs">Обновлено {dateTime(data.updated_at,data.period.timezone)} · только просмотр</p></div><AnalyticsDashboard data={data} publicView /></>}
    <footer className="pt-4 text-center text-xs text-text-secondary">Агрегированная статистика бота · <a href="https://swipies.app" target="_blank" rel="noreferrer" className="underline">Swipies AI</a></footer>
  </div></main>;
}
