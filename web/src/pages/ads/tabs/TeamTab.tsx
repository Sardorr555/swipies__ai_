import React from 'react';
import { Users, UserPlus, RefreshCw, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import { TeamMemberItem } from '@/services/ad-service';

export interface TeamTabProps {
  teamMembers: TeamMemberItem[];
  loadingTeam: boolean;
  updatingMemberId?: string | null;
  onOpenInviteModal: () => void;
  onRefresh: () => void;
  onUpdateRole: (memberId: string, role: string) => void;
  onDeleteMember: (memberId: string) => void;
}

export const TeamTab: React.FC<TeamTabProps> = ({
  teamMembers,
  loadingTeam,
  updatingMemberId,
  onOpenInviteModal,
  onRefresh,
  onUpdateRole,
  onDeleteMember,
}) => {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-muted/30 p-4 rounded-xl border">
        <div>
          <h3 className="text-base font-bold flex items-center gap-2">
            <Users className="h-5 w-5 text-blue-500" />
            Командный доступ & Роли
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Приглашайте маркетологов, аналитиков и бухгалтеров для совместной работы в рекламном кабинете
          </p>
        </div>
        <Button
          onClick={onOpenInviteModal}
          size="sm"
          className="bg-blue-600 hover:bg-blue-700 text-white text-xs flex items-center gap-1.5"
        >
          <UserPlus className="h-3.5 w-3.5" /> + Пригласить участника
        </Button>
      </div>

      {/* Roles Matrix Cards */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border p-3 bg-muted/20 text-xs">
          <div className="font-semibold text-foreground flex items-center gap-1.5 mb-1">
            👑 Администратор
          </div>
          <p className="text-[11px] text-muted-foreground">
            Полный доступ: кампании, ставки, баланс, подписки, аналитика, управление участниками.
          </p>
        </div>
        <div className="rounded-lg border p-3 bg-muted/20 text-xs">
          <div className="font-semibold text-foreground flex items-center gap-1.5 mb-1">
            🎯 Маркетолог
          </div>
          <p className="text-[11px] text-muted-foreground">
            Создание и редактирование кампаний, настройка A/B тестов, ключевых слов и офферов.
          </p>
        </div>
        <div className="rounded-lg border p-3 bg-muted/20 text-xs">
          <div className="font-semibold text-foreground flex items-center gap-1.5 mb-1">
            📊 Аналитик
          </div>
          <p className="text-[11px] text-muted-foreground">
            Просмотр графиков, отчетов, CTR, CVR, воронки конверсий и выгрузка CSV/PDF.
          </p>
        </div>
        <div className="rounded-lg border p-3 bg-muted/20 text-xs">
          <div className="font-semibold text-foreground flex items-center gap-1.5 mb-1">
            💳 Бухгалтерия
          </div>
          <p className="text-[11px] text-muted-foreground">
            Пополнение баланса, управление счетами, выписки транзакций и финансовые отчеты.
          </p>
        </div>
      </div>

      {/* Members Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <div>
            <CardTitle className="text-sm font-semibold">Список участников</CardTitle>
            <CardDescription className="text-xs">
              Сотрудники с доступом к вашему рекламному кабинету
            </CardDescription>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={onRefresh}
            disabled={loadingTeam}
            aria-label="Обновить список участников"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loadingTeam ? 'animate-spin' : ''}`} />
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {!Array.isArray(teamMembers) || teamMembers.length === 0 ? (
            <div className="p-8 text-center text-xs text-muted-foreground">
              <Users className="h-8 w-8 mx-auto mb-2 text-muted-foreground/50" />
              У вас пока нет приглашенных участников. Вы единственный владелец кабинета.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b bg-muted/40 uppercase text-muted-foreground">
                  <tr>
                    <th className="py-2.5 px-4">Email / Участник</th>
                    <th className="py-2.5 px-4">Роль</th>
                    <th className="py-2.5 px-4">Статус</th>
                    <th className="py-2.5 px-4">Дата добавления</th>
                    <th className="py-2.5 px-4 text-right">Действия</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(teamMembers || []).map((m) => (
                    <tr key={m.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 px-4 font-medium">{m.email}</td>
                      <td className="py-3 px-4">
                        <Select
                          value={m.role}
                          onValueChange={(val) => onUpdateRole(m.id, val)}
                          disabled={updatingMemberId === m.id}
                        >
                          <SelectTrigger className="h-7 w-36 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="admin">👑 Администратор</SelectItem>
                            <SelectItem value="manager">🎯 Маркетолог</SelectItem>
                            <SelectItem value="analyst">📊 Аналитик</SelectItem>
                            <SelectItem value="billing">💳 Бухгалтерия</SelectItem>
                          </SelectContent>
                        </Select>
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant="outline"
                          className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 text-[10px]"
                        >
                          🟢 Активен
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {m.create_time ? new Date(m.create_time).toLocaleDateString() : '—'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onDeleteMember(m.id)}
                          className="text-red-500 hover:text-red-700 h-7 px-2 text-xs"
                          title="Отозвать доступ"
                          aria-label={`Отозвать доступ ${m.email}`}
                        >
                          <Trash2 className="h-3.5 w-3.5 mr-1" /> Удалить
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
    </div>
  );
};

export default TeamTab;
