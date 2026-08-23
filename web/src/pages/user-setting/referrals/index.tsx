import Spotlight from '@/components/spotlight';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import message from '@/components/ui/message';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import api from '@/utils/api';
import { formatDate } from '@/utils/date';
import request from '@/utils/request';
import adService, { AttributionStatsData } from '@/services/ad-service';
import {
  Activity,
  Check,
  Copy,
  Cpu,
  Gift,
  HardDrive,
  MousePointerClick,
  Percent,
  Share2,
  ShieldAlert,
  Sparkles,
  Users,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ProfileSettingWrapperCard } from '../components/user-setting-header';

interface ReferralItem {
  email: string;
  nickname: string;
  created_at: string | null;
}

const ReferralPage = () => {
  const { t } = useTranslation();
  const { data: userInfo } = useFetchUserInfo();
  const [referrals, setReferrals] = useState<ReferralItem[]>([]);
  const [attributionStats, setAttributionStats] = useState<AttributionStatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [copiedUtm, setCopiedUtm] = useState(false);

  const referralLink = userInfo?.id
    ? `${window.location.protocol}//${window.location.host}/login?ref=${userInfo.id}`
    : '';

  const utmLink = attributionStats?.utm_link || (userInfo?.id
    ? `${window.location.protocol}//${window.location.host}/?ref=${userInfo.id}&utm_source=swipies_ai&utm_medium=chat_watermark&utm_campaign=share_attribution`
    : '');

  useEffect(() => {
    const loadReferrals = async () => {
      try {
        setLoading(true);
        const [refRes, attrRes] = await Promise.allSettled([
          request.get(api.referrals),
          adService.getAttributionStats(),
        ]);

        if (refRes.status === 'fulfilled' && refRes.value.data?.code === 0) {
          setReferrals(refRes.value.data.data || []);
        }

        if (attrRes.status === 'fulfilled' && attrRes.value.data?.code === 0) {
          setAttributionStats(attrRes.value.data.data || null);
        }
      } catch (err) {
        console.error('Failed to load referrals or attribution stats', err);
      } finally {
        setLoading(false);
      }
    };
    loadReferrals();
  }, []);

  const handleCopy = () => {
    if (!referralLink) return;
    navigator.clipboard.writeText(referralLink);
    setCopied(true);
    message.success(t('setting.copied'));
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopyUtm = () => {
    if (!utmLink) return;
    navigator.clipboard.writeText(utmLink);
    setCopiedUtm(true);
    message.success(t('setting.copied'));
    setTimeout(() => setCopiedUtm(false), 2000);
  };

  const totalCount = referrals.length;
  const totalVisits = attributionStats?.total_visits || 0;
  const uniqueVisitors = attributionStats?.unique_visitors || 0;
  const conversionRate = attributionStats?.conversion_rate || (totalVisits > 0 ? ((totalCount / totalVisits) * 100).toFixed(1) : '0.0');
  const storageBonus = totalCount * 1.0; // 1 GB per user
  const agentsBonus = totalCount * 5; // 5 agents per user

  return (
    <ProfileSettingWrapperCard
      header={
        <header className="flex flex-col gap-1">
          <h2 className="text-2xl font-bold tracking-tight text-text-primary flex items-center gap-2">
            <Gift className="text-accent-primary animate-pulse" size={24} />
            {t('setting.referralProgram')}
          </h2>
          <p className="text-text-secondary text-sm">
            {t('setting.referralDescription')}
          </p>
        </header>
      }
    >
      <Spotlight />

      <div className="h-full overflow-x-hidden overflow-y-auto space-y-6 pb-8 pr-1">
        {/* Referral & AI Watermark Attribution Links Card */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Direct Invite Link */}
          <Card className="border border-border-default bg-bg-component/40 backdrop-blur-md overflow-hidden relative">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold flex items-center gap-2 text-text-primary">
                <Share2 size={16} className="text-accent-primary" />
                {t('setting.yourReferralLink')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex gap-2">
                <div className="flex-1 bg-bg-input/60 border border-border-default rounded-lg px-3 py-2 text-xs text-text-primary select-all font-mono truncate flex items-center min-h-[38px]">
                  {referralLink || 'Loading link...'}
                </div>
                <Button
                  type="button"
                  size="sm"
                  className="bg-accent-primary hover:bg-accent-primary/95 text-white flex items-center justify-center gap-1.5 px-3 shrink-0"
                  onClick={handleCopy}
                  disabled={!referralLink}
                >
                  {copied ? <Check size={14} /> : <Copy size={14} />}
                  {t('copy')}
                </Button>
              </div>
              <p className="text-[11px] text-text-tertiary">
                Прямая ссылка для отправки друзьям и коллегам для регистрации.
              </p>
            </CardContent>
          </Card>

          {/* AI Chat Watermark UTM Link */}
          <Card className="border border-border-default bg-bg-component/40 backdrop-blur-md overflow-hidden relative">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold flex items-center gap-2 text-text-primary">
                <Sparkles size={16} className="text-blue-500" />
                <span>AI Chat Watermark (UTM Ссылка)</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex gap-2">
                <div className="flex-1 bg-bg-input/60 border border-border-default rounded-lg px-3 py-2 text-xs text-text-primary select-all font-mono truncate flex items-center min-h-[38px]">
                  {utmLink || 'Loading UTM link...'}
                </div>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="border-border-default hover:bg-bg-component/60 flex items-center justify-center gap-1.5 px-3 shrink-0 text-text-primary"
                  onClick={handleCopyUtm}
                  disabled={!utmLink}
                >
                  {copiedUtm ? <Check size={14} /> : <Copy size={14} />}
                  {t('copy')}
                </Button>
              </div>
              <p className="text-[11px] text-text-tertiary">
                Встраивается в футер ответов AI на Free тарифе для автоматического привлечения рефералов.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* 4 Stats Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Total Visits from AI */}
          <Card className="border border-border-default bg-bg-component/25 backdrop-blur-sm transition-all duration-300 hover:border-accent-primary/45">
            <CardContent className="p-4 flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-[11px] font-medium text-text-secondary uppercase tracking-wider">
                  Переходы по AI ссылкам
                </p>
                <p className="text-2xl font-extrabold text-text-primary tracking-tight">
                  {totalVisits}
                </p>
                <p className="text-[10px] text-text-tertiary">
                  {uniqueVisitors} уникальных посетителей
                </p>
              </div>
              <div className="p-2.5 bg-blue-500/10 rounded-xl text-blue-500">
                <MousePointerClick size={22} />
              </div>
            </CardContent>
          </Card>

          {/* Card 2: Total Registered Referrals */}
          <Card className="border border-border-default bg-bg-component/25 backdrop-blur-sm transition-all duration-300 hover:border-accent-primary/45">
            <CardContent className="p-4 flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-[11px] font-medium text-text-secondary uppercase tracking-wider">
                  {t('setting.totalInvited')}
                </p>
                <p className="text-2xl font-extrabold text-text-primary tracking-tight">
                  {totalCount}
                </p>
                <p className="text-[10px] text-text-tertiary">
                  Конверсия: {conversionRate}%
                </p>
              </div>
              <div className="p-2.5 bg-accent-primary/10 rounded-xl text-accent-primary">
                <Users size={22} />
              </div>
            </CardContent>
          </Card>

          {/* Card 3: Storage Bonus */}
          <Card className="border border-border-default bg-bg-component/25 backdrop-blur-sm transition-all duration-300 hover:border-accent-primary/45">
            <CardContent className="p-4 flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-[11px] font-medium text-text-secondary uppercase tracking-wider">
                  {t('setting.storageBonus')}
                </p>
                <p className="text-2xl font-extrabold text-emerald-500 tracking-tight">
                  +{storageBonus.toFixed(1)} GB
                </p>
                <p className="text-[10px] text-text-tertiary">
                  +1.0 GB за каждого пользователя
                </p>
              </div>
              <div className="p-2.5 bg-emerald-500/10 rounded-xl text-emerald-500">
                <HardDrive size={22} />
              </div>
            </CardContent>
          </Card>

          {/* Card 4: Agents Bonus */}
          <Card className="border border-border-default bg-bg-component/25 backdrop-blur-sm transition-all duration-300 hover:border-accent-primary/45">
            <CardContent className="p-4 flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-[11px] font-medium text-text-secondary uppercase tracking-wider">
                  {t('setting.agentsBonus')}
                </p>
                <p className="text-2xl font-extrabold text-indigo-500 tracking-tight">
                  +{agentsBonus}
                </p>
                <p className="text-[10px] text-text-tertiary">
                  +5 агентов за пользователя
                </p>
              </div>
              <div className="p-2.5 bg-indigo-500/10 rounded-xl text-indigo-500">
                <Cpu size={22} />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Invited Referrals Table */}
        <Card className="border border-border-default bg-bg-component/20 backdrop-blur-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">
              {t('setting.referrals')}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="rounded-b-lg overflow-hidden border-t border-border-default">
              <Table>
                <TableHeader className="bg-bg-title/50">
                  <TableRow>
                    <TableHead className="h-11 px-6 text-xs font-semibold text-text-secondary uppercase tracking-wider">
                      {t('common.name')}
                    </TableHead>
                    <TableHead className="h-11 px-6 text-xs font-semibold text-text-secondary uppercase tracking-wider">
                      {t('setting.email')}
                    </TableHead>
                    <TableHead className="h-11 px-6 text-xs font-semibold text-text-secondary uppercase tracking-wider">
                      {t('setting.regDate')}
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody className="bg-transparent">
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={3} className="h-32 text-center">
                        <div className="flex flex-col items-center justify-center gap-2">
                          <div className="h-6 w-6 animate-spin rounded-full border-2 border-solid border-accent-primary border-r-transparent align-[-0.125em]"></div>
                          <span className="text-xs text-text-secondary">
                            Loading...
                          </span>
                        </div>
                      </TableCell>
                    </TableRow>
                  ) : referrals.length > 0 ? (
                    referrals.map((record, index) => (
                      <TableRow
                        key={index}
                        className="hover:bg-bg-component/30 border-b border-border-default last:border-none transition-colors duration-150"
                      >
                        <TableCell className="px-6 py-3.5 text-sm font-medium text-text-primary">
                          {record.nickname || 'Invited User'}
                        </TableCell>
                        <TableCell className="px-6 py-3.5 text-sm text-text-secondary font-mono">
                          {record.email}
                        </TableCell>
                        <TableCell className="px-6 py-3.5 text-sm text-text-secondary">
                          {record.created_at
                            ? formatDate(record.created_at)
                            : '-'}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={3} className="h-32 text-center">
                        <div className="flex flex-col items-center justify-center gap-2 py-4">
                          <ShieldAlert
                            className="text-text-secondary/40"
                            size={32}
                          />
                          <span className="text-sm text-text-secondary font-medium">
                            {t('setting.noReferralsYet')}
                          </span>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </ProfileSettingWrapperCard>
  );
};

export default ReferralPage;
