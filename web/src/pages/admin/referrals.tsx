import { useQuery } from '@tanstack/react-query';
import {
  Cpu,
  Database,
  Gift,
  LucideLoader2,
  LucideSearch,
  Users,
} from 'lucide-react';
import { useState } from 'react';

import Spotlight from '@/components/spotlight';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { SearchInput } from '@/components/ui/input';
import { RAGFlowPagination } from '@/components/ui/ragflow-pagination';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { getReferrals } from '@/services/admin-service';

export default function AdminReferrals() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);

  const { data: res, isLoading } = useQuery({
    queryKey: ['admin/listReferrals', page, pageSize, search],
    queryFn: async () => {
      const response = await getReferrals({ page, size: pageSize, search });
      return response.data.data;
    },
  });

  const stats = res?.stats || {
    total_referrals: 0,
    active_referrers: 0,
    total_storage_bonus_gb: 0,
    total_agents_bonus: 0,
    reward_storage_gb: 1.0,
    reward_agents_limit: 5,
  };

  const records = res?.records || [];
  const total = res?.total || 0;

  if (isLoading && !res) {
    return (
      <div className="flex items-center justify-center h-full w-full">
        <LucideLoader2 className="animate-spin size-8 text-accent-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 h-full overflow-hidden">
      {/* Title */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Referral Program Activity
          </h1>
          <p className="text-sm text-text-secondary">
            Monitor referral system conversions, rewards activity, and global
            settings.
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="border border-border-button dark:bg-bg-card/30">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-text-secondary">
              Total Referrals
            </CardTitle>
            <Users className="h-4 w-4 text-accent-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_referrals}</div>
            <p className="text-xs text-text-secondary mt-1">
              Registered users from invite links
            </p>
          </CardContent>
        </Card>

        <Card className="border border-border-button dark:bg-bg-card/30">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-text-secondary">
              Active Referrers
            </CardTitle>
            <Gift className="h-4 w-4 text-accent-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.active_referrers}</div>
            <p className="text-xs text-text-secondary mt-1">
              Unique users who invited others
            </p>
          </CardContent>
        </Card>

        <Card className="border border-border-button dark:bg-bg-card/30">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-text-secondary">
              Storage Bonus Given
            </CardTitle>
            <Database className="h-4 w-4 text-accent-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.total_storage_bonus_gb} GB
            </div>
            <p className="text-xs text-text-secondary mt-1">
              +{stats.reward_storage_gb} GB per referral conversion
            </p>
          </CardContent>
        </Card>

        <Card className="border border-border-button dark:bg-bg-card/30">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-text-secondary">
              Agents Limit Bonus
            </CardTitle>
            <Cpu className="h-4 w-4 text-accent-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              +{stats.total_agents_bonus} Apps
            </div>
            <p className="text-xs text-text-secondary mt-1">
              +{stats.reward_agents_limit} apps per referral conversion
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Table Card */}
      <Card className="!shadow-none relative flex-1 border-0.5 border-border-button bg-transparent rounded-xl overflow-hidden flex flex-col">
        <Spotlight />
        <CardHeader className="space-y-0 flex flex-row justify-between items-center p-4 border-b border-border-button">
          <CardTitle className="text-base font-semibold">
            User Conversions List
          </CardTitle>
          <SearchInput
            className="w-64 h-9 bg-bg-input border-border-button"
            placeholder="Search inviter or invitee..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            prefix={<LucideSearch className="size-3.5" />}
          />
        </CardHeader>

        <div className="flex-1 overflow-hidden">
          <ScrollArea className="h-full">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Invitee (Referred User)</TableHead>
                    <TableHead>Invitee Nickname</TableHead>
                    <TableHead>Inviter (Referrer)</TableHead>
                    <TableHead>Inviter Nickname</TableHead>
                    <TableHead>Conversion Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {records.length > 0 ? (
                    records.map((r: any) => (
                      <TableRow key={r.invitee_id} className="group">
                        <TableCell className="font-medium">
                          {r.invitee_email}
                        </TableCell>
                        <TableCell>{r.invitee_nickname || '-'}</TableCell>
                        <TableCell>{r.inviter_email}</TableCell>
                        <TableCell>{r.inviter_nickname || '-'}</TableCell>
                        <TableCell>
                          {r.invitee_create_date
                            ? new Date(r.invitee_create_date).toLocaleString()
                            : '-'}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell
                        colSpan={5}
                        className="h-24 text-center text-text-secondary"
                      >
                        No referral conversions found.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </ScrollArea>
        </div>

        <div className="p-4 border-t border-border-button flex items-center justify-end">
          <RAGFlowPagination
            total={total}
            current={page}
            pageSize={pageSize}
            onChange={(p, size) => {
              setPage(p);
              setPageSize(size);
            }}
          />
        </div>
      </Card>
    </div>
  );
}
