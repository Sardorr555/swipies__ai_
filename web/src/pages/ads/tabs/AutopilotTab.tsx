import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Zap,
  Activity,
  ShieldCheck,
  Timer,
  Sparkles,
  RefreshCw,
  Play,
  Plus,
  Trash2,
} from 'lucide-react';
import {
  AutomatedRuleItem,
  RuleTemplateItem,
  RuleExecutionLogItem,
} from '@/services/ad-service';

export interface AutopilotTabProps {
  rulesList?: AutomatedRuleItem[];
  ruleTemplates?: RuleTemplateItem[];
  ruleExecutionLogs?: RuleExecutionLogItem[];
  evaluatingRules?: boolean;
  onApplyRuleTemplate: (template: RuleTemplateItem) => void;
  onEvaluateRules: () => void;
  onOpenCreateRuleModal: () => void;
  onToggleRule: (ruleId: string) => void;
  onDeleteRule: (ruleId: string) => void;
}

export const AutopilotTab: React.FC<AutopilotTabProps> = ({
  rulesList = [],
  ruleTemplates = [],
  ruleExecutionLogs = [],
  evaluatingRules = false,
  onApplyRuleTemplate,
  onEvaluateRules,
  onOpenCreateRuleModal,
  onToggleRule,
  onDeleteRule,
}) => {
  return (
    <div className="space-y-6">
      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-cyan-500/20 bg-gradient-to-br from-cyan-500/5 to-transparent">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Активные авто-правила</span>
              <Zap className="h-4 w-4 text-cyan-500" />
            </div>
            <div className="text-2xl font-bold text-foreground mt-1">
              {Array.isArray(rulesList) ? rulesList.filter((r) => r.is_active).length : 0} / {Array.isArray(rulesList) ? rulesList.length : 0}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">Круглосуточный мониторинг</p>
          </CardContent>
        </Card>

        <Card className="border-emerald-500/20 bg-gradient-to-br from-emerald-500/5 to-transparent">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Срабатываний авто-правил</span>
              <Activity className="h-4 w-4 text-emerald-500" />
            </div>
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
              {Array.isArray(rulesList) ? rulesList.reduce((acc, r) => acc + (r.trigger_count || 0), 0) : 0}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">Автоматических оптимизаций</p>
          </CardContent>
        </Card>

        <Card className="border-amber-500/20 bg-gradient-to-br from-amber-500/5 to-transparent">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Защита бюджета (Stop-Loss)</span>
              <ShieldCheck className="h-4 w-4 text-amber-500" />
            </div>
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">
              {Array.isArray(rulesList) ? rulesList.filter((r) => r.action_type === 'pause_campaign').length : 0} правил
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">Предотвращают слив средств</p>
          </CardContent>
        </Card>

        <Card className="border-purple-500/20 bg-gradient-to-br from-purple-500/5 to-transparent">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground">Плавный расход (Pacing)</span>
              <Timer className="h-4 w-4 text-purple-500" />
            </div>
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400 mt-1">
              24/7
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">Сглаживание пиковых скачков</p>
          </CardContent>
        </Card>
      </div>

      {/* 1-Click Recipe Templates */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-cyan-500" /> Готовые рецепты автоматизации в 1 клик
            </CardTitle>
            <CardDescription className="text-xs">
              Выберите готовый шаблон для защиты инвестиций или быстрого масштабирования конверсий.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {(ruleTemplates || []).map((tmpl) => (
              <div
                key={tmpl.template_id}
                className="p-3.5 rounded-xl border border-muted hover:border-cyan-500/40 bg-card hover:bg-muted/30 transition-all flex flex-col justify-between"
              >
                <div>
                  <h4 className="font-bold text-xs text-foreground flex items-center gap-1.5">
                    {tmpl.name}
                  </h4>
                  <p className="text-[11px] text-muted-foreground mt-1 line-clamp-3">
                    {tmpl.description}
                  </p>
                </div>
                <div className="mt-3 pt-2 border-t flex items-center justify-between">
                  <Badge variant="outline" className="text-[9px] uppercase font-mono">
                    {tmpl.metric} {tmpl.operator} {tmpl.threshold_value}
                  </Badge>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onApplyRuleTemplate(tmpl)}
                    className="h-6 text-[10px] px-2 text-cyan-600 hover:bg-cyan-500/10 border-cyan-500/30"
                  >
                    + Добавить
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Active Rules List Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Zap className="h-4 w-4 text-amber-500" /> Настроенные правила Auto-Pilot ({(Array.isArray(rulesList) ? rulesList.length : 0)})
            </CardTitle>
            <CardDescription className="text-xs">
              Правила непрерывно проверяют метрики и автоматически реагируют на изменения.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={onEvaluateRules}
              disabled={evaluatingRules}
              className="text-xs flex items-center gap-1.5 border-cyan-500/30 text-cyan-600 hover:bg-cyan-500/10"
            >
              {evaluatingRules ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              {evaluatingRules ? 'Проверка...' : 'Проверить правила сейчас'}
            </Button>
            <Button
              size="sm"
              onClick={onOpenCreateRuleModal}
              className="bg-cyan-600 hover:bg-cyan-700 text-white text-xs"
            >
              <Plus className="mr-1 h-3.5 w-3.5" /> Создать правило
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {!Array.isArray(rulesList) || rulesList.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground text-xs">
              У вас пока нет настроенных правил. Выберите готовый рецепт выше или создайте новое правило.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b bg-muted/40 uppercase text-muted-foreground text-[10px]">
                  <tr>
                    <th className="py-2.5 px-3">Правило / Описание</th>
                    <th className="py-2.5 px-3">Кампания</th>
                    <th className="py-2.5 px-3">Условие триггера</th>
                    <th className="py-2.5 px-3">Действие</th>
                    <th className="py-2.5 px-3">Срабатываний</th>
                    <th className="py-2.5 px-3">Статус</th>
                    <th className="py-2.5 px-3 text-right">Управление</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(rulesList || []).map((r) => (
                    <tr key={r.id} className="hover:bg-muted/30">
                      <td className="py-3 px-3">
                        <div className="font-semibold text-foreground">{r.name}</div>
                        <div className="text-[11px] text-muted-foreground">{r.description || '—'}</div>
                      </td>
                      <td className="py-3 px-3">
                        <Badge variant="outline" className="text-[10px]">
                          {r.campaign_name || 'Все кампании'}
                        </Badge>
                      </td>
                      <td className="py-3 px-3">
                        <div className="font-mono text-cyan-600 font-bold">
                          {(r.metric || '').toUpperCase()} {r.operator} {r.threshold_value}
                        </div>
                        <div className="text-[10px] text-muted-foreground">
                          мин. {r.min_impressions} показов ({r.time_window})
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <Badge
                          variant="outline"
                          className={
                            r.action_type === 'pause_campaign'
                              ? 'border-rose-500/30 bg-rose-500/10 text-rose-600'
                              : r.action_type === 'increase_budget'
                              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600'
                              : 'border-blue-500/30 bg-blue-500/10 text-blue-600'
                          }
                        >
                          {r.action_type === 'pause_campaign' && '🛑 Пауза'}
                          {r.action_type === 'resume_campaign' && '▶️ Возобновление'}
                          {r.action_type === 'increase_bid' && `📈 Ставка +${r.action_value}%`}
                          {r.action_type === 'decrease_bid' && `📉 Ставка -${r.action_value}%`}
                          {r.action_type === 'increase_budget' && `🚀 Бюджет +${r.action_value}%`}
                          {r.action_type === 'decrease_budget' && `💰 Бюджет -${r.action_value}%`}
                          {r.action_type === 'send_alert' && '🔔 Алерт'}
                        </Badge>
                      </td>
                      <td className="py-3 px-3 font-semibold">
                        {r.trigger_count || 0} раз
                      </td>
                      <td className="py-3 px-3">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onToggleRule(r.id)}
                          className="h-6 text-[10px] px-2 font-semibold"
                        >
                          {r.is_active ? '🟢 Включено' : '⚪ Выключено'}
                        </Button>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onDeleteRule(r.id)}
                          className="text-rose-500 hover:text-rose-700 h-7 w-7 p-0"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Execution History Logs */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Activity className="h-4 w-4 text-cyan-500" /> Журнал выполнения правил и срабатываний Auto-Pilot
          </CardTitle>
          <CardDescription className="text-xs">
            История всех автоматических решений: паузы, масштабирование бюджета, корректировка ставок.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!Array.isArray(ruleExecutionLogs) || ruleExecutionLogs.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground text-xs">
              Журнал пуст. Срабатывания авто-правил будут фиксироваться здесь в реальном времени.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b bg-muted/40 uppercase text-muted-foreground text-[10px]">
                  <tr>
                    <th className="py-2.5 px-3">Время</th>
                    <th className="py-2.5 px-3">Правило</th>
                    <th className="py-2.5 px-3">Кампания</th>
                    <th className="py-2.5 px-3">Метрика / Значение</th>
                    <th className="py-2.5 px-3">Выполненное действие</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(ruleExecutionLogs || []).map((log) => {
                    const formattedDate = log.create_time
                      ? (() => {
                          const d = new Date(log.create_time);
                          return isNaN(d.getTime())
                            ? String(log.create_time)
                            : d.toLocaleString([], { dateStyle: 'short', timeStyle: 'medium' });
                        })()
                      : '—';
                    return (
                      <tr key={log.id} className="hover:bg-muted/30">
                        <td className="py-2.5 px-3 text-muted-foreground whitespace-nowrap">
                          {formattedDate}
                        </td>
                        <td className="py-2.5 px-3 font-semibold text-foreground">{log.rule_name}</td>
                        <td className="py-2.5 px-3 text-muted-foreground">{log.campaign_name}</td>
                        <td className="py-2.5 px-3 font-mono text-cyan-600 font-bold">
                          {(log.metric_name || '').toUpperCase()} = {log.metric_current_value}
                        </td>
                        <td className="py-2.5 px-3 text-foreground font-medium">
                          {log.action_details || log.action_taken}
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
    </div>
  );
};
