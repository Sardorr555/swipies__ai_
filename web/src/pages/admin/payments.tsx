import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CreditCard,
  TrendingUp,
  DollarSign,
  CheckCircle2,
  AlertCircle,
  Clock,
  ShieldAlert,
  Search,
  RotateCw,
  Copy,
  Check,
  User,
  Filter,
  Layers,
  ChevronLeft,
  ChevronRight,
  FileText,
  ExternalLink,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input, SearchInput } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal/modal';
import message from '@/components/ui/message';
import Spotlight from '@/components/spotlight';
import {
  getPaymentTransactions,
  getPaymentAnalytics,
  reconcilePayment,
} from '@/services/admin-service';

export default function AdminPaymentsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [planFilter, setPlanFilter] = useState<string>('ALL');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Reconcile Modal State
  const [isReconcileModalOpen, setIsReconcileModalOpen] = useState(false);
  const [selectedTx, setSelectedTx] = useState<AdminService.PaymentTransactionItem | null>(null);
  const [reconcileAction, setReconcileAction] = useState<'mark_paid' | 'mark_failed' | 'set_audit_note'>('mark_paid');
  const [reconcilePaidAmount, setReconcilePaidAmount] = useState<number>(0);
  const [reconcileErrorMsg, setReconcileErrorMsg] = useState('');
  const [reconcileAuditNote, setReconcileAuditNote] = useState('');
  const [confirmRevocationChecked, setConfirmRevocationChecked] = useState(false);

  // 1. Fetch Analytics Summary
  const {
    data: analyticsRes,
    isLoading: isAnalyticsLoading,
    refetch: refetchAnalytics,
  } = useQuery({
    queryKey: ['admin/payments/analytics'],
    queryFn: async () => {
      const res = await getPaymentAnalytics();
      return res?.data?.data;
    },
  });

  // 2. Fetch Transactions List
  const {
    data: transactionsRes,
    isLoading: isTransactionsLoading,
    isFetching: isTransactionsFetching,
    refetch: refetchTransactions,
  } = useQuery({
    queryKey: ['admin/payments/transactions', page, pageSize, search, statusFilter, planFilter],
    queryFn: async () => {
      const res = await getPaymentTransactions({
        page,
        size: pageSize,
        search: search.trim() || undefined,
        status: statusFilter === 'ALL' ? undefined : statusFilter,
        plan_type: planFilter === 'ALL' ? undefined : planFilter,
      });
      return res?.data?.data;
    },
  });

  // 3. Reconcile Mutation
  const reconcileMutation = useMutation({
    mutationFn: async (params: {
      transaction_id: string;
      action: 'mark_paid' | 'mark_failed' | 'set_audit_note';
      paid_amount_uzs?: number;
      error_message?: string;
      audit_note: string;
    }) => {
      const res = await reconcilePayment(params);
      return res?.data;
    },
    onSuccess: (data) => {
      if (data?.code === 0) {
        if (data?.data?.warning) {
          message.warning(data.data.warning, 8);
        } else if (data?.data?.downgraded) {
          message.success('Transaction marked FAILED and tenant subscription revoked to FREE.');
        } else {
          message.success('Transaction reconciled successfully');
        }
        setIsReconcileModalOpen(false);
        queryClient.invalidateQueries({ queryKey: ['admin/payments/transactions'] });
        queryClient.invalidateQueries({ queryKey: ['admin/payments/analytics'] });
      } else {
        message.error(data?.message || 'Reconciliation failed');
      }
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.message || err?.message || 'Error reconciling transaction');
    },
  });

  const handleRefreshAll = () => {
    refetchAnalytics();
    refetchTransactions();
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const openReconcileModal = (tx: AdminService.PaymentTransactionItem) => {
    setSelectedTx(tx);
    setReconcilePaidAmount(tx.paid_amount_uzs || tx.expected_amount_uzs || 0);
    setReconcileErrorMsg('');
    setReconcileAuditNote(tx.audit_note || '');
    setConfirmRevocationChecked(false);
    setReconcileAction(tx.status === 'PAID' ? 'set_audit_note' : 'mark_paid');
    setIsReconcileModalOpen(true);
  };

  const handleSubmitReconciliation = () => {
    if (!selectedTx) return;
    if (!reconcileAuditNote.trim()) {
      message.warning('Please enter an audit note explaining this reconciliation.');
      return;
    }
    if (reconcileAction === 'mark_failed' && !confirmRevocationChecked) {
      message.warning('Please check the confirmation box to verify subscription revocation.');
      return;
    }

    reconcileMutation.mutate({
      transaction_id: selectedTx.transaction_id,
      action: reconcileAction,
      paid_amount_uzs: reconcileAction === 'mark_paid' ? Number(reconcilePaidAmount) : undefined,
      error_message: reconcileAction === 'mark_failed' ? reconcileErrorMsg : undefined,
      audit_note: reconcileAuditNote.trim(),
    });
  };

  const formatUzs = (amount: number | null | undefined) => {
    if (amount === null || amount === undefined) return '—';
    return `${Number(amount).toLocaleString()} UZS`;
  };

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      return d.toLocaleString();
    } catch {
      return dateStr;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PAID':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 size={12} /> PAID
          </span>
        );
      case 'PENDING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            <Clock size={12} /> PENDING
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
            <AlertCircle size={12} /> FAILED
          </span>
        );
      case 'REQUIRES_AUDIT':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
            <ShieldAlert size={12} /> REQUIRES AUDIT
          </span>
        );
      case 'EXPIRED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-500 border border-slate-500/20">
            EXPIRED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-500/10 text-gray-500 border border-gray-500/20">
            {status}
          </span>
        );
    }
  };

  const getPlanBadge = (plan: string) => {
    switch (plan.toLowerCase()) {
      case 'pro':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-bold bg-blue-500/10 text-blue-500 border border-blue-500/20">
            PRO
          </span>
        );
      case 'plus':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-bold bg-cyan-500/10 text-cyan-500 border border-cyan-500/20">
            PLUS
          </span>
        );
      case 'license':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-bold bg-amber-500/10 text-amber-500 border border-amber-500/20">
            LICENSE
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-500/10 text-gray-500 border border-gray-500/20">
            {plan.toUpperCase()}
          </span>
        );
    }
  };

  const analytics = analyticsRes || {
    total_revenue_uzs: 0,
    mrr_uzs: 0,
    total_initiated_count: 0,
    paid_transactions_count: 0,
    conversion_rate_pct: 0,
    plan_breakdown: {},
    status_distribution: {},
  };

  const records = transactionsRes?.records || [];
  const totalRecords = transactionsRes?.total || 0;

  return (
    <div className="flex flex-col gap-6 h-full overflow-y-auto pb-10">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary flex items-center gap-2">
            <CreditCard className="text-accent-primary size-7" />
            Payments & Financial Ledger
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Real-time Atmos transaction ledger, revenue analytics, and dispute moderation.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="flex items-center gap-2 border-border-button hover:bg-bg-component/20"
          onClick={handleRefreshAll}
          disabled={isTransactionsFetching || isAnalyticsLoading}
        >
          <RotateCw className={`size-4 ${isTransactionsFetching ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Total Confirmed Revenue */}
        <Card className="border border-border-button dark:bg-bg-card/30 relative overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-text-secondary">
              Total Confirmed Revenue
            </CardTitle>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500">
              <DollarSign className="size-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-text-primary">
              {formatUzs(analytics.total_revenue_uzs)}
            </div>
            <p className="text-xs text-text-secondary mt-1 flex items-center gap-1">
              <span className="font-semibold text-emerald-500">{analytics.paid_transactions_count}</span> confirmed paid orders
            </p>
          </CardContent>
        </Card>

        {/* 30-Day MRR */}
        <Card className="border border-border-button dark:bg-bg-card/30 relative overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-text-secondary">
              30-Day Revenue (MRR)
            </CardTitle>
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500">
              <TrendingUp className="size-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-text-primary">
              {formatUzs(analytics.mrr_uzs)}
            </div>
            <p className="text-xs text-text-secondary mt-1">
              Confirmed in last 30 rolling days
            </p>
          </CardContent>
        </Card>

        {/* Conversion Rate */}
        <Card className="border border-border-button dark:bg-bg-card/30 relative overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-text-secondary">
              Checkout Conversion Rate
            </CardTitle>
            <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-500">
              <CheckCircle2 className="size-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-text-primary">
              {analytics.conversion_rate_pct}%
            </div>
            <p className="text-xs text-text-secondary mt-1">
              {analytics.paid_transactions_count} paid / {analytics.total_initiated_count} initiated checkouts
            </p>
          </CardContent>
        </Card>

        {/* Plans Revenue Breakdown */}
        <Card className="border border-border-button dark:bg-bg-card/30 relative overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-text-secondary">
              Revenue by Tariff
            </CardTitle>
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-500">
              <Layers className="size-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-1 text-xs">
              {Object.entries(analytics.plan_breakdown || {}).length > 0 ? (
                Object.entries(analytics.plan_breakdown).map(([plan, data]: [string, any]) => (
                  <div key={plan} className="flex justify-between items-center">
                    <span className="font-semibold uppercase text-text-secondary">{plan}:</span>
                    <span className="font-medium text-text-primary">
                      {formatUzs(data.total_paid_uzs)} ({data.count})
                    </span>
                  </div>
                ))
              ) : (
                <span className="text-text-secondary italic">No paid subscriptions yet</span>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Ledger Table Card */}
      <Card className="!shadow-none relative border border-border-button bg-transparent rounded-xl overflow-hidden flex flex-col">
        <Spotlight />
        
        {/* Filters and Search Toolbar */}
        <CardHeader className="p-4 border-b border-border-button flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <CardTitle className="text-base font-semibold text-text-primary">
              Transactions Journal
            </CardTitle>
            <CardDescription className="text-xs text-text-secondary mt-0.5">
              Showing {records.length} of {totalRecords} recorded payment events
            </CardDescription>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Status Filter */}
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-text-secondary">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="bg-bg-input border border-border-button text-text-primary text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-accent-primary"
              >
                <option value="ALL">All Statuses</option>
                <option value="PAID">PAID</option>
                <option value="PENDING">PENDING</option>
                <option value="FAILED">FAILED</option>
                <option value="REQUIRES_AUDIT">REQUIRES_AUDIT</option>
                <option value="EXPIRED">EXPIRED</option>
              </select>
            </div>

            {/* Plan Filter */}
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-text-secondary">Plan:</span>
              <select
                value={planFilter}
                onChange={(e) => {
                  setPlanFilter(e.target.value);
                  setPage(1);
                }}
                className="bg-bg-input border border-border-button text-text-primary text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-accent-primary"
              >
                <option value="ALL">All Plans</option>
                <option value="plus">Plus</option>
                <option value="pro">Pro</option>
                <option value="license">Self-Hosted</option>
              </select>
            </div>

            {/* Search Input */}
            <SearchInput
              placeholder="Search by Email or TX ID..."
              className="w-64 h-8 bg-bg-input border-border-button text-xs"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>
        </CardHeader>

        {/* Table Content */}
        <CardContent className="p-0 overflow-x-auto">
          {isTransactionsLoading && records.length === 0 ? (
            <div className="flex items-center justify-center p-12 text-text-secondary">
              <RotateCw className="animate-spin size-6 mr-2 text-accent-primary" />
              Loading payment transactions...
            </div>
          ) : records.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-text-secondary">
              <CreditCard className="size-10 mb-2 opacity-30" />
              <p className="text-sm font-medium">No payment transactions found</p>
              <p className="text-xs text-text-secondary mt-1">
                Try clearing search filters or initiate a checkout test.
              </p>
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border-button bg-bg-component/10 text-xs font-semibold text-text-secondary">
                  <th className="py-3 px-4">Transaction ID</th>
                  <th className="py-3 px-4">User Account</th>
                  <th className="py-3 px-4">Plan & Duration</th>
                  <th className="py-3 px-4">Paid / Expected Amount</th>
                  <th className="py-3 px-4">Method</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-button text-xs">
                {records.map((tx) => (
                  <tr key={tx.id} className="hover:bg-bg-component/10 transition-colors">
                    {/* Transaction ID */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-xs text-text-primary bg-bg-base/60 border border-border-button rounded px-1.5 py-0.5 truncate max-w-[160px]">
                          {tx.transaction_id}
                        </span>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-6 text-text-secondary hover:text-text-primary"
                          onClick={() => handleCopy(tx.transaction_id, tx.id)}
                          title="Copy Transaction ID"
                        >
                          {copiedId === tx.id ? (
                            <Check className="text-emerald-500" size={12} />
                          ) : (
                            <Copy size={12} />
                          )}
                        </Button>
                      </div>
                    </td>

                    {/* User / Email */}
                    <td className="py-3.5 px-4">
                      <div className="font-medium text-text-primary flex items-center gap-1">
                        <User size={12} className="text-text-secondary" />
                        {tx.account_email}
                      </div>
                      <div className="text-[11px] text-text-secondary font-mono mt-0.5">
                        ID: {tx.user_id}
                      </div>
                    </td>

                    {/* Plan & Duration */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1.5">
                        {getPlanBadge(tx.plan_type)}
                        <span className="text-text-secondary font-medium">
                          {tx.duration_months} mo
                        </span>
                      </div>
                    </td>

                    {/* Expected vs Paid */}
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-text-primary">
                        {tx.paid_amount_uzs !== null ? formatUzs(tx.paid_amount_uzs) : '—'}
                      </div>
                      <div className="text-[11px] text-text-secondary mt-0.5">
                        Expected: {formatUzs(tx.expected_amount_uzs)}
                      </div>
                    </td>

                    {/* Method */}
                    <td className="py-3.5 px-4">
                      <span className="capitalize font-mono text-[11px] text-text-secondary">
                        {tx.payment_method.replace('_', ' ')}
                      </span>
                    </td>

                    {/* Status */}
                    <td className="py-3.5 px-4 text-center">
                      {getStatusBadge(tx.status)}
                      {tx.error_message && (
                        <div
                          className="text-[10px] text-rose-500 truncate max-w-[140px] mt-1 mx-auto cursor-help"
                          title={`${tx.error_code || 'ERROR'}: ${tx.error_message}`}
                        >
                          {tx.error_message}
                        </div>
                      )}
                    </td>

                    {/* Date */}
                    <td className="py-3.5 px-4 text-text-secondary text-[11px]">
                      <div>{formatDate(tx.create_date)}</div>
                      {tx.audit_note && (
                        <div
                          className="text-[10px] text-accent-primary truncate max-w-[130px] mt-0.5 cursor-help"
                          title={tx.audit_note}
                        >
                          Note: {tx.audit_note}
                        </div>
                      )}
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs border-border-button hover:bg-accent-primary/10 hover:text-accent-primary"
                        onClick={() => openReconcileModal(tx)}
                      >
                        Reconcile
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>

        {/* Pagination Footer */}
        <div className="flex justify-between items-center p-4 border-t border-border-button text-xs text-text-secondary">
          <span>
            Total: <strong>{totalRecords}</strong> records (Page {page} of{' '}
            {Math.max(1, Math.ceil(totalRecords / pageSize))})
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-7 border-border-button"
              disabled={page === 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft size={14} /> Prev
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 border-border-button"
              disabled={page * pageSize >= totalRecords}
              onClick={() => setPage((p) => p + 1)}
            >
              Next <ChevronRight size={14} />
            </Button>
          </div>
        </div>
      </Card>

      {/* MANUAL RECONCILIATION MODAL */}
      <Modal
        title={`Reconcile Transaction #${selectedTx?.transaction_id || ''}`}
        open={isReconcileModalOpen}
        showfooter={false}
        className="max-w-[500px]"
        onOpenChange={(open) => {
          if (!open) setIsReconcileModalOpen(false);
        }}
      >
        {selectedTx && (
          <div className="mt-4 space-y-4 text-xs">
            {/* Summary Box */}
            <div className="p-3 bg-bg-component/20 border border-border-button rounded-lg space-y-1.5">
              <div className="flex justify-between">
                <span className="text-text-secondary">User Account:</span>
                <span className="font-semibold text-text-primary">{selectedTx.account_email}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Plan / Duration:</span>
                <span className="font-semibold text-text-primary">
                  {selectedTx.plan_type.toUpperCase()} ({selectedTx.duration_months} mo)
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Expected Amount:</span>
                <span className="font-semibold text-text-primary">
                  {formatUzs(selectedTx.expected_amount_uzs)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Current Status:</span>
                <span>{getStatusBadge(selectedTx.status)}</span>
              </div>
            </div>

            {/* Action Selector */}
            <div className="space-y-1.5">
              <label className="font-semibold text-text-primary">Resolution Action</label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  className={`py-2 px-2 rounded-lg border text-center font-medium transition-all ${
                    reconcileAction === 'mark_paid'
                      ? 'border-emerald-500 bg-emerald-500/10 text-emerald-500 font-bold'
                      : 'border-border-button bg-bg-input text-text-secondary hover:border-border-default'
                  }`}
                  onClick={() => setReconcileAction('mark_paid')}
                >
                  Mark as PAID
                </button>
                <button
                  type="button"
                  className={`py-2 px-2 rounded-lg border text-center font-medium transition-all ${
                    reconcileAction === 'mark_failed'
                      ? 'border-rose-500 bg-rose-500/10 text-rose-500 font-bold'
                      : 'border-border-button bg-bg-input text-text-secondary hover:border-border-default'
                  }`}
                  onClick={() => setReconcileAction('mark_failed')}
                >
                  Mark as FAILED
                </button>
                <button
                  type="button"
                  className={`py-2 px-2 rounded-lg border text-center font-medium transition-all ${
                    reconcileAction === 'set_audit_note'
                      ? 'border-accent-primary bg-accent-primary/10 text-accent-primary font-bold'
                      : 'border-border-button bg-bg-input text-text-secondary hover:border-border-default'
                  }`}
                  onClick={() => setReconcileAction('set_audit_note')}
                >
                  Add Audit Note
                </button>
              </div>
            </div>

            {/* Paid Amount Field (for mark_paid) */}
            {reconcileAction === 'mark_paid' && (
              <div className="space-y-1.5">
                <label className="font-semibold text-text-primary">
                  Verified Paid Amount (UZS)
                </label>
                <Input
                  type="number"
                  placeholder="e.g. 400000"
                  value={reconcilePaidAmount}
                  onChange={(e) => setReconcilePaidAmount(Number(e.target.value))}
                  className="bg-bg-input border-border-button text-xs"
                />
                <p className="text-[11px] text-text-secondary">
                  The actual amount in Uzbek So'm confirmed received in Atmos statement.
                </p>
              </div>
            )}

            {/* Error Message Field & Revocation Warning (for mark_failed) */}
            {reconcileAction === 'mark_failed' && (
              <div className="space-y-2.5">
                <div className="space-y-1.5">
                  <label className="font-semibold text-text-primary">
                    Rejection Reason / Error Code
                  </label>
                  <Input
                    placeholder="e.g. Chargeback, Mismatch, Manual Revocation"
                    value={reconcileErrorMsg}
                    onChange={(e) => setReconcileErrorMsg(e.target.value)}
                    className="bg-bg-input border-border-button text-xs"
                  />
                </div>

                {/* 2-Step Destructive Action Confirmation */}
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 space-y-2">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="size-4 shrink-0 mt-0.5" />
                    <span className="font-semibold text-xs">
                      Irreversible Audit Warning: Revoking / Rejecting Subscription
                    </span>
                  </div>
                  <p className="text-[11px] text-text-secondary leading-relaxed">
                    Marking this transaction as <strong>FAILED</strong> immediately revokes the subscription, downgrades the tenant to <strong>FREE</strong> with 512 credits, and records this action in the financial audit log.
                  </p>
                  <label className="flex items-start gap-2 text-[11px] text-text-primary font-medium cursor-pointer pt-1 border-t border-rose-500/20">
                    <input
                      type="checkbox"
                      checked={confirmRevocationChecked}
                      onChange={(e) => setConfirmRevocationChecked(e.target.checked)}
                      className="mt-0.5 rounded border-border-button text-rose-500 focus:ring-rose-500"
                    />
                    <span>
                      I have verified the absence of payment evidence and confirm this subscription revocation.
                    </span>
                  </label>
                </div>
              </div>
            )}

            {/* Audit Note */}
            <div className="space-y-1.5">
              <label className="font-semibold text-text-primary">
                Audit Trail Explanation <span className="text-rose-500">*</span>
              </label>
              <textarea
                rows={3}
                placeholder="Detailed reason for this manual moderation action (e.g. Verified via Bank Statement ID #88931)..."
                value={reconcileAuditNote}
                onChange={(e) => setReconcileAuditNote(e.target.value)}
                className="w-full p-2.5 rounded-lg bg-bg-input border border-border-button text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
              />
              <p className="text-[11px] text-text-secondary">
                Your email as superuser administrator will be recorded alongside this note.
              </p>
            </div>

            {/* Modal Actions */}
            <div className="flex justify-end gap-2 pt-3 border-t border-border-button">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsReconcileModalOpen(false)}
                disabled={reconcileMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                className={`${
                  reconcileAction === 'mark_failed'
                    ? 'bg-rose-600 hover:bg-rose-700 text-white'
                    : 'bg-accent-primary hover:bg-accent-primary/90 text-white'
                }`}
                onClick={handleSubmitReconciliation}
                disabled={
                  reconcileMutation.isPending ||
                  !reconcileAuditNote.trim() ||
                  (reconcileAction === 'mark_failed' && !confirmRevocationChecked) ||
                  (reconcileAction === 'mark_paid' && (reconcilePaidAmount === undefined || Number(reconcilePaidAmount) < 0))
                }
              >
                {reconcileMutation.isPending
                  ? 'Submitting...'
                  : reconcileAction === 'mark_failed'
                  ? 'Confirm Revocation'
                  : 'Confirm Resolution'}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
