import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import message from '@/components/ui/message';
import { 
  Key, 
  ArrowRight, 
  Copy, 
  Check, 
  ShieldCheck, 
  Clock, 
  Edit2, 
  Trash2, 
  Plus, 
  Loader2, 
  CheckCircle2, 
  Download, 
  Eye, 
  EyeOff, 
  Terminal, 
  Sparkles, 
  Server, 
  RefreshCw, 
  Calendar, 
  ChevronDown, 
  ChevronUp 
} from 'lucide-react';
import { ProfileSettingWrapperCard } from '../components/user-setting-header';
import { 
  getUserLicensePricing, 
  listLicenses, 
  renameLicense, 
  revokeLicense 
} from '@/services/license-service';
import { useNavigate } from 'react-router';

interface PricingConfig {
  price_6_months: number;
  price_12_months: number;
  price_per_month_custom?: number;
}

interface LicenseItem {
  id: string;
  name: string;
  license_key: string;
  duration_months: number;
  expiry_date?: string;
  status: 'active' | 'pending' | 'revoked' | 'expired';
  is_paid: boolean;
  payment_id?: string;
  create_time?: string | number;
}

const fmtUZS = (n: number) =>
  new Intl.NumberFormat('uz-UZ').format(n) + ' UZS';

const LicensePurchasePage = () => {
  const { t } = useTranslation('translation', { keyPrefix: 'license' });
  const navigate = useNavigate();
  const [selectedMonths, setSelectedMonths] = useState<6 | 12>(12);
  const [pricing, setPricing] = useState<PricingConfig>({
    price_6_months: 300000,
    price_12_months: 500000,
  });

  const [licenses, setLicenses] = useState<LicenseItem[]>([]);
  const [loadingLicenses, setLoadingLicenses] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [copiedDockerId, setCopiedDockerId] = useState<string | null>(null);
  const [revealedKeys, setRevealedKeys] = useState<Record<string, boolean>>({});
  const [showGuide, setShowGuide] = useState(false);

  // Rename state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  const fetchUserLicenses = () => {
    setLoadingLicenses(true);
    listLicenses()
      .then((res: any) => {
        if (res?.data?.code === 0 && Array.isArray(res.data.data)) {
          // Filter to show active/paid or user licenses
          setLicenses(res.data.data.filter((l: LicenseItem) => l.is_paid || l.status === 'active' || l.license_key));
        }
      })
      .catch((err) => console.error('Failed to load user licenses', err))
      .finally(() => setLoadingLicenses(false));
  };

  useEffect(() => {
    getUserLicensePricing()
      .then((res: any) => {
        if (res?.data?.code === 0 && res.data.data) {
          setPricing(res.data.data);
        }
      })
      .catch(() => {});

    fetchUserLicenses();
  }, []);

  const handleProceedToCheckout = (period: 6 | 12) => {
    navigate(`/checkout?plan=license&period=${period}`);
  };

  const handleCopyKey = (key: string, id: string) => {
    if (!key) return;
    navigator.clipboard.writeText(key);
    setCopiedId(id);
    message.success(t('keyCopied', { defaultValue: 'Лицензионный ключ скопирован!' }));
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleCopyDockerSnippet = (key: string, id: string) => {
    if (!key) return;
    const snippet = `RAGFLOW_LICENSE_KEY="${key}"`;
    navigator.clipboard.writeText(snippet);
    setCopiedDockerId(id);
    message.success(t('envCopied', { defaultValue: 'Переменная для docker/.env скопирована!' }));
    setTimeout(() => setCopiedDockerId(null), 2000);
  };

  const handleDownloadKey = (key: string, name: string) => {
    if (!key) return;
    const blob = new Blob([key], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const cleanName = (name || 'key').toLowerCase().replace(/[^a-z0-9]/gi, '_');
    link.download = `swipies_license_${cleanName}.key`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    message.success(t('keyDownloaded', { defaultValue: 'Лицензионный файл .key скачан!' }));
  };

  const toggleRevealKey = (id: string) => {
    setRevealedKeys((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleStartRename = (license: LicenseItem) => {
    setEditingId(license.id);
    setEditingName(license.name || '');
  };

  const handleSaveRename = async (licenseId: string) => {
    if (!editingName.trim()) return;
    try {
      const res: any = await renameLicense(licenseId, editingName.trim());
      if (res?.data?.code === 0) {
        message.success(t('renameSuccess', { defaultValue: 'Имя лицензии обновлено' }));
        setEditingId(null);
        fetchUserLicenses();
      }
    } catch {
      message.error(t('renameError', { defaultValue: 'Не удалось обновить имя лицензии' }));
    }
  };

  const handleRevoke = async (licenseId: string) => {
    if (!window.confirm(t('revokeConfirm', { defaultValue: 'Вы уверены, что хотите отозвать данный лицензионный ключ?' }))) return;
    try {
      const res: any = await revokeLicense(licenseId);
      if (res?.data?.code === 0) {
        message.success(t('revokeSuccess', { defaultValue: 'Лицензионный ключ отозван' }));
        fetchUserLicenses();
      }
    } catch {
      message.error(t('revokeError', { defaultValue: 'Не удалось отозвать лицензию' }));
    }
  };

  const getExpirationInfo = (expiryDate?: string, durationMonths: number = 12) => {
    if (!expiryDate) return { daysLeft: null, percent: 100, isExpired: false, formattedDate: t('permanent', { defaultValue: 'Бессрочно' }) };
    const end = new Date(expiryDate).getTime();
    const now = Date.now();
    const diffDays = Math.ceil((end - now) / (1000 * 60 * 60 * 24));
    const totalDays = durationMonths * 30;
    const percent = Math.max(0, Math.min(100, Math.round((diffDays / totalDays) * 100)));
    const formattedDate = String(expiryDate).split('T')[0];
    return {
      daysLeft: diffDays,
      percent,
      isExpired: diffDays <= 0,
      formattedDate,
    };
  };

  const activeLicensesCount = licenses.filter((l) => l.is_paid || l.status === 'active').length;

  return (
    <ProfileSettingWrapperCard
      header={
        <header className="flex flex-col gap-1 w-full">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-extrabold tracking-tight text-text-primary flex items-center gap-2.5">
              <Key className="text-accent-primary" size={24} />
              {t('title', { defaultValue: 'Лицензионные ключи (Self-Hosted)' })}
            </h2>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchUserLicenses}
              disabled={loadingLicenses}
              className="gap-1.5 text-xs text-text-secondary border-border-default hover:text-text-primary"
            >
              <RefreshCw size={13} className={loadingLicenses ? 'animate-spin' : ''} />
              {t('refresh', { defaultValue: 'Обновить' })}
            </Button>
          </div>
          <p className="text-text-secondary text-sm">
            {t('description', { defaultValue: 'Управляйте лицензионными ключами Swipies AI для развертывания на собственных серверах и дата-центрах.' })}
          </p>
        </header>
      }
    >
      <div className="h-full overflow-x-hidden overflow-y-auto pb-16 pr-1 mt-5 space-y-8 w-full max-w-6xl mx-auto px-1 sm:px-4">
        
        {/* TOP KPI SUMMARY CARDS */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 sm:gap-4">
          {/* Card 1: Активные лицензии */}
          <div className="group relative rounded-2xl border border-border-default/80 bg-bg-card/40 p-4 sm:p-5 backdrop-blur-md transition-all duration-300 hover:border-emerald-500/40 hover:shadow-[0_4px_24px_-4px_rgba(16,185,129,0.15)] flex flex-col justify-between min-h-[152px] overflow-hidden">
            <div className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-emerald-500/10 blur-xl transition-all group-hover:bg-emerald-500/20" />
            
            <div className="flex items-center justify-between gap-2 relative z-10">
              <span className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
                {t('activeLicensesTitle', { defaultValue: 'Активные лицензии' })}
              </span>
              <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0">
                <ShieldCheck size={18} />
              </div>
            </div>

            <div className="space-y-1 relative z-10">
              <div className="flex items-baseline gap-2 flex-wrap">
                <span className="text-2xl sm:text-3xl font-black text-text-primary tracking-tight">
                  {activeLicensesCount}
                </span>
                <span className="inline-flex items-center text-xs font-semibold px-2.5 py-0.5 rounded-md bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                  {activeLicensesCount === 1 
                    ? t('oneKeyActive', { defaultValue: '1 ключ активен' }) 
                    : activeLicensesCount > 1 
                      ? t('keysActive', { count: activeLicensesCount, defaultValue: `${activeLicensesCount} ключа(ей) активно` }) 
                      : t('zeroKeys', { defaultValue: '0 ключей' })}
                </span>
              </div>
              <p className="text-xs text-text-secondary leading-snug">
                {t('localClusterDesc', { defaultValue: 'Локальный защищенный кластер' })}
              </p>
            </div>

            <div className="pt-2.5 border-t border-border-default/50 flex items-center gap-2 text-xs text-emerald-400 font-medium relative z-10">
              <span className="relative flex h-2 w-2 shrink-0">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>
              <span className="truncate" title={t('readyToDeploy', { defaultValue: 'Готовы к развертыванию на узлах' })}>
                {t('readyToDeploy', { defaultValue: 'Готовы к развертыванию на узлах' })}
              </span>
            </div>
          </div>

          {/* Card 2: Тип редакции */}
          <div className="group relative rounded-2xl border border-border-default/80 bg-bg-card/40 p-4 sm:p-5 backdrop-blur-md transition-all duration-300 hover:border-indigo-500/40 hover:shadow-[0_4px_24px_-4px_rgba(99,102,241,0.15)] flex flex-col justify-between min-h-[152px] overflow-hidden">
            <div className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-indigo-500/10 blur-xl transition-all group-hover:bg-indigo-500/20" />
            
            <div className="flex items-center justify-between gap-2 relative z-10">
              <span className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
                {t('editionTypeTitle', { defaultValue: 'Тип редакции' })}
              </span>
              <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shrink-0">
                <Server size={18} />
              </div>
            </div>

            <div className="space-y-1 relative z-10">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-lg sm:text-xl font-extrabold text-text-primary tracking-tight">
                  {t('selfHosted', { defaultValue: 'Self-Hosted' })}
                </span>
                <span className="inline-flex items-center text-[11px] font-bold px-2 py-0.5 rounded-md bg-indigo-500/15 text-indigo-400 border border-indigo-500/30 uppercase tracking-wide">
                  {t('enterprise', { defaultValue: 'Enterprise' })}
                </span>
              </div>
              <p className="text-xs text-text-secondary leading-snug">
                {t('dataIsolationDesc', { defaultValue: 'Локальная изоляция данных' })}
              </p>
            </div>

            <div className="pt-2.5 border-t border-border-default/50 flex items-center gap-2 text-xs text-indigo-400 font-medium relative z-10">
              <span className="size-1.5 rounded-full bg-indigo-400 shrink-0" />
              <span className="truncate" title={t('unlimitedDocsLlm', { defaultValue: 'Безлимитные документы и LLM' })}>
                {t('unlimitedDocsLlm', { defaultValue: 'Безлимитные документы и LLM' })}
              </span>
            </div>
          </div>

          {/* Card 3: Безопасность */}
          <div className="group relative rounded-2xl border border-border-default/80 bg-bg-card/40 p-4 sm:p-5 backdrop-blur-md transition-all duration-300 hover:border-violet-500/40 hover:shadow-[0_4px_24px_-4px_rgba(139,92,246,0.15)] flex flex-col justify-between min-h-[152px] overflow-hidden sm:col-span-2 lg:col-span-1">
            <div className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-violet-500/10 blur-xl transition-all group-hover:bg-violet-500/20" />
            
            <div className="flex items-center justify-between gap-2 relative z-10">
              <span className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
                {t('securityTitle', { defaultValue: 'Безопасность' })}
              </span>
              <div className="p-2 rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/20 shrink-0">
                <Sparkles size={18} />
              </div>
            </div>

            <div className="space-y-1 relative z-10">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-lg sm:text-xl font-extrabold text-text-primary tracking-tight">
                  {t('rsa2048', { defaultValue: 'RSA-2048' })}
                </span>
                <span className="inline-flex items-center text-[11px] font-bold px-2 py-0.5 rounded-md bg-violet-500/15 text-violet-400 border border-violet-500/30 uppercase tracking-wide">
                  {t('signature', { defaultValue: 'Signature' })}
                </span>
              </div>
              <p className="text-xs text-text-secondary leading-snug">
                {t('offlineWorkDesc', { defaultValue: 'Абсолютно автономная работа' })}
              </p>
            </div>

            <div className="pt-2.5 border-t border-border-default/50 flex items-center gap-2 text-xs text-violet-400 font-medium relative z-10">
              <span className="size-1.5 rounded-full bg-violet-400 shrink-0" />
              <span className="truncate" title={t('noExternalDeps', { defaultValue: 'Без привязки к внешним серверам' })}>
                {t('noExternalDeps', { defaultValue: 'Без привязки к внешним серверам' })}
              </span>
            </div>
          </div>
        </div>

        {/* SECTION 1: MY PURCHASED LICENSES */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-text-primary flex items-center gap-2">
              <ShieldCheck className="text-emerald-400" size={20} />
              {t('purchasedTitle', { defaultValue: 'Купленные лицензионные ключи' })}
            </h3>
            <span className="text-xs text-text-secondary font-medium bg-bg-card/50 px-2.5 py-1 rounded-full border border-border-default">
              {t('totalKeys', { defaultValue: 'Всего ключей:' })} <strong className="text-text-primary">{licenses.length}</strong>
            </span>
          </div>

          {loadingLicenses ? (
            <div className="flex flex-col items-center justify-center py-12 rounded-2xl border border-border-default bg-bg-card/20 text-text-secondary gap-3 text-sm">
              <Loader2 className="animate-spin text-accent-primary" size={24} />
              <span>{t('loading', { defaultValue: 'Загрузка лицензионных ключей...' })}</span>
            </div>
          ) : licenses.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 rounded-2xl border border-dashed border-border-default bg-bg-card/10 text-center p-8 space-y-4">
              <div className="p-4 bg-accent-primary/10 rounded-2xl text-accent-primary">
                <Key size={32} />
              </div>
              <div className="space-y-1.5 max-w-md">
                <p className="text-base font-bold text-text-primary">{t('noKeysTitle', { defaultValue: 'У вас пока нет лицензионных ключей' })}</p>
                <p className="text-xs text-text-secondary leading-relaxed">
                  {t('noKeysDesc', { defaultValue: 'Выберите период подписки ниже, чтобы мгновенно получить криптографический ключ для автономного сервера Swipies AI.' })}
                </p>
              </div>
              <Button
                onClick={() => setSelectedMonths(12)}
                className="bg-accent-primary hover:bg-accent-primary/90 text-white rounded-xl text-xs font-semibold gap-1.5"
              >
                <Plus size={14} /> {t('choosePlanBelow', { defaultValue: 'Выбрать тариф ниже' })}
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-5">
              {licenses.map((lic) => {
                const isRevealed = !!revealedKeys[lic.id];
                const expInfo = getExpirationInfo(lic.expiry_date, lic.duration_months);

                return (
                  <div
                    key={lic.id}
                    className="rounded-2xl border border-border-default bg-bg-card/40 p-5 sm:p-6 backdrop-blur-md space-y-5 transition-all hover:border-accent-primary/50 shadow-sm relative overflow-hidden"
                  >
                    {/* Top Bar: Title, Inline Edit, Status Badges, Revoke */}
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-default/60 pb-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2.5 rounded-xl bg-accent-primary/10 text-accent-primary">
                          <Server size={20} />
                        </div>
                        {editingId === lic.id ? (
                          <div className="flex items-center gap-2">
                            <Input
                              value={editingName}
                              onChange={(e) => setEditingName(e.target.value)}
                              className="h-8 text-sm bg-bg-base border-accent-primary max-w-[240px]"
                              placeholder={t('renamePlaceholder', { defaultValue: 'Имя сервера/лицензии' })}
                              autoFocus
                            />
                            <Button
                              size="sm"
                              className="h-8 text-xs bg-accent-primary hover:bg-accent-primary/90 text-white"
                              onClick={() => handleSaveRename(lic.id)}
                            >
                              {t('save', { defaultValue: 'Сохранить' })}
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-8 text-xs text-text-secondary"
                              onClick={() => setEditingId(null)}
                            >
                              {t('cancel', { defaultValue: 'Отмена' })}
                            </Button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-base text-text-primary">
                              {lic.name || t('defaultKeyName', { defaultValue: 'Swipies Self-Hosted Key' })}
                            </span>
                            <button
                              onClick={() => handleStartRename(lic)}
                              className="text-text-secondary hover:text-accent-primary transition-colors p-1"
                              title={t('rename', { defaultValue: 'Переименовать' })}
                            >
                              <Edit2 size={13} />
                            </button>
                          </div>
                        )}
                      </div>

                      {/* Status & Actions */}
                      <div className="flex items-center gap-2.5">
                        <span className="text-xs bg-bg-base text-text-secondary px-2.5 py-1 rounded-full border border-border-default font-medium">
                          {t('months', { count: lic.duration_months, defaultValue: `${lic.duration_months} мес.` })}
                        </span>

                        {lic.status === 'active' || lic.is_paid ? (
                          <span className="flex items-center gap-1.5 text-xs font-semibold bg-emerald-500/15 text-emerald-400 px-3 py-1 rounded-full border border-emerald-500/20">
                            <CheckCircle2 size={13} /> {t('active', { defaultValue: 'Активен' })}
                          </span>
                        ) : (
                          <span className="flex items-center gap-1.5 text-xs font-semibold bg-amber-500/15 text-amber-400 px-3 py-1 rounded-full border border-amber-500/20">
                            <Clock size={13} /> {lic.status}
                          </span>
                        )}
                        
                        <button
                          onClick={() => handleRevoke(lic.id)}
                          className="text-rose-400/80 hover:text-rose-400 hover:bg-rose-500/10 transition-colors p-1.5 rounded-lg ml-1 cursor-pointer"
                          title={t('revoke', { defaultValue: 'Отозвать лицензию' })}
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </div>

                    {/* Middle: License Key Box with Actions */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-[11px] font-bold tracking-wider uppercase text-text-secondary flex items-center gap-1.5">
                          <Terminal size={12} className="text-accent-primary" />
                          {t('rsaKey', { defaultValue: 'RSA Лицензионный ключ' })}
                        </label>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => toggleRevealKey(lic.id)}
                            className="text-[11px] text-text-secondary hover:text-text-primary transition-colors flex items-center gap-1 px-2 py-0.5 rounded hover:bg-bg-card cursor-pointer"
                          >
                            {isRevealed ? (
                              <>
                                <EyeOff size={12} /> {t('hide', { defaultValue: 'Скрыть' })}
                              </>
                            ) : (
                              <>
                                <Eye size={12} /> {t('showFullKey', { defaultValue: 'Показать полный ключ' })}
                              </>
                            )}
                          </button>
                        </div>
                      </div>

                      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 bg-slate-950/70 border border-border-default rounded-xl p-3 font-mono text-xs text-indigo-300">
                        <div className="flex-1 overflow-hidden select-all text-slate-300">
                          {isRevealed ? (
                            <p className="break-all whitespace-pre-wrap leading-relaxed max-h-32 overflow-y-auto">
                              {lic.license_key || t('generatingKey', { defaultValue: 'Генерация ключа...' })}
                            </p>
                          ) : (
                            <div className="flex items-center gap-2">
                              <span className="truncate">
                                {lic.license_key ? `${lic.license_key.slice(0, 32)}••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••` : t('waitingGeneration', { defaultValue: 'Ожидание генерации...' })}
                              </span>
                            </div>
                          )}
                        </div>

                        {lic.license_key && (
                          <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-center pt-2 sm:pt-0 border-t sm:border-t-0 border-border-default/50 w-full sm:w-auto justify-end">
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => handleCopyKey(lic.license_key, lic.id)}
                              className="h-8 px-3 text-xs bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700/80 gap-1.5"
                            >
                              {copiedId === lic.id ? (
                                <>
                                  <Check size={13} className="text-emerald-400" />
                                  <span className="text-emerald-400">{t('copied', { defaultValue: 'Скопировано' })}</span>
                                </>
                              ) : (
                                <>
                                  <Copy size={13} />
                                  <span>{t('copy', { defaultValue: 'Копировать' })}</span>
                                </>
                              )}
                            </Button>

                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => handleDownloadKey(lic.license_key, lic.name)}
                              className="h-8 px-3 text-xs bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700/80 gap-1.5"
                              title={t('downloadKey', { defaultValue: 'Скачать файл ключа' })}
                            >
                              <Download size={13} />
                              <span>.key</span>
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Quick Docker Activation Snippet */}
                    {lic.license_key && (
                      <div className="bg-bg-base/40 rounded-xl border border-border-default/50 p-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs">
                        <div className="flex items-center gap-2 text-text-secondary truncate">
                          <span className="text-slate-400 font-medium">{t('forEnv', { defaultValue: 'Для .env:' })}</span>
                          <code className="font-mono text-[11px] text-slate-300 truncate max-w-sm sm:max-w-md">
                            RAGFLOW_LICENSE_KEY="{lic.license_key.slice(0, 24)}..."
                          </code>
                        </div>
                        <button
                          onClick={() => handleCopyDockerSnippet(lic.license_key, lic.id)}
                          className="text-[11px] text-accent-primary hover:underline flex items-center gap-1 shrink-0 font-medium cursor-pointer"
                        >
                          {copiedDockerId === lic.id ? (
                            <>
                              <Check size={12} className="text-emerald-400" /> {t('copiedToClipboard', { defaultValue: 'Скопировано в буфер' })}
                            </>
                          ) : (
                            <>
                              <Copy size={12} /> {t('copyEnvSnippet', { defaultValue: 'Скопировать строку для .env' })}
                            </>
                          )}
                        </button>
                      </div>
                    )}

                    {/* Footer Info: Expiry progress & Details */}
                    <div className="pt-2 border-t border-border-default/50 space-y-2">
                      <div className="flex flex-wrap items-center justify-between text-xs text-text-secondary gap-2">
                        <div className="flex items-center gap-4">
                          <span className="flex items-center gap-1.5">
                            <Calendar size={13} className="text-accent-primary" />
                            {t('expires', { defaultValue: 'Истекает:' })}{' '}
                            <strong className="text-text-primary ml-1">
                              {expInfo.formattedDate}
                            </strong>
                          </span>
                          {expInfo.daysLeft !== null && (
                            <span className={expInfo.isExpired ? 'text-rose-400' : 'text-emerald-400'}>
                              ({expInfo.isExpired ? t('expired', { defaultValue: 'Срок действия истек' }) : t('daysLeft', { count: expInfo.daysLeft, defaultValue: `Осталось ${expInfo.daysLeft} дн.` })})
                            </span>
                          )}
                        </div>

                        {lic.payment_id && (
                          <span className="text-[11px] text-text-secondary font-mono">
                            TxID: {String(lic.payment_id).slice(-10)}
                          </span>
                        )}
                      </div>

                      {/* Expiration bar */}
                      {expInfo.daysLeft !== null && !expInfo.isExpired && (
                        <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden border border-slate-800">
                          <div
                            className="bg-gradient-to-r from-indigo-500 to-emerald-400 h-1.5 rounded-full transition-all duration-500"
                            style={{ width: `${expInfo.percent}%` }}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* SECTION 2: HOW TO ACTIVATE GUIDE ACCORDION */}
        <div className="rounded-2xl border border-border-default bg-bg-card/25 backdrop-blur-md overflow-hidden">
          <button
            onClick={() => setShowGuide(!showGuide)}
            className="w-full p-4 sm:p-5 flex items-center justify-between text-left hover:bg-bg-card/40 transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400">
                <Terminal size={18} />
              </div>
              <div>
                <h4 className="text-sm font-bold text-text-primary">{t('guideTitle', { defaultValue: 'Инструкция по активации на вашем сервере' })}</h4>
                <p className="text-xs text-text-secondary">{t('guideSubtitle', { defaultValue: 'Как применить ключ в Docker Compose за 1 минуту' })}</p>
              </div>
            </div>
            <div className="text-text-secondary">
              {showGuide ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
            </div>
          </button>

          {showGuide && (
            <div className="p-5 pt-0 border-t border-border-default/50 space-y-4 text-xs text-text-secondary leading-relaxed">
              <div className="space-y-2 mt-4">
                <p className="font-semibold text-text-primary">{t('step1Title', { defaultValue: '1. Добавьте ключ в конфигурацию Docker:' })}</p>
                <div className="bg-slate-950 p-3 rounded-xl font-mono text-[11px] text-slate-300 border border-slate-800">
                  {t('step1Comment', { defaultValue: '# В файле docker/.env вашего репозитория добавьте:' })}<br />
                  <span className="text-indigo-400">RAGFLOW_LICENSE_KEY</span>="{t('yourKeyPlaceholder', { defaultValue: '<ВАШ_СКОПИРОВАННЫЙ_КЛЮЧ>' })}"
                </div>
              </div>

              <div className="space-y-2">
                <p className="font-semibold text-text-primary">{t('step2Title', { defaultValue: '2. Перезапустите контейнеры приложения:' })}</p>
                <div className="bg-slate-950 p-3 rounded-xl font-mono text-[11px] text-slate-300 border border-slate-800 flex items-center justify-between">
                  <span>docker compose down && docker compose up -d</span>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText('docker compose down && docker compose up -d');
                      message.success(t('commandCopied', { defaultValue: 'Команда скопирована' }));
                    }}
                    className="text-indigo-400 hover:text-indigo-300 p-1 cursor-pointer"
                    title={t('copyCommand', { defaultValue: 'Скопировать команду' })}
                  >
                    <Copy size={13} />
                  </button>
                </div>
              </div>

              <p className="text-[11px] text-slate-400 pt-1">
                {t('guideNote', { defaultValue: 'Ключ проверяется офлайн встроенной криптографической библиотекой. Подключение сервера к интернету для валидации лицензии не требуется.' })}
              </p>
            </div>
          )}
        </div>

        {/* SECTION 3: PURCHASE NEW LICENSE KEY (BALANCED 2-COLUMN GRID) */}
        <div className="space-y-5 pt-2">
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-text-primary flex items-center gap-2">
              <Sparkles className="text-accent-primary" size={20} />
              {t('purchaseTitle', { defaultValue: 'Приобрести новый лицензионный ключ' })}
            </h3>
            <p className="text-xs text-text-secondary">
              {t('purchaseSubtitle', { defaultValue: 'Выберите подходящий период действия. Лицензионный ключ генерируется мгновенно после подтверждения оплаты картой.' })}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
            {/* 6 Months Tier */}
            <div 
              onClick={() => setSelectedMonths(6)}
              className={`rounded-2xl border p-6 flex flex-col justify-between transition-all cursor-pointer relative overflow-hidden ${
                selectedMonths === 6
                  ? 'border-accent-primary bg-accent-primary/10 ring-1 ring-accent-primary/50 shadow-xl shadow-accent-primary/5'
                  : 'border-border-default bg-bg-card/30 hover:border-accent-primary/40 hover:bg-bg-card/50'
              }`}
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-extrabold uppercase tracking-wider text-indigo-400 bg-indigo-500/15 px-3 py-1 rounded-full border border-indigo-500/20">
                    {t('tier6Title', { defaultValue: 'Пилот / 6 Месяцев' })}
                  </span>
                  <span className="text-xs text-text-secondary font-medium">{t('oneServer', { defaultValue: '1 сервер' })}</span>
                </div>

                <div>
                  <div className="text-3xl font-black text-text-primary">
                    {fmtUZS(pricing.price_6_months)}
                  </div>
                  <p className="text-xs text-text-secondary mt-1">{t('oneTime6Mo', { defaultValue: 'Единоразовая оплата на полгода' })}</p>
                </div>

                <hr className="border-border-default/50" />

                <ul className="space-y-2.5 text-xs text-text-secondary">
                  <li className="flex items-center gap-2 text-slate-300">
                    <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
                    {t('tier6Feat1', { defaultValue: 'Безлимитное количество документов и баз знаний' })}
                  </li>
                  <li className="flex items-center gap-2 text-slate-300">
                    <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
                    {t('tier6Feat2', { defaultValue: 'Полная автономная работа без интернета (Air-gap)' })}
                  </li>
                  <li className="flex items-center gap-2 text-slate-300">
                    <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
                    {t('tier6Feat3', { defaultValue: 'Развертывание в локальном Docker окружении' })}
                  </li>
                  <li className="flex items-center gap-2 text-slate-300">
                    <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
                    {t('tier6Feat4', { defaultValue: 'Поддержка через тикеты и документацию' })}
                  </li>
                </ul>
              </div>

              <div className="pt-6">
                <Button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleProceedToCheckout(6);
                  }}
                  variant={selectedMonths === 6 ? 'default' : 'outline'}
                  className={`w-full py-5 rounded-xl font-bold text-sm gap-2 transition-all cursor-pointer ${
                    selectedMonths === 6
                      ? 'bg-accent-primary hover:bg-accent-primary/90 text-white shadow-lg shadow-accent-primary/20'
                      : 'border-border-default hover:bg-accent-primary hover:text-white'
                  }`}
                >
                  {t('buy6Months', { defaultValue: 'Купить на 6 месяцев' })} <ArrowRight size={15} />
                </Button>
              </div>
            </div>

            {/* 12 Months Tier (Featured / Best Value) */}
            <div 
              onClick={() => setSelectedMonths(12)}
              className={`rounded-2xl border p-6 flex flex-col justify-between transition-all cursor-pointer relative overflow-hidden ${
                selectedMonths === 12
                  ? 'border-accent-primary bg-accent-primary/10 ring-2 ring-accent-primary/60 shadow-xl shadow-accent-primary/10'
                  : 'border-border-default bg-bg-card/30 hover:border-accent-primary/40 hover:bg-bg-card/50'
              }`}
            >
              {/* Best Value Ribbon */}
              <div className="absolute top-0 right-0">
                <div className="bg-gradient-to-l from-emerald-500 to-teal-500 text-slate-950 font-extrabold text-[10px] uppercase tracking-wider py-1 px-4 rounded-bl-xl shadow-md flex items-center gap-1">
                  <Sparkles size={11} /> {t('ribbon2MonthsFree', { defaultValue: '2 Месяца бесплатно' })}
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between gap-2 pr-24 sm:pr-28">
                  <span className="text-xs sm:text-sm font-extrabold uppercase tracking-wider text-emerald-400 bg-emerald-500/15 px-3 py-1 rounded-full border border-emerald-500/20">
                    {t('tier12Title', { defaultValue: 'Годовая / 12 Месяцев' })}
                  </span>
                  <span className="text-xs text-emerald-400 font-semibold shrink-0 hidden sm:inline">{t('bestPrice', { defaultValue: 'Лучшая цена' })}</span>
                </div>

                <div>
                  <div className="text-3xl font-black text-text-primary">
                    {fmtUZS(pricing.price_12_months)}
                  </div>
                  <p className="text-xs text-text-secondary mt-1">
                    {t('savings100k', { defaultValue: 'Экономия 100,000 UZS по сравнению с полугодовой' })}
                  </p>
                </div>

                <hr className="border-border-default/50" />

                <ul className="space-y-2.5 text-xs text-text-secondary">
                  <li className="flex items-center gap-2 text-slate-200 font-medium">
                    <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
                    {t('tier12Feat1', { defaultValue: 'Все преимущества тарифа на 6 месяцев' })}
                  </li>
                  <li className="flex items-center gap-2 text-slate-200 font-medium">
                    <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
                    {t('tier12Feat2', { defaultValue: 'Приоритетная линия технической поддержки' })}
                  </li>
                  <li className="flex items-center gap-2 text-slate-200 font-medium">
                    <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
                    {t('tier12Feat3', { defaultValue: 'Гарантия совместимости будущих обновлений' })}
                  </li>
                  <li className="flex items-center gap-2 text-slate-200 font-medium">
                    <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
                    {t('tier12Feat4', { defaultValue: 'Поддержка промышленных кластеров Kubernetes' })}
                  </li>
                </ul>
              </div>

              <div className="pt-6">
                <Button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleProceedToCheckout(12);
                  }}
                  className="w-full py-5 rounded-xl font-bold text-sm bg-accent-primary hover:bg-accent-primary/90 text-white gap-2 shadow-lg shadow-accent-primary/25 cursor-pointer"
                >
                  {t('buy12Months', { defaultValue: 'Купить на 12 месяцев (Выгодно)' })} <ArrowRight size={15} />
                </Button>
              </div>
            </div>
          </div>
        </div>

      </div>
    </ProfileSettingWrapperCard>
  );
};

export default LicensePurchasePage;
