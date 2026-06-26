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
import {
  Check,
  Copy,
  Cpu,
  Gift,
  HardDrive,
  ShieldAlert,
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
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  const referralLink = userInfo?.id
    ? `${window.location.protocol}//${window.location.host}/login?ref=${userInfo.id}`
    : '';

  useEffect(() => {
    const loadReferrals = async () => {
      try {
        setLoading(true);
        const { data } = await request.get(api.referrals);
        if (data && data.code === 0) {
          setReferrals(data.data || []);
        }
      } catch (err) {
        console.error('Failed to load referrals', err);
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

  const totalCount = referrals.length;
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
        {/* Referral Link & Explanations Card */}
        <Card className="border border-border-default bg-bg-component/40 backdrop-blur-md overflow-hidden relative">
          <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
            <Gift size={120} />
          </div>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold">
              {t('setting.yourReferralLink')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="flex-1 bg-bg-input/60 border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary select-all font-mono break-all flex items-center justify-start min-h-[40px]">
                {referralLink || 'Loading link...'}
              </div>
              <Button
                type="button"
                className="bg-accent-primary hover:bg-accent-primary/95 text-white flex items-center justify-center gap-2 px-4 py-2 shrink-0 transition-all duration-200"
                onClick={handleCopy}
                disabled={!referralLink}
              >
                {copied ? <Check size={16} /> : <Copy size={16} />}
                {t('copy')}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Stats Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Card 1: Total Invited */}
          <Card className="border border-border-default bg-bg-component/25 backdrop-blur-sm transition-all duration-300 hover:border-accent-primary/45">
            <CardContent className="p-5 flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs font-medium text-text-secondary uppercase tracking-wider">
                  {t('setting.totalInvited')}
                </p>
                <p className="text-3xl font-extrabold text-text-primary tracking-tight">
                  {totalCount}
                </p>
              </div>
              <div className="p-3 bg-accent-primary/10 rounded-xl text-accent-primary">
                <Users size={24} />
              </div>
            </CardContent>
          </Card>

          {/* Card 2: Storage Bonus */}
          <Card className="border border-border-default bg-bg-component/25 backdrop-blur-sm transition-all duration-300 hover:border-accent-primary/45">
            <CardContent className="p-5 flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs font-medium text-text-secondary uppercase tracking-wider">
                  {t('setting.storageBonus')}
                </p>
                <p className="text-3xl font-extrabold text-accent-primary tracking-tight">
                  +{storageBonus.toFixed(1)} GB
                </p>
              </div>
              <div className="p-3 bg-accent-primary/10 rounded-xl text-accent-primary">
                <HardDrive size={24} />
              </div>
            </CardContent>
          </Card>

          {/* Card 3: Agents Bonus */}
          <Card className="border border-border-default bg-bg-component/25 backdrop-blur-sm transition-all duration-300 hover:border-accent-primary/45">
            <CardContent className="p-5 flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs font-medium text-text-secondary uppercase tracking-wider">
                  {t('setting.agentsBonus')}
                </p>
                <p className="text-3xl font-extrabold text-accent-primary tracking-tight">
                  +{agentsBonus}
                </p>
              </div>
              <div className="p-3 bg-accent-primary/10 rounded-xl text-accent-primary">
                <Cpu size={24} />
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
