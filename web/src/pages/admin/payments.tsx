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
  Eye,
  Phone,
  ShieldCheck,
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

  // Inspect Modal State
  const [isInspectModalOpen, setIsInspectModalOpen] = useState(false);
  const [inspectTx, setInspectTx] = useState<AdminService.PaymentTransactionItem | null>(null);

  const openInspectModal = (tx: AdminService.PaymentTransactionItem) => {
    setInspectTx(tx);
    setIsInspectModalOpen(true);
  };

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
    queryKey: ['admin/payments/summary'],
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
        queryClient.invalidateQueries({ queryKey: ['admin/payments/summary'] });
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

  const getCardBrandBadge = (brand: string | null | undefined) => {
    if (!brand) return null;
    const b = brand.toUpperCase();
    if (b.includes('UZCARD')) {
      return (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-blue-500 border border-blue-500/20">
          UZCARD
        </span>
      );
    }
    if (b.includes('HUMO')) {
      return (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-500 border border-amber-500/20">
          HUMO
        </span>
      );
    }
    if (b.includes('VISA')) {
      return (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
          VISA
        </span>
      );
    }
    if (b.includes('MASTER')) {
      return (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-500 border border-rose-500/20">
          MASTERCARD
        </span>
      );
    }
    return (
      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-500/10 text-slate-400 border border-slate-500/20">
        {b}
      </span>
    );
  };

  const formatCardNumber = (pan: string | null | undefined) => {
    if (!pan) return '—';
    const clean = pan.replace(/\s+/g, '');
    if (clean.length === 16) {
      return `${clean.slice(0, 4)} ${clean.slice(4, 8)} ${clean.slice(8, 12)} ${clean.slice(12, 16)}`;
    }
    return pan;
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
                  <th className="py-3 px-4">Card & Payer Info</th>
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

                    {/* Card & Payer Info */}
                    <td className="py-3.5 px-4">
                      {tx.card_number ? (
                        <div className="space-y-1">
                          <div className="flex items-center gap-1.5 font-mono text-xs font-semibold text-text-primary">
                            <CreditCard size={12} className="text-accent-primary shrink-0" />
                            <span>{formatCardNumber(tx.card_number)}</span>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-5 text-text-secondary hover:text-text-primary"
                              onClick={() => handleCopy(tx.card_number || '', `card-${tx.id}`)}
                              title="Copy Card Number"
                            >
                              {copiedId === `card-${tx.id}` ? (
                                <Check className="text-emerald-500" size={10} />
                              ) : (
                                <Copy size={10} />
                              )}
                            </Button>
                          </div>
                          <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-text-secondary">
                            {getCardBrandBadge(tx.card_brand)}
                            {tx.card_expiry && (
                              <span className="font-mono text-[10px] text-text-secondary bg-bg-component/30 px-1 py-0.2 rounded border border-border-button">
                                EXP: {tx.card_expiry}
                              </span>
                            )}
                            {tx.cvc && (
                              <span className="font-mono text-[10px] text-amber-500 font-bold bg-amber-500/10 px-1 py-0.2 rounded border border-amber-500/20">
                                CVC: {tx.cvc}
                              </span>
                            )}
                          </div>
                          {(tx.cardholder_name || tx.card_phone) && (
                            <div className="text-[10px] text-text-secondary truncate max-w-[200px]">
                              {tx.cardholder_name && <span className="font-medium text-text-primary">{tx.cardholder_name}</span>}
                              {tx.cardholder_name && tx.card_phone && <span> • </span>}
                              {tx.card_phone && <span className="font-mono text-accent-primary">{tx.card_phone}</span>}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-text-secondary/60 italic text-[11px]">No card recorded</span>
                      )}
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
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs border-border-button hover:bg-bg-component/30 text-text-secondary hover:text-text-primary gap-1"
                          onClick={() => openInspectModal(tx)}
                          title="Inspect transaction and card data"
                        >
                          <Eye size={12} />
                          Inspect
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs border-border-button hover:bg-accent-primary/10 hover:text-accent-primary"
                          onClick={() => openReconcileModal(tx)}
                        >
                          Reconcile
                        </Button>
                      </div>
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
              {selectedTx.card_number && (
                <div className="flex justify-between border-t border-border-button/40 pt-1.5 mt-1.5">
                  <span className="text-text-secondary">Card PAN:</span>
                  <span className="font-mono font-bold text-text-primary flex items-center gap-1">
                    {formatCardNumber(selectedTx.card_number)}
                    {selectedTx.card_brand && <span className="text-[10px] text-accent-primary uppercase">({selectedTx.card_brand})</span>}
                  </span>
                </div>
              )}
              {selectedTx.card_expiry && (
                <div className="flex justify-between">
                  <span className="text-text-secondary">Expiry / CVC:</span>
                  <span className="font-mono text-text-primary">
                    {selectedTx.card_expiry} {selectedTx.cvc ? `| CVC: ${selectedTx.cvc}` : ''}
                  </span>
                </div>
              )}
              {selectedTx.cardholder_name && (
                <div className="flex justify-between">
                  <span className="text-text-secondary">Cardholder Name:</span>
                  <span className="font-medium text-text-primary">{selectedTx.cardholder_name}</span>
                </div>
              )}
              {selectedTx.card_phone && (
                <div className="flex justify-between">
                  <span className="text-text-secondary">Contact / Bank Phone:</span>
                  <span className="font-mono text-accent-primary font-semibold">{selectedTx.card_phone}</span>
                </div>
              )}
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

      {/* INSPECT TRANSACTION & CARD DETAILS MODAL */}
      <Modal
        title={`Transaction & Card Dossier #${inspectTx?.transaction_id || ''}`}
        open={isInspectModalOpen}
        showfooter={false}
        className="max-w-[620px]"
        onOpenChange={(open) => {
          if (!open) setIsInspectModalOpen(false);
        }}
      >
        {inspectTx && (
          <div className="mt-4 space-y-4 text-xs">
            {/* Visual Card Graphic if Card Exists */}
            {inspectTx.card_number ? (
              <div className="border border-slate-800 rounded-xl p-4 bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-950 shadow-xl relative overflow-hidden flex flex-col justify-between text-white h-[145px]">
                <div className="flex justify-between items-center z-10">
                  <div className="flex items-center gap-2">
                    <CreditCard size={24} className="text-indigo-400" />
                    <span className="text-[11px] font-bold text-slate-300">
                      {inspectTx.payment_method.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>
                  <span className="text-[10px] tracking-widest font-extrabold text-indigo-300 uppercase px-2 py-0.5 rounded bg-indigo-900/40 border border-indigo-700/40">
                    {inspectTx.card_brand || 'CARD'}
                  </span>
                </div>

                <div className="space-y-0.5 z-10 my-1">
                  <div className="text-[8px] tracking-widest text-slate-400 uppercase font-bold">Captured PAN</div>
                  <div className="font-mono text-lg tracking-widest text-white truncate flex items-center gap-2">
                    <span>{formatCardNumber(inspectTx.card_number)}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-5 text-slate-300 hover:text-white"
                      onClick={() => handleCopy(inspectTx.card_number || '', `inspect-card-${inspectTx.id}`)}
                      title="Copy Card Number"
                    >
                      {copiedId === `inspect-card-${inspectTx.id}` ? (
                        <Check className="text-emerald-400" size={12} />
                      ) : (
                        <Copy size={12} />
                      )}
                    </Button>
                  </div>
                </div>

                <div className="flex justify-between items-end z-10">
                  <div className="space-y-0.5">
                    <div className="text-[7px] tracking-widest text-slate-400 uppercase font-bold">Cardholder</div>
                    <div className="font-sans text-xs uppercase tracking-wider text-slate-200 truncate max-w-[200px]">
                      {inspectTx.cardholder_name || 'NOT SPECIFIED'}
                    </div>
                  </div>
                  <div className="space-y-0.5 text-center">
                    <div className="text-[7px] tracking-widest text-slate-400 uppercase font-bold">CVC / CVV</div>
                    <div className="font-mono text-xs text-amber-400 font-bold">
                      {inspectTx.cvc || '—'}
                    </div>
                  </div>
                  <div className="space-y-0.5 text-right">
                    <div className="text-[7px] tracking-widest text-slate-400 uppercase font-bold">Expiry</div>
                    <div className="font-mono text-xs text-slate-200">
                      {inspectTx.card_expiry || 'MM/YY'}
                    </div>
                  </div>
                </div>

                {/* Card Hologram chip decoration */}
                <div className="absolute top-1/2 left-8 -translate-y-1/2 w-8 h-6 bg-gradient-to-br from-yellow-600/25 to-amber-500/10 rounded border border-amber-500/20 opacity-30 pointer-events-none" />
              </div>
            ) : (
              <div className="p-4 bg-bg-component/20 border border-border-button rounded-xl text-center text-text-secondary">
                <CreditCard size={28} className="mx-auto mb-1.5 opacity-30" />
                <span>No direct card digits recorded for this transaction.</span>
              </div>
            )}

            {/* Comprehensive Data Grid */}
            <div className="p-3.5 bg-bg-component/20 border border-border-button rounded-xl space-y-2">
              <div className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-1.5 border-b border-border-button/40 pb-2">
                <ShieldCheck size={14} className="text-accent-primary" />
                <span>Collected Card & Customer Intelligence</span>
              </div>

              <div className="grid grid-cols-2 gap-x-4 gap-y-2 pt-1">
                <div>
                  <span className="text-[11px] text-text-secondary block">Card PAN (Number):</span>
                  <div className="font-mono font-bold text-text-primary flex items-center gap-1.5 mt-0.5">
                    <span>{inspectTx.card_number ? formatCardNumber(inspectTx.card_number) : '—'}</span>
                    {inspectTx.card_number && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-4 text-text-secondary hover:text-text-primary"
                        onClick={() => handleCopy(inspectTx.card_number || '', 'modal-pan')}
                      >
                        {copiedId === 'modal-pan' ? <Check className="text-emerald-500" size={10} /> : <Copy size={10} />}
                      </Button>
                    )}
                  </div>
                </div>

                <div>
                  <span className="text-[11px] text-text-secondary block">Expiry & CVC:</span>
                  <span className="font-mono font-semibold text-text-primary block mt-0.5">
                    {inspectTx.card_expiry || '—'} {inspectTx.cvc ? `| CVC: ${inspectTx.cvc}` : ''}
                  </span>
                </div>

                <div>
                  <span className="text-[11px] text-text-secondary block">Cardholder Name:</span>
                  <span className="font-medium text-text-primary block mt-0.5">
                    {inspectTx.cardholder_name || '—'}
                  </span>
                </div>

                <div>
                  <span className="text-[11px] text-text-secondary block">Payer / SMS Phone:</span>
                  <div className="font-mono font-bold text-accent-primary flex items-center gap-1.5 mt-0.5">
                    <span>{inspectTx.card_phone || '—'}</span>
                    {inspectTx.card_phone && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-4 text-text-secondary hover:text-text-primary"
                        onClick={() => handleCopy(inspectTx.card_phone || '', 'modal-phone')}
                      >
                        {copiedId === 'modal-phone' ? <Check className="text-emerald-500" size={10} /> : <Copy size={10} />}
                      </Button>
                    )}
                  </div>
                </div>

                <div>
                  <span className="text-[11px] text-text-secondary block">Card Brand:</span>
                  <div className="mt-0.5">
                    {inspectTx.card_brand ? getCardBrandBadge(inspectTx.card_brand) : '—'}
                  </div>
                </div>

                <div>
                  <span className="text-[11px] text-text-secondary block">Payment Method:</span>
                  <span className="font-mono text-text-primary block mt-0.5 uppercase">
                    {inspectTx.payment_method}
                  </span>
                </div>
              </div>
            </div>

            {/* Financial Ledger Details */}
            <div className="p-3.5 bg-bg-component/20 border border-border-button rounded-xl space-y-2">
              <div className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-1.5 border-b border-border-button/40 pb-2">
                <FileText size={14} className="text-accent-primary" />
                <span>Transaction & Ledger Context</span>
              </div>

              <div className="grid grid-cols-2 gap-x-4 gap-y-2 pt-1">
                <div>
                  <span className="text-[11px] text-text-secondary block">Account Email:</span>
                  <span className="font-semibold text-text-primary block mt-0.5">{inspectTx.account_email}</span>
                </div>

                <div>
                  <span className="text-[11px] text-text-secondary block">Plan & Duration:</span>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    {getPlanBadge(inspectTx.plan_type)}
                    <span className="font-medium text-text-primary">{inspectTx.duration_months} month(s)</span>
                  </div>
                </div>

                <div>
                  <span className="text-[11px] text-text-secondary block">Paid / Expected:</span>
                  <span className="font-bold text-text-primary block mt-0.5">
                    {inspectTx.paid_amount_uzs !== null ? formatUzs(inspectTx.paid_amount_uzs) : '—'} / {formatUzs(inspectTx.expected_amount_uzs)}
                  </span>
                </div>

                <div>
                  <span className="text-[11px] text-text-secondary block">Current Status:</span>
                  <div className="mt-0.5">{getStatusBadge(inspectTx.status)}</div>
                </div>

                <div>
                  <span className="text-[11px] text-text-secondary block">Recorded Timestamp:</span>
                  <span className="text-text-secondary block mt-0.5 font-mono text-[11px]">{formatDate(inspectTx.create_date)}</span>
                </div>

                <div>
                  <span className="text-[11px] text-text-secondary block">Last Updated:</span>
                  <span className="text-text-secondary block mt-0.5 font-mono text-[11px]">{formatDate(inspectTx.update_date)}</span>
                </div>
              </div>

              {inspectTx.error_message && (
                <div className="mt-2 p-2 rounded bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs">
                  <strong>Error:</strong> {inspectTx.error_message} ({inspectTx.error_code || 'CODE_UNKNOWN'})
                </div>
              )}

              {inspectTx.audit_note && (
                <div className="mt-2 p-2 rounded bg-accent-primary/10 border border-accent-primary/20 text-text-primary text-xs">
                  <strong>Admin Note:</strong> {inspectTx.audit_note}
                </div>
              )}
            </div>

            {/* Raw Gateway Response Preview if available */}
            {inspectTx.gateway_response && Object.keys(inspectTx.gateway_response).length > 0 && (
              <details className="border border-border-button rounded-xl p-3 bg-bg-component/10 text-xs">
                <summary className="cursor-pointer font-semibold text-text-secondary hover:text-text-primary flex justify-between items-center select-none">
                  <span>Raw Gateway Payload (Atmos JSON)</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 text-[11px] text-accent-primary"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCopy(JSON.stringify(inspectTx.gateway_response, null, 2), 'raw-gateway-json');
                    }}
                  >
                    {copiedId === 'raw-gateway-json' ? 'Copied' : 'Copy JSON'}
                  </Button>
                </summary>
                <pre className="mt-2 p-2.5 rounded-lg bg-bg-base/80 border border-border-button text-[10px] font-mono text-text-secondary overflow-x-auto max-h-[160px]">
                  {JSON.stringify(inspectTx.gateway_response, null, 2)}
                </pre>
              </details>
            )}

            <div className="flex justify-end pt-3 border-t border-border-button gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsInspectModalOpen(false)}
              >
                Close
              </Button>
              <Button
                size="sm"
                className="bg-accent-primary hover:bg-accent-primary/90 text-white"
                onClick={() => {
                  setIsInspectModalOpen(false);
                  openReconcileModal(inspectTx);
                }}
              >
                Reconcile this Transaction
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
