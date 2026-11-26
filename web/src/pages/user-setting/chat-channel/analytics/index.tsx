import { useState } from 'react';
import { useParams, Link } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, RefreshCw, Share2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import AnalyticsDashboard from './dashboard';
import PeriodPicker, { defaultPeriod } from './period';
import SharePanel from './share-panel';
import { Snapshot, Period, endpoint, privateRequest, periodQuery, number, dateTime } from './service';

type Chats = { items: Array<{ id: string; name: string; type: string; active_users: number; messages: number; last_activity: string; payments: number | null }>; total: number; page: number; page_size: number };
const chatTypes: Record<string,string> = { private: 'Личный диалог', group: 'Группа', supergroup: 'Супергруппа', channel: 'Канал', unknown: 'Неизвестно' };

export default function TelegramAnalytics() {
  const { channelId = '' }=useParams();
  const [period,setPeriod]=useState<Period>(defaultPeriod);
  const [share,setShare]=useState(false); const [search,setSearch]=useState(''); const [sort,setSort]=useState('last_activity'); const [page,setPage]=useState(1);
  const { data,error,isPending,isFetching,refetch }=useQuery({ queryKey: ['telegram-analytics',channelId,period],
    queryFn: ({ signal }) => privateRequest<Snapshot>(endpoint(channelId)+'?'+periodQuery(period),'GET',undefined,signal), refetchInterval: 15000 });
  const chats=useQuery({ queryKey: ['telegram-analytics-chats',channelId,period,search,sort,page],
    queryFn: ({ signal }) => privateRequest<Chats>(endpoint(channelId,'/chats')+'?'+periodQuery(period)+`&search=${encodeURIComponent(search)}&sort=${sort}&page=${page}&page_size=20`,'GET',undefined,signal),
    enabled: data?.initialized === true, refetchInterval: 15000 });
  const updatePeriod=(value: Period) => { setPeriod(value); setPage(1); };
  return <main className="h-full overflow-y-auto p-3 sm:p-6 text-text-primary"><div className="mx-auto max-w-7xl space-y-5 pb-10">
    <Link to="/user-setting/chat-channel" className="inline-flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary"><ArrowLeft size={16} />Chat Channels</Link>
    <header className="flex flex-wrap items-start justify-between gap-4"><div className="min-w-0"><p className="text-xs font-medium uppercase tracking-widest text-text-secondary">Telegram · Аналитика</p><h1 className="mt-1 text-2xl sm:text-3xl font-semibold break-words">{data?.bot.name || 'Аналитика бота'}</h1>{data?.bot.username && <p className="mt-1 text-text-secondary">@{data.bot.username}</p>}
      {data?.connection && <p className="mt-2 text-xs text-text-secondary"><span className={data.connection.polling_active ? 'text-green-500' : 'text-amber-500'}>●</span> {data.connection.polling_active ? 'Подключён' : data.connection.enabled ? 'Соединение не активно' : 'Отключён'}</p>}
    </div><div className="flex flex-wrap gap-2"><Button variant="outline" disabled={isFetching} onClick={() => { void refetch(); void chats.refetch(); }}><RefreshCw size={16} className={isFetching ? 'animate-spin' : ''} />Обновить</Button><Button disabled={!data?.initialized} onClick={() => setShare(true)}><Share2 size={16} />Поделиться</Button></div></header>
    <PeriodPicker value={period} onChange={updatePeriod} />
    {data?.updated_at && <p className="text-xs text-text-secondary">Обновлено {dateTime(data.updated_at,period.timezone)} · данные обновляются каждые 15 секунд</p>}
    {isPending && <p role="status" className="py-12 text-center text-text-secondary">Загружаем аналитику…</p>}
    {error && <p role="alert" className="rounded-xl border border-state-error/30 p-4 text-state-error">{error.message}</p>}
    {data?.initialized === false && <Card className="bg-transparent"><CardContent className="p-6 text-text-secondary">{data.message}</CardContent></Card>}
    {data?.initialized && <><AnalyticsDashboard data={data} />
      <section className="space-y-3"><header className="flex flex-wrap justify-between items-center gap-3"><div><h2 className="text-lg font-semibold">Чаты с доступными событиями</h2><p className="text-xs text-text-secondary">Участники групп и подписчики: нет данных, Telegram не передаёт их полный состав</p></div>
        <div className="flex flex-wrap gap-2"><Input className="w-52" aria-label="Поиск чатов" placeholder="Найти чат" value={search} onChange={event => { setSearch(event.target.value); setPage(1); }} /><select aria-label="Сортировка чатов" className="rounded-lg border border-border-button bg-bg-base px-2 text-sm" value={sort} onChange={event => { setSort(event.target.value); setPage(1); }}><option value="last_activity">Последняя активность</option><option value="active_users">Активные пользователи</option><option value="messages">Сообщения</option><option value="name">Название</option></select></div></header>
        {chats.error && <p role="alert" className="text-state-error text-sm">{chats.error.message}</p>}
        <div className="overflow-x-auto rounded-xl border border-border-button"><table className="w-full min-w-[660px] text-sm"><thead className="bg-bg-card text-text-secondary"><tr>{['Чат','Тип','Активные','Сообщения','Последняя активность','Платежи'].map(label => <th key={label} className="px-4 py-3 text-left font-medium">{label}</th>)}</tr></thead><tbody>{chats.data?.items.map(row => <tr key={row.id} className="border-t border-border-button"><td className="px-4 py-3 max-w-64 break-words">{row.name}</td><td className="px-4 py-3">{chatTypes[row.type] || row.type}</td><td className="px-4 py-3">{number(row.active_users)}</td><td className="px-4 py-3">{number(row.messages)}</td><td className="px-4 py-3">{dateTime(row.last_activity,period.timezone)}</td><td className="px-4 py-3">{row.payments == null ? 'Нет данных' : number(row.payments)}</td></tr>)}{!chats.data?.items.length && <tr><td colSpan={6} className="py-8 text-center text-text-secondary">{chats.isPending ? 'Загружаем чаты…' : 'В доступной истории чатов пока нет'}</td></tr>}</tbody></table></div>
        <div className="flex flex-wrap justify-between items-center gap-2 text-sm text-text-secondary"><span>Всего чатов: {number(chats.data?.total)}</span><div className="flex items-center gap-3"><Button variant="outline" disabled={page <= 1} onClick={() => setPage(value => value-1)}>Назад</Button><span>Страница {page}</span><Button variant="outline" disabled={!chats.data || page*chats.data.page_size >= chats.data.total} onClick={() => setPage(value => value+1)}>Дальше</Button></div></div>
      </section>
    </>}
    {share && data?.initialized && <SharePanel channel={channelId} data={data} close={() => setShare(false)} />}
  </div></main>;
}
