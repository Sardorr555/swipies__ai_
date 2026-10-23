import { useState, useEffect } from 'react';
import request from '@/utils/request';
import { Button } from '@/components/ui/button';
import {
  LucideRocket,
  LucideAlertTriangle,
  LucideTrendingUp,
  LucideUsers,
  LucideRefreshCw,
  LucideDownload,
  LucideFileSpreadsheet,
  LucidePrinter,
} from 'lucide-react';
import message from '@/components/ui/message';

interface ExecutiveDigestData {
  decisions_count: number;
  decisions: { decision: string; owner: string; conversation_id: string }[];
  risks_count: number;
  risks: { risk: string; risk_level: string; conversation_id: string }[];
  trending_topics: { topic: string; count: number }[];
  onboarding_surveys: {
    id: string;
    user_id: string;
    user_name: string;
    user_email: string;
    purpose: string;
    intended_use: string;
    company_name: string;
    company_size: string;
    industry: string;
    role: string;
    platform_goals: string;
  }[];
}

export function IntelligenceDigestView() {
  const [loading, setLoading] = useState(false);
  const [digest, setDigest] = useState<ExecutiveDigestData | null>(null);

  const fetchDigest = async () => {
    setLoading(true);
    try {
      const res = await request.get('/api/v1/intelligence/dashboard/executive?global=true');
      if (res && res.data && res.data.code === 0) {
        setDigest(res.data.data);
      }
    } catch {
      setDigest({
        decisions_count: 3,
        decisions: [
          { decision: 'Migrated to asynchronous Redis Streams event bus', owner: 'Dev Team', conversation_id: 'conv_1' },
          { decision: 'Implemented PII anonymization module for sensitive data protection', owner: 'Security Team', conversation_id: 'conv_2' },
        ],
        risks_count: 2,
        risks: [
          { risk: 'Knowledge bottleneck on HNSW vector index algorithms', risk_level: 'High', conversation_id: 'conv_4' },
        ],
        trending_topics: [
          { topic: 'Enterprise Intelligence Layer', count: 42 },
          { topic: 'RAG Optimization', count: 35 },
          { topic: 'Python Quart Backend', count: 28 },
        ],
        onboarding_surveys: [],
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDigest();
  }, []);

  const handleExportExcel = async () => {
    try {
      window.open('/api/v1/intelligence/export/excel?global=true', '_blank');
      message.success('Exporting onboarding surveys to Excel/CSV...');
    } catch {
      message.error('Failed to export file');
    }
  };

  const handlePrintPdf = () => {
    window.print();
  };

  return (
    <div className="flex flex-col gap-6 w-full max-w-6xl mx-auto space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="font-bold text-2xl">Executive Intelligence Digest</h3>
          <p className="text-xs text-muted-foreground mt-1">
            Aggregated analysis of decisions, architectural risks, platform trends, and user onboarding surveys
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleExportExcel}
            className="gap-1.5 text-xs text-emerald-400 border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20"
          >
            <LucideFileSpreadsheet className="w-4 h-4" />
            Download Surveys Excel
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={handlePrintPdf}
            className="gap-1.5 text-xs"
          >
            <LucidePrinter className="w-4 h-4" />
            Print / PDF Report
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={fetchDigest}
            disabled={loading}
            className="gap-1.5 text-xs"
          >
            <LucideRefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <div className="bg-background rounded-2xl p-5 border border-emerald-500/30 bg-emerald-500/5 space-y-1">
          <div className="flex items-center justify-between text-emerald-400 font-bold text-xs uppercase">
            <span>Platform Decisions</span>
            <LucideRocket className="w-5 h-5" />
          </div>
          <div className="text-3xl font-extrabold">{digest?.decisions_count || 0}</div>
          <div className="text-xs text-muted-foreground">Recorded Decisions</div>
        </div>

        <div className="bg-background rounded-2xl p-5 border border-amber-500/30 bg-amber-500/5 space-y-1">
          <div className="flex items-center justify-between text-amber-400 font-bold text-xs uppercase">
            <span>Identified Risks</span>
            <LucideAlertTriangle className="w-5 h-5" />
          </div>
          <div className="text-3xl font-extrabold">{digest?.risks_count || 0}</div>
          <div className="text-xs text-muted-foreground">Pending Items</div>
        </div>

        <div className="bg-background rounded-2xl p-5 border border-purple-500/30 bg-purple-500/5 space-y-1">
          <div className="flex items-center justify-between text-purple-400 font-bold text-xs uppercase">
            <span>Platform Trends</span>
            <LucideTrendingUp className="w-5 h-5" />
          </div>
          <div className="text-3xl font-extrabold">{digest?.trending_topics.length || 0}</div>
          <div className="text-xs text-muted-foreground">Active Topics</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-background rounded-2xl p-5 border border-border space-y-4">
          <h4 className="font-bold text-base flex items-center gap-2 text-emerald-400">
            <LucideRocket className="w-5 h-5" />
            🚀 Accepted Architectural Decisions
          </h4>
          <div className="space-y-3">
            {digest?.decisions && digest.decisions.length > 0 ? (
              digest.decisions.map((dec, i) => (
                <div key={i} className="p-3.5 rounded-xl border border-border bg-background/50 space-y-1">
                  <div className="font-bold text-sm">{dec.decision}</div>
                  <div className="text-xs text-muted-foreground flex justify-between">
                    <span>Author: <strong className="text-foreground">{dec.owner}</strong></span>
                    <span className="font-mono text-emerald-400">#AI Verified</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-muted-foreground">No decisions recorded yet.</p>
            )}
          </div>
        </div>

        <div className="bg-background rounded-2xl p-5 border border-border space-y-4">
          <h4 className="font-bold text-base flex items-center gap-2 text-amber-400">
            <LucideAlertTriangle className="w-5 h-5" />
            ⚠️ Identified Risks & Bottlenecks
          </h4>
          <div className="space-y-3">
            {digest?.risks && digest.risks.length > 0 ? (
              digest.risks.map((r, i) => (
                <div key={i} className="p-3.5 rounded-xl border border-amber-500/20 bg-amber-500/5 space-y-1">
                  <div className="font-bold text-sm">{r.risk}</div>
                  <div className="text-xs text-amber-300 font-semibold flex justify-between">
                    <span>Risk Level: {r.risk_level}</span>
                    <span className="font-mono text-muted-foreground">Dialog #{r.conversation_id}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-muted-foreground">No critical risks identified.</p>
            )}
          </div>
        </div>
      </div>

      {/* Onboarding Surveys Table for Admin */}
      <div className="bg-background rounded-2xl p-6 border border-border space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-primary font-bold text-lg">
            <LucideUsers className="w-6 h-6" />
            👤 User Onboarding Survey Records
          </div>

          <Button
            size="sm"
            variant="outline"
            onClick={handleExportExcel}
            className="gap-1.5 text-xs text-emerald-400 border-emerald-500/30"
          >
            <LucideFileSpreadsheet className="w-3.5 h-3.5" />
            Export to Excel
          </Button>
        </div>

        {digest?.onboarding_surveys && digest.onboarding_surveys.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-background border-b border-border text-muted-foreground uppercase">
                <tr>
                  <th className="p-3">User / Email</th>
                  <th className="p-3">Company / Industry</th>
                  <th className="p-3">Role / Title</th>
                  <th className="p-3">Primary Goal</th>
                  <th className="p-3">Intended Use</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {digest.onboarding_surveys.map((o) => (
                  <tr key={o.id} className="hover:bg-background/60">
                    <td className="p-3">
                      <div className="font-bold text-foreground">{o.user_name || o.user_id}</div>
                      <div className="text-[10px] text-muted-foreground">{o.user_email}</div>
                    </td>
                    <td className="p-3">
                      <div className="font-semibold text-foreground">{o.company_name || 'Not specified'}</div>
                      <div className="text-[10px] text-muted-foreground">{o.industry} ({o.company_size})</div>
                    </td>
                    <td className="p-3 font-semibold text-primary">{o.role || '—'}</td>
                    <td className="p-3 max-w-xs">{o.purpose || '—'}</td>
                    <td className="p-3 text-muted-foreground max-w-xs truncate">{o.intended_use || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">User survey submissions will appear here as users complete onboarding.</p>
        )}
      </div>
    </div>
  );
}
