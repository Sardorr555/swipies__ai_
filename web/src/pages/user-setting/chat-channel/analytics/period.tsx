import { Period } from './service';

export const defaultPeriod: Period = { period: '7d', timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Tashkent' };
const presets = [['today','Сегодня'],['yesterday','Вчера'],['7d','7 дней'],['30d','30 дней'],['custom','Свои даты']];
export default function PeriodPicker({ value, onChange, compact = false }: { value: Period; onChange: (value: Period) => void; compact?: boolean }) {
  const zones = Array.from(new Set([value.timezone, 'Asia/Tashkent', 'UTC', 'Europe/Moscow', 'Europe/Berlin', 'Asia/Almaty', 'America/New_York', ...(typeof Intl.supportedValuesOf === 'function' ? Intl.supportedValuesOf('timeZone') : [])]));
  const style = 'h-10 min-w-0 rounded-lg border border-border-button bg-bg-base px-3 text-sm';
  return <div className={`flex flex-wrap items-end gap-3 ${compact ? '' : 'rounded-xl border border-border-button p-3 sm:p-4'}`}>
    <label className="grid gap-1 text-xs text-text-secondary">Период<select aria-label="Период" className={style} value={value.period} onChange={event => {
      const period=event.target.value; const today=new Date().toLocaleDateString('en-CA');
      onChange({ ...value, period, ...(period === 'custom' ? { start: value.start || today, end: value.end || today } : {}) });
    }}>{presets.map(([key,label]) => <option key={key} value={key}>{label}</option>)}</select></label>
    {value.period === 'custom' && <><label className="grid gap-1 text-xs text-text-secondary">С<input aria-label="Дата начала" className={style} type="date" value={value.start || ''} onChange={event => onChange({ ...value, start: event.target.value })} /></label><label className="grid gap-1 text-xs text-text-secondary">По<input aria-label="Дата конца" className={style} type="date" value={value.end || ''} onChange={event => onChange({ ...value, end: event.target.value })} /></label></>}
    <label className="grid gap-1 text-xs text-text-secondary max-w-full">Часовой пояс<select aria-label="Часовой пояс" className={`${style} max-w-64`} value={value.timezone} onChange={event => onChange({ ...value, timezone: event.target.value })}>{zones.map(zone => <option key={zone}>{zone}</option>)}</select></label>
  </div>;
}
