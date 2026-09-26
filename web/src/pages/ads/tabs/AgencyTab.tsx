import React from 'react';
import {
  Building2,
  Briefcase,
  Wallet,
  Lock,
  Settings2,
  FileSpreadsheet,
  DollarSign,
  Users,
  Layers,
  Plus,
  Trash2,
  UserPlus,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import {
  AgencyWorkspace,
  AgencyClient,
  AgencyMember,
} from '@/services/ad-service';
import { toFixedSafe } from '../format-utils';

export interface AgencyTabProps {
  agencyWorkspace: AgencyWorkspace | null;
  agencyClients: AgencyClient[];
  agencyMembers: AgencyMember[];
  onOpenSettingsModal: () => void;
  onOpenExecutiveReport: (clientId?: string) => void;
  onOpenAddClientModal: () => void;
  onDeleteClient: (clientId: string, clientName: string) => void;
  onOpenInviteMemberModal: () => void;
  onRemoveMember: (memberId: string) => void;
}

export const AgencyTab: React.FC<AgencyTabProps> = ({
  agencyWorkspace,
  agencyClients,
  agencyMembers,
  onOpenSettingsModal,
  onOpenExecutiveReport,
  onOpenAddClientModal,
  onDeleteClient,
  onOpenInviteMemberModal,
  onRemoveMember,
}) => {
  return (
    <div className="space-y-6">
      {/* Agency Top Hero Banner */}
      <div className="rounded-2xl border bg-gradient-to-br from-indigo-500/10 via-purple-500/5 to-background p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div
              className="flex h-16 w-16 items-center justify-center rounded-2xl shadow-md border text-white font-bold text-xl overflow-hidden shrink-0"
              style={{ backgroundColor: agencyWorkspace?.brand_color || '#6366f1' }}
            >
              {agencyWorkspace?.logo_url && agencyWorkspace.logo_url.startsWith('http') ? (
                <img
                  src={agencyWorkspace.logo_url}
                  alt={agencyWorkspace.name}
                  className="h-full w-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
              ) : (
                <Building2 className="h-8 w-8" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xl font-black tracking-tight text-foreground">
                  {agencyWorkspace?.name || 'Agency Enterprise Hub'}
                </h3>
                <Badge variant="secondary" className="text-xs bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-semibold">
                  Enterprise Agency Hub
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Единый центр управления клиентскими субаккаунтами, бюджетами, командой с RBAC и White-Label отчетностью
              </p>
              <div className="flex flex-wrap items-center gap-3 mt-2 text-[11px] text-muted-foreground">
                <span className="flex items-center gap-1 font-mono">
                  <Briefcase className="h-3 w-3 text-indigo-500" />
                  slug: <span className="text-foreground font-semibold">{agencyWorkspace?.agency_slug || 'agency'}</span>
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Wallet className="h-3 w-3 text-emerald-500" />
                  Биллинг: <span className="text-foreground font-semibold capitalize">{agencyWorkspace?.billing_mode || 'consolidated'}</span>
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Lock className="h-3 w-3 text-purple-500" />
                  RBAC Защита: <span className="text-foreground font-semibold">Включена</span>
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              onClick={onOpenSettingsModal}
              className="text-xs flex items-center gap-1.5 border-indigo-500/30 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-500/10"
            >
              <Settings2 className="h-3.5 w-3.5" /> White-Label Брендинг
            </Button>
            <Button
              size="sm"
              onClick={() => onOpenExecutiveReport()}
              className="text-xs flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm"
            >
              <FileSpreadsheet className="h-3.5 w-3.5" /> Сводный Executive Report
            </Button>
          </div>
        </div>
      </div>

      {/* 4-Grid Agency KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-indigo-500/20 bg-indigo-50/20 dark:bg-indigo-950/10">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Клиентские субаккаунты</span>
              <Briefcase className="h-4 w-4 text-indigo-500" />
            </div>
            <div className="text-2xl font-bold text-foreground mt-1">
              {(Array.isArray(agencyClients) ? agencyClients.length : 0)}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">Активных брендов в управлении</p>
          </CardContent>
        </Card>

        <Card className="border-emerald-500/20 bg-emerald-50/20 dark:bg-emerald-950/10">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Управляемый рекламный бюджет</span>
              <DollarSign className="h-4 w-4 text-emerald-500" />
            </div>
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
              ${toFixedSafe(agencyWorkspace?.total_managed_spend, 2)}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">Совокупный spend клиентов</p>
          </CardContent>
        </Card>

        <Card className="border-purple-500/20 bg-purple-50/20 dark:bg-purple-950/10">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Сотрудники и RBAC роли</span>
              <Users className="h-4 w-4 text-purple-500" />
            </div>
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400 mt-1">
              {(Array.isArray(agencyMembers) ? agencyMembers.length : 0)}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">Медиабайеры, дизайнеры, аудиторы</p>
          </CardContent>
        </Card>

        <Card className="border-blue-500/20 bg-blue-50/20 dark:bg-blue-950/10">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Активные кампании клиентов</span>
              <Layers className="h-4 w-4 text-blue-500" />
            </div>
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">
              {Array.isArray(agencyClients) ? agencyClients.reduce((sum, c) => sum + (c.active_campaigns_count || 0), 0) : 0}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              из {Array.isArray(agencyClients) ? agencyClients.reduce((sum, c) => sum + (c.campaigns_count || 0), 0) : 0} запущенных
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Section 1: Sub-Accounts Management */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <div>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Briefcase className="h-4 w-4 text-indigo-500" /> Клиентские Субаккаунты (Sub-Accounts)
            </CardTitle>
            <CardDescription className="text-xs">
              Изолированные рекламные пространства для каждого клиента с персональными лимитами и аналитикой
            </CardDescription>
          </div>
          <Button
            size="sm"
            onClick={onOpenAddClientModal}
            className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            <Plus className="h-3.5 w-3.5 mr-1" /> Добавить субаккаунт
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {!Array.isArray(agencyClients) || agencyClients.length === 0 ? (
            <div className="py-12 text-center text-xs text-muted-foreground">
              <Briefcase className="h-8 w-8 mx-auto text-muted-foreground/50 mb-2" />
              У вас пока нет созданных субаккаунтов клиентов. Нажмите «Добавить субаккаунт», чтобы подключить бренд.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b bg-muted/40 uppercase text-muted-foreground">
                  <tr>
                    <th className="py-2.5 px-4">Бренд / Субаккаунт</th>
                    <th className="py-2.5 px-4">Месячный Лимит & Spend</th>
                    <th className="py-2.5 px-4">Кампании</th>
                    <th className="py-2.5 px-4">Клики & CTR%</th>
                    <th className="py-2.5 px-4">Конверсии & CPA</th>
                    <th className="py-2.5 px-4 text-right">Отчет & Действия</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(agencyClients || []).map((client) => {
                    const spendPercent = client.monthly_budget_cap > 0
                      ? Math.min(100, Math.round((client.total_spend / client.monthly_budget_cap) * 100))
                      : 0;

                    return (
                      <tr key={client.id} className="hover:bg-muted/30 transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-bold text-foreground">{client.client_name}</div>
                          <div className="text-[11px] text-muted-foreground flex items-center gap-1 font-mono">
                            {client.contact_email || '—'}
                          </div>
                        </td>
                        <td className="py-3 px-4 min-w-[180px]">
                          <div className="flex items-center justify-between text-[11px] font-medium mb-1">
                            <span className="font-bold text-foreground">${toFixedSafe(client.total_spend, 2)}</span>
                            <span className="text-muted-foreground">
                              {client.monthly_budget_cap > 0 ? `/ $${toFixedSafe(client.monthly_budget_cap, 2)}` : 'Без лимита'}
                            </span>
                          </div>
                          {client.monthly_budget_cap > 0 && (
                            <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${
                                  spendPercent > 90
                                    ? 'bg-rose-500'
                                    : spendPercent > 70
                                    ? 'bg-amber-500'
                                    : 'bg-indigo-600'
                                }`}
                                style={{ width: `${spendPercent}%` }}
                              />
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <Badge variant="outline" className="text-[11px] font-semibold">
                            {client.active_campaigns_count} акт. / {client.campaigns_count} всего
                          </Badge>
                        </td>
                        <td className="py-3 px-4">
                          <div className="font-semibold text-foreground">{client.total_clicks} кликов</div>
                          <div className="text-[11px] text-muted-foreground">{client.avg_ctr}% CTR</div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="font-semibold text-emerald-600 dark:text-emerald-400">
                            {client.total_conversions} конв.
                          </div>
                          <div className="text-[11px] text-muted-foreground">
                            {client.avg_cpa > 0 ? `$${toFixedSafe(client.avg_cpa, 2)} CPA` : '—'}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => onOpenExecutiveReport(client.id)}
                              className="text-xs h-7 border-indigo-500/30 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-500/10 flex items-center gap-1 font-medium"
                            >
                              <FileSpreadsheet className="h-3 w-3" /> Report
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => onDeleteClient(client.id, client.client_name)}
                              className="text-xs h-7 text-rose-500 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/20"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section 2: Team & RBAC Permissions */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <div>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Users className="h-4 w-4 text-purple-500" /> Команда Агентства & Роли Доступа (RBAC)
            </CardTitle>
            <CardDescription className="text-xs">
              Гранулярное распределение полномочий: медиабайеры, дизайнеры, финансовые аудиторы и клиенты
            </CardDescription>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={onOpenInviteMemberModal}
            className="text-xs border-purple-500/30 text-purple-600 dark:text-purple-400 hover:bg-purple-500/10"
          >
            <UserPlus className="h-3.5 w-3.5 mr-1" /> Пригласить сотрудника
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b bg-muted/40 uppercase text-muted-foreground">
                <tr>
                  <th className="py-2.5 px-4">Сотрудник / Email</th>
                  <th className="py-2.5 px-4">Роль в Агентстве (RBAC)</th>
                  <th className="py-2.5 px-4">Доступные Субаккаунты</th>
                  <th className="py-2.5 px-4">Статус</th>
                  <th className="py-2.5 px-4 text-right">Действия</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {(agencyMembers || []).map((member) => (
                  <tr key={member.id} className="hover:bg-muted/30 transition-colors">
                    <td className="py-3 px-4 font-medium text-foreground">
                      {member.email}
                      <div className="text-[10px] text-muted-foreground font-mono">
                        ID: {member.id.slice(0, 8)}...
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <Badge
                        variant="secondary"
                        className={`text-[10px] font-bold ${
                          member.role === 'agency_admin'
                            ? 'bg-purple-500/10 text-purple-600 border-purple-500/30'
                            : member.role === 'media_buyer'
                            ? 'bg-blue-500/10 text-blue-600 border-blue-500/30'
                            : member.role === 'creative_designer'
                            ? 'bg-amber-500/10 text-amber-600 border-amber-500/30'
                            : member.role === 'financial_auditor'
                            ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30'
                            : 'bg-muted text-muted-foreground'
                        }`}
                      >
                        {member.role === 'agency_admin' && '👑 Agency Admin (Владелец)'}
                        {member.role === 'media_buyer' && '🎯 Media Buyer (Кампании & Bids)'}
                        {member.role === 'creative_designer' && '🎨 Creative Designer (Студия & Feeds)'}
                        {member.role === 'financial_auditor' && '📊 Financial Auditor (Биллинг & Отчеты)'}
                        {member.role === 'client_viewer' && '👁️ Client Viewer (Read-only)'}
                      </Badge>
                    </td>
                    <td className="py-3 px-4">
                      {member.assigned_client_ids && Array.isArray(member.assigned_client_ids) && member.assigned_client_ids.length > 0 ? (
                        <span className="text-[11px] text-foreground font-medium">
                          {member.assigned_client_ids.length} субаккаунтов
                        </span>
                      ) : (
                        <Badge variant="outline" className="text-[10px] text-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/20">
                          🌐 Все субаккаунты
                        </Badge>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant="outline" className="text-[10px] text-emerald-600 border-emerald-500/20 bg-emerald-500/10">
                        Активен
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-right">
                      {member.role !== 'agency_admin' && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onRemoveMember(member.id)}
                          className="text-xs h-7 text-rose-500 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/20"
                        >
                          Отозвать
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Section 3: White-Label Reporting Capabilities Card */}
      <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <FileSpreadsheet className="h-5 w-5 text-indigo-500 mt-0.5 shrink-0" />
          <div>
            <h4 className="text-xs font-bold text-foreground">
              White-Label Экспорт и Публичные Отчеты для Клиентов
            </h4>
            <p className="text-xs text-muted-foreground mt-0.5">
              Создавайте брендированные отчеты в PDF и CSV с логотипом вашего агентства, индивидуальной цветовой палитрой и делитесь защищенными ссылками без входа в систему.
            </p>
          </div>
        </div>
        <Button
          size="sm"
          onClick={() => onOpenExecutiveReport()}
          className="text-xs shrink-0 bg-indigo-600 hover:bg-indigo-700 text-white"
        >
          Сформировать сводный отчет
        </Button>
      </div>
    </div>
  );
};
