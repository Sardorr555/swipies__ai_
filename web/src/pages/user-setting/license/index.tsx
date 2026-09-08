import { useEffect, useState } from 'react';
import Spotlight from '@/components/spotlight';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import message from '@/components/ui/message';
import request from '@/utils/request';
import { 
  Key, 
  ShieldCheck, 
  Info,
  AlertTriangle,
  LucideExternalLink
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { ProfileSettingWrapperCard } from '../components/user-setting-header';

interface LicenseStatus {
  is_valid: boolean;
  message: string;
  payload?: {
    owner: string;
    expiry: string;
    type: string;
  };
  license_key?: string;
  db_record?: {
    id: string;
    name: string;
    duration_months: number;
    expiry_date: string;
    status: string;
    create_date: string;
  };
}

const LicensePage = () => {
  const { t } = useTranslation();
  const [status, setStatus] = useState<LicenseStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [licenseInput, setLicenseInput] = useState('');
  const [updating, setUpdating] = useState(false);

  const fetchLicenseStatus = async () => {
    setLoading(true);
    try {
      const res = await request.get('/api/v1/system/license');
      if (res?.data?.code === 0) {
        setStatus(res.data.data);
        if (res.data.data?.license_key) {
          setLicenseInput(res.data.data.license_key);
        }
      }
    } catch (err) {
      console.error(err);
      message.error(t('setting.licenseLoadError', 'Не удалось загрузить данные лицензии.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLicenseStatus();
  }, []);

  const handleActivate = async () => {
    const trimmedKey = licenseInput.trim();
    if (!trimmedKey) {
      message.error(t('setting.licenseEmptyError', 'Ключ лицензии не может быть пустым.'));
      return;
    }
    setUpdating(true);
    try {
      const res = await request.post('/api/v1/system/license', {
        data: { license_key: trimmedKey },
      });
      if (res && res.data && res.data.code === 0) {
        message.success(t('setting.licenseActivatedSuccess', 'Лицензия успешно активирована!'));
        setStatus(res.data.data);
      } else {
        message.error(res?.data?.message || t('setting.licenseActivateFailed', 'Не удалось активировать лицензию.'));
      }
    } catch (err: any) {
      const errMsg = err?.response?.data?.message || err?.message || t('setting.licenseActivateError', 'Ошибка при активации лицензии.');
      message.error(errMsg);
    } finally {
      setUpdating(false);
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    try {
      const formattedStr = dateStr.includes(' ') ? dateStr.replace(' ', 'T') : dateStr;
      const date = new Date(formattedStr);
      return date.toLocaleDateString(undefined, { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <ProfileSettingWrapperCard
      header={
        <header className="flex flex-col gap-1 w-full">
          <div className="flex justify-between items-center w-full">
            <h2 className="text-2xl font-bold tracking-tight text-text-primary flex items-center gap-2">
              <Key className="text-accent-primary" size={24} />
              Лицензионные ключи (Self-Hosted)
            </h2>
          </div>
          <p className="text-text-secondary text-sm">
            {t('setting.licenseDesc', 'Активация коммерческой лицензии Swipies AI для локальной установки.')}
          </p>
        </header>
      }
    >
      <Spotlight />

      <div className="h-full overflow-x-hidden overflow-y-auto space-y-6 pb-8 pr-1 mt-6">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-accent-primary"></div>
          </div>
        ) : (
          <div className="grid gap-6">
            {/* License Status Hero */}
            {status?.is_valid ? (
              <Card className="border border-emerald-500/20 bg-emerald-500/5 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-6 opacity-[0.05] pointer-events-none text-emerald-500">
                  <ShieldCheck size={140} />
                </div>
                <CardContent className="p-6 space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-emerald-500/20 rounded-full text-emerald-400 border border-emerald-500/25">
                      <ShieldCheck size={24} />
                    </div>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                        {t('setting.activeLicense', 'Активная лицензия')}
                      </span>
                      <h3 className="text-lg font-bold text-text-primary mt-1">
                        {t('setting.premiumCommercialEdition', 'Премиум коммерческая версия')}
                      </h3>
                    </div>
                  </div>

                  <p className="text-sm text-text-secondary">
                    {status.message || t('setting.validLicenseMsg', 'Система работает под валидной коммерческой лицензией.')}
                  </p>

                  {status.payload && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4 border-t border-emerald-500/10 text-sm">
                      <div className="space-y-1">
                        <span className="text-text-secondary block text-xs">
                          {t('setting.licensedTo', 'Владелец лицензии:')}
                        </span>
                        <span className="font-semibold text-text-primary font-mono">{status.payload.owner}</span>
                      </div>
                      <div className="space-y-1">
                        <span className="text-text-secondary block text-xs">
                          {t('setting.licenseType', 'Тип лицензии / Срок:')}
                        </span>
                        <span className="font-semibold text-text-primary capitalize">
                          {status.payload.type === 'yearly' 
                            ? 'Yearly (12 Months)' 
                            : status.payload.type === '6_months' 
                            ? '6 Months' 
                            : status.payload.type || 'Commercial'}
                        </span>
                      </div>
                      <div className="space-y-1">
                        <span className="text-text-secondary block text-xs">
                          {t('setting.expirationDate', 'Дата окончания:')}
                        </span>
                        <span className="font-semibold text-text-primary">
                          {formatDate(status.payload.expiry)}
                        </span>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ) : (
              <Card className="border border-amber-500/25 bg-amber-500/5 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-6 opacity-[0.05] pointer-events-none text-amber-500">
                  <AlertTriangle size={140} />
                </div>
                <CardContent className="p-6 space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-amber-500/20 rounded-full text-amber-400 border border-amber-500/25">
                      <AlertTriangle size={24} />
                    </div>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded">
                        {t('setting.noActiveLicense', 'Нет активной лицензии')}
                      </span>
                      <h3 className="text-lg font-bold text-text-primary mt-1">
                        {t('setting.freeBaseEdition', 'Бесплатная / Базовая версия')}
                      </h3>
                    </div>
                  </div>
                  <p className="text-sm text-text-secondary leading-relaxed">
                    {t('setting.unlicensedDesc', 'Вы используете базовую версию Swipies. Чтобы разблокировать всех провайдеров моделей, неограниченные агенты и снять ограничения API, активируйте коммерческий лицензионный ключ.')}
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Input & Activation Box */}
            <Card className="border border-border-default bg-bg-component/10">
              <CardContent className="p-6 space-y-4">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-semibold text-text-primary">
                    {status?.is_valid 
                      ? t('setting.updateLicenseKey', 'Обновить / изменить лицензионный ключ:') 
                      : t('setting.enterLicenseKey', 'Введите лицензионный ключ:')}
                  </label>
                  <Textarea
                    placeholder={t('setting.licenseKeyPlaceholder', 'Вставьте ваш ключ лицензии Swipies (base64)...')}
                    value={licenseInput}
                    onChange={(e) => setLicenseInput(e.target.value)}
                    disabled={updating}
                    className="font-mono text-xs"
                    rows={6}
                  />
                </div>

                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pt-2">
                  <div className="flex items-center gap-2 text-xs text-text-secondary">
                    <Info size={16} className="text-accent-primary shrink-0" />
                    <span>{t('setting.needKeyPrompt', 'Нужен ключ? Получите его на платформе: ')}</span>
                    <a
                      href="https://swipies.app"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 font-semibold text-accent-primary hover:underline"
                    >
                      swipies.app <LucideExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                  <Button
                    className="bg-accent-primary hover:bg-accent-primary/95 text-white"
                    onClick={handleActivate}
                    loading={updating}
                  >
                    {status?.is_valid 
                      ? t('setting.updateLicenseBtn', 'Обновить лицензию') 
                      : t('setting.activateLicenseBtn', 'Активировать лицензию')}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </ProfileSettingWrapperCard>
  );
};

export default LicensePage;
