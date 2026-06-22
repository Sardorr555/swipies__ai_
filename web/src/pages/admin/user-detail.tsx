import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router';

import { LucideArrowLeft, LucideDot } from 'lucide-react';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';

import { Routes } from '@/routes';

import { RAGFlowAvatar } from '@/components/ragflow-avatar';
import Spotlight from '@/components/spotlight';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import message from '@/components/ui/message';
import { RAGFlowPagination } from '@/components/ui/ragflow-pagination';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Table, TableBody, TableCell, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import {
  getUserDetails,
  listUserAgents,
  listUserDatasets,
  updateUserDetails,
  updateUserSubscription,
} from '@/services/admin-service';

import { TableEmpty } from '@/components/table-skeleton';
import EnterpriseFeature from './components/enterprise-feature';
import { parseBooleanish } from './utils';

const ASSET_NAMES = ['dataset', 'flow'];

const datasetColumnHelper =
  createColumnHelper<AdminService.ListUserDatasetItem>();
const agentColumnHelper = createColumnHelper<AdminService.ListUserAgentItem>();

function UserDatasetTable(props: {
  data?: AdminService.ListUserDatasetItem[];
}) {
  const { t } = useTranslation();

  const columnDefs = useMemo(
    () => [
      datasetColumnHelper.accessor('name', {
        header: t('admin.name'),
        cell: ({ row, cell }) => (
          <div className="flex items-center gap-2">
            <RAGFlowAvatar
              avatar={row.original.avatar}
              name={cell.getValue()}
            />
            <span>{cell.getValue()}</span>
          </div>
        ),
      }),
      // #region
      /*
      datasetColumnHelper.accessor('name', {
        header: t('admin.name'),
        enableSorting: false,
      }),
      datasetColumnHelper.accessor('status', {
        header: t('admin.status'),
        cell: ({ cell }) => {
          return (
            <Badge
              variant={parseBooleanish(cell.getValue()) ? 'success' : 'destructive'}
              className="pl-[.35em]"
            >
              <LucideDot className="size-[1em] stroke-[8] mr-1" />
              {t(
                parseBooleanish(cell.getValue())
                  ? 'admin.active'
                  : 'admin.inactive',
              )}"
            </Badge>
          );
        },
        enableSorting: false,
      }),
      datasetColumnHelper.accessor('chunk_num', {
        header: t('admin.chunkNum'),
      }),
      datasetColumnHelper.accessor('doc_num', {
        header: t('admin.docNum'),
      }),
      datasetColumnHelper.accessor('token_num', {
        header: t('admin.tokenNum'),
      }),
      datasetColumnHelper.accessor('language', {
        header: t('admin.language'),
        enableSorting: false,
      }),
      datasetColumnHelper.accessor('create_date', {
        header: t('admin.createDate'),
      }),
      datasetColumnHelper.accessor('update_date', {
        header: t('admin.updateDate'),
      }),
      datasetColumnHelper.accessor('permission', {
        header: t('admin.permission'),
        enableSorting: false,
      }),
      */
      // #endregion
    ],
    [t],
  );

  const table = useReactTable({
    data: props.data ?? [],
    columns: columnDefs,

    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),

    enableSorting: false,
  });

  return (
    <section className="space-y-4">
      <Table>
        {/* <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>
                  {header.isPlaceholder ? null : header.column.getCanSort() ? (
                    <Button
                      variant="ghost"
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                      {getSortIcon(header.column.getIsSorted())}
                    </Button>
                  ) : (
                    flexRender(
                      header.column.columnDef.header,
                      header.getContext(),
                    )
                  )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader> */}

        <TableBody>
          {table.getRowModel().rows?.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableEmpty columnsLength={columnDefs.length} />
          )}
        </TableBody>
      </Table>

      <RAGFlowPagination
        total={props.data?.length}
        current={table.getState().pagination.pageIndex + 1}
        pageSize={table.getState().pagination.pageSize}
        onChange={(page, pageSize) => {
          table.setPagination({
            pageIndex: page - 1,
            pageSize,
          });
        }}
      />
    </section>
  );
}

function UserAgentTable(props: { data?: AdminService.ListUserAgentItem[] }) {
  const { t } = useTranslation();

  const columnDefs = useMemo(
    () => [
      agentColumnHelper.accessor('title', {
        header: t('admin.agentTitle'),
        cell: ({ row, cell }) => (
          <div className="flex items-center gap-2">
            <RAGFlowAvatar
              avatar={row.original.avatar}
              name={cell.getValue()}
            />
            <span>{cell.getValue()}</span>
          </div>
        ),
      }),
      // #region
      /*
      agentColumnHelper.accessor('title', {
        header: t('admin.agentTitle'),
      }),
      agentColumnHelper.accessor('permission', {
        header: t('admin.permission'),
      }),
      agentColumnHelper.accessor('canvas_category', {
        header: t('admin.canvasCategory'),
      }),
      */
      // #endregion
    ],
    [t],
  );

  const table = useReactTable({
    data: props.data ?? [],
    columns: columnDefs,

    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),

    enableSorting: false,
  });

  return (
    <section className="space-y-4">
      <Table>
        {/* <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>
                  {header.isPlaceholder ? null : (
                    <>
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                    </>
                  )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader> */}

        <TableBody>
          {table.getRowModel().rows?.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableEmpty columnsLength={columnDefs.length} />
          )}
        </TableBody>
      </Table>

      <RAGFlowPagination
        total={props.data?.length}
        current={table.getState().pagination.pageIndex + 1}
        pageSize={table.getState().pagination.pageSize}
        onChange={(page, pageSize) => {
          table.setPagination({
            pageIndex: page - 1,
            pageSize,
          });
        }}
      />
    </section>
  );
}

function AdminUserDetail() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { id } = useParams();
  const queryClient = useQueryClient();

  const [planType, setPlanType] = useState<string>('free');
  const [planExpiry, setPlanExpiry] = useState<string>('');
  const [credits, setCredits] = useState<number>(512);
  const [nickname, setNickname] = useState<string>('');
  const [phone, setPhone] = useState<string>('');

  const { data: { detail, datasets, agents } = {} } = useQuery({
    queryKey: ['admin/userDetail', id],
    queryFn: async () => {
      const [userDetails, userDatasets, userAgents] = await Promise.all([
        getUserDetails(id!),
        listUserDatasets(id!),
        listUserAgents(id!),
      ]);

      return {
        detail: userDetails.data.data[0],
        datasets: userDatasets.data.data,
        agents: userAgents.data.data,
      };
    },
    enabled: !!id,
    retry: false,
  });

  useEffect(() => {
    if (detail) {
      setPlanType(detail.plan_type || 'free');
      setPlanExpiry(detail.plan_expiry_date || '');
      setCredits(detail.credit ?? 512);
      setNickname(detail.nickname || '');
      setPhone(detail.phone || '');
    }
  }, [detail]);

  const updateSubscriptionMutation = useMutation({
    mutationFn: (params: {
      plan_type: string;
      plan_expiry_date: string | null;
      credit: number;
    }) => updateUserSubscription(id!, params),
    onSuccess: (res) => {
      if (res.data.code === 0) {
        message.success('Subscription updated successfully!');
      }
      queryClient.invalidateQueries({ queryKey: ['admin/userDetail', id] });
    },
  });

  const updateProfileMutation = useMutation({
    mutationFn: (params: { nickname: string; phone: string }) =>
      updateUserDetails(id!, params),
    onSuccess: (res) => {
      if (res.data.code === 0) {
        message.success('Profile details updated successfully!');
      }
      queryClient.invalidateQueries({ queryKey: ['admin/userDetail', id] });
    },
  });

  return (
    <section className="px-10 py-5 size-full flex flex-col">
      <nav className="mb-5">
        <Button
          variant="outline"
          className="h-10 px-3 dark:bg-bg-input dark:border-border-button"
          onClick={() => navigate(`${Routes.AdminUserManagement}`)}
        >
          <LucideArrowLeft />
          <span>{t('admin.back')}</span>
        </Button>
      </nav>

      <Card className="!shadow-none relative h-0 basis-0 grow flex flex-col bg-transparent border-0.5 border-border-button overflow-hidden">
        <Spotlight />

        <CardHeader className="pb-10 border-b-0.5 dark:border-border-button space-y-8">
          <section className="flex items-center gap-4 text-base">
            <RAGFlowAvatar
              avatar={detail?.avatar}
              name={detail?.email}
              isPerson
            />

            <span>{detail?.email}</span>

            <Badge
              variant={
                parseBooleanish(detail?.is_active) ? 'success' : 'destructive'
              }
              className="pl-[.5em]"
            >
              <LucideDot className="size-[1em] stroke-[8] mr-1" />
              {t(
                parseBooleanish(detail?.is_active)
                  ? 'admin.active'
                  : 'admin.inactive',
              )}
            </Badge>

            <EnterpriseFeature>
              {() =>
                detail?.role && (
                  <Badge variant="secondary">{detail?.role}</Badge>
                )
              }
            </EnterpriseFeature>
          </section>

          <section className="flex items-start px-14 space-x-14">
            <div>
              <div className="text-sm text-text-secondary mb-2">
                {t('admin.lastLoginTime')}
              </div>
              <div>{detail?.last_login_time}</div>
            </div>

            <div>
              <div className="text-sm text-text-secondary mb-2">
                {t('admin.createTime')}
              </div>
              <div>{detail?.create_date}</div>
            </div>

            <div>
              <div className="text-sm text-text-secondary mb-2">
                {t('admin.lastUpdateTime')}
              </div>
              <div>{detail?.update_date}</div>
            </div>

            <div>
              <div className="text-sm text-text-secondary mb-2">
                {t('admin.language')}
              </div>
              <div>{detail?.language}</div>
            </div>

            <div>
              <div className="text-sm text-text-secondary mb-2">
                {t('admin.isAnonymous')}
              </div>
              <div>{t(detail?.is_anonymous ? 'admin.yes' : 'admin.no')}</div>
            </div>

            <div>
              <div className="text-sm text-text-secondary mb-2">
                {t('admin.isSuperuser')}
              </div>
              <div>{t(detail?.is_superuser ? 'admin.yes' : 'admin.no')}</div>
            </div>

            <div>
              <div className="text-sm text-text-secondary mb-2">Nickname</div>
              <div className="font-semibold text-accent-primary">
                {detail?.nickname || 'N/A'}
              </div>
            </div>

            <div>
              <div className="text-sm text-text-secondary mb-2">
                Phone Number
              </div>
              <div className="font-semibold">{detail?.phone || 'N/A'}</div>
            </div>

            <div className="border-l pl-8 dark:border-border-button">
              <div className="text-sm text-text-secondary mb-2">
                Current Plan
              </div>
              <div className="capitalize font-bold text-primary">
                {detail?.plan_type || 'free'}
              </div>
            </div>

            <div>
              <div className="text-sm text-text-secondary mb-2">Credits</div>
              <div className="font-semibold">{detail?.credit ?? 512}</div>
            </div>

            <div>
              <div className="text-sm text-text-secondary mb-2">
                Expiry Date
              </div>
              <div className="text-sm text-text-secondary">
                {detail?.plan_expiry_date
                  ? detail.plan_expiry_date
                  : 'Unlimited'}
              </div>
            </div>
          </section>

          <div className="border-t border-dashed dark:border-border-button pt-6 px-14 space-y-4">
            <h3 className="text-sm font-semibold text-text-primary">
              Profile Management
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-end">
              <div className="space-y-2">
                <label className="text-xs text-text-secondary">Nickname</label>
                <Input
                  type="text"
                  className="bg-bg-input border-border-button"
                  placeholder="Enter nickname"
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs text-text-secondary">
                  Phone Number
                </label>
                <Input
                  type="text"
                  className="bg-bg-input border-border-button"
                  placeholder="Enter phone number"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </div>

              <div className="flex gap-2">
                <Button
                  className="w-full h-10"
                  disabled={updateProfileMutation.isPending}
                  onClick={() => {
                    updateProfileMutation.mutate({
                      nickname,
                      phone,
                    });
                  }}
                >
                  {updateProfileMutation.isPending
                    ? 'Saving...'
                    : 'Save Profile'}
                </Button>
              </div>
            </div>
          </div>

          <div className="border-t border-dashed dark:border-border-button pt-6 px-14 space-y-4">
            <h3 className="text-sm font-semibold text-text-primary">
              Subscription & Plan Management
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-end">
              <div className="space-y-2">
                <label className="text-xs text-text-secondary">
                  Pricing Plan
                </label>
                <Select value={planType} onValueChange={setPlanType}>
                  <SelectTrigger className="w-full bg-bg-input border-border-button">
                    <SelectValue placeholder="Select Plan" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="free">Free (Basic)</SelectItem>
                    <SelectItem value="plus">Plus Plan</SelectItem>
                    <SelectItem value="pro">Pro Plan</SelectItem>
                    <SelectItem value="enterprise">Enterprise Plan</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-xs text-text-secondary">
                  Credits Balance
                </label>
                <Input
                  type="number"
                  className="bg-bg-input border-border-button"
                  value={credits}
                  onChange={(e) => setCredits(parseInt(e.target.value) || 0)}
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs text-text-secondary">
                  Plan Expiry Date (YYYY-MM-DD HH:MM:SS)
                </label>
                <Input
                  type="text"
                  className="bg-bg-input border-border-button"
                  placeholder="Unlimited"
                  value={planExpiry}
                  onChange={(e) => setPlanExpiry(e.target.value)}
                />
              </div>

              <div className="flex gap-2">
                <Button
                  className="w-full h-10"
                  disabled={updateSubscriptionMutation.isPending}
                  onClick={() => {
                    updateSubscriptionMutation.mutate({
                      plan_type: planType,
                      plan_expiry_date: planExpiry || null,
                      credit: credits,
                    });
                  }}
                >
                  {updateSubscriptionMutation.isPending
                    ? 'Saving...'
                    : 'Save Changes'}
                </Button>
              </div>
            </div>

            {/* Quick Presets */}
            <div className="flex flex-wrap gap-2 pt-2">
              <span className="text-xs text-text-secondary self-center mr-2">
                Quick Presets:
              </span>
              <Button
                variant="outline"
                size="sm"
                className="text-xs border-border-button dark:bg-bg-input"
                onClick={() => {
                  setPlanType('plus');
                  setCredits(5000);
                  const expiry = new Date();
                  expiry.setDate(expiry.getDate() + 30);
                  // format as YYYY-MM-DD HH:MM:SS
                  const formatted = expiry
                    .toISOString()
                    .replace('T', ' ')
                    .substring(0, 19);
                  setPlanExpiry(formatted);
                }}
              >
                +1 Month Plus (5k credits)
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-xs border-border-button dark:bg-bg-input"
                onClick={() => {
                  setPlanType('pro');
                  setCredits(10000);
                  const expiry = new Date();
                  expiry.setDate(expiry.getDate() + 30);
                  const formatted = expiry
                    .toISOString()
                    .replace('T', ' ')
                    .substring(0, 19);
                  setPlanExpiry(formatted);
                }}
              >
                +1 Month Pro (10k credits)
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-xs border-border-button dark:bg-bg-input"
                onClick={() => {
                  setPlanType('free');
                  setCredits(512);
                  setPlanExpiry('');
                }}
              >
                Reset to Free
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="h-0 basis-0 grow pt-6">
          <Tabs className="h-full flex flex-col" defaultValue="dataset">
            <TabsList className="p-0 mb-2 gap-4 bg-transparent justify-start">
              {ASSET_NAMES.map((name) => (
                <TabsTrigger
                  key={name}
                  className="text-text-secondary border-0.5 border-border-button data-[state=active]:bg-bg-card"
                  value={name}
                >
                  {t(`header.${name}`)}
                </TabsTrigger>
              ))}
            </TabsList>

            <TabsContent value="dataset" className="h-0 basis-0 grow">
              <ScrollArea className="h-full">
                <UserDatasetTable data={datasets} />
              </ScrollArea>
            </TabsContent>

            <TabsContent value="flow" className="h-0 basis-0 grow">
              <ScrollArea className="h-full">
                <UserAgentTable data={agents} />
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </section>
  );
}

export default AdminUserDetail;
