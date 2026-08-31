declare namespace AdminService {
  export type LoginData = {
    access_token: string;
    avatar: unknown;
    color_schema: 'Bright' | 'Dark';
    create_date: string;
    create_time: number;
    email: string;
    id: string;
    is_active: '0' | '1';
    is_anonymous: '0' | '1';
    is_authenticated: '0' | '1';
    is_superuser: boolean;
    language: string;
    last_login_time: string;
    login_channel: unknown;
    nickname: string;
    password: string;
    status: '0' | '1';
    timezone: string;
    update_date: [string];
    update_time: [number];
  };

  export type ListUsersItem = {
    id?: string;
    create_date: string;
    email: string;
    is_active: '0' | '1';
    is_superuser: boolean;
    role: string;
    nickname: string;
    referred_by_id?: string;
    referred_by_email?: string;
    referrals_count?: number;
  };

  export type UserDetail = {
    id?: string;
    avatar?: string;
    create_date: string;
    email: string;
    nickname?: string;
    phone?: string;
    is_active: '0' | '1';
    is_anonymous: '0' | '1';
    is_superuser: boolean;
    language: string;
    last_login_time: string;
    login_channel: unknown;
    status: '0' | '1';
    update_date: string;
    role: string;
    plan_type?: string;
    plan_expiry_date?: string | null;
    credit?: number;
    referred_by_id?: string;
    referred_by_email?: string;
    referrals_count?: number;
  };

  export type ListUserDatasetItem = {
    avatar?: string;
    chunk_num: number;
    create_date: string;
    doc_num: number;
    language: string;
    name: string;
    permission: string;
    status: '0' | '1';
    token_num: number;
    update_date: string;
  };

  export type ListUserAgentItem = {
    avatar?: string;
    canvas_category: 'agent';
    permission: 'string';
    title: string;
  };

  export type TaskExecutorHeartbeatItem = {
    name: string;
    boot_at: string;
    now: string;
    ip_address: string;
    current: Record<string, object>;
    done: number;
    failed: number;
    lag: number;
    pending: number;
    pid: number;
  };

  export type TaskExecutorInfo = Record<string, TaskExecutorHeartbeatItem[]>;

  export type ListServicesItem = {
    extra: Record<string, unknown>;
    host: string;
    id: number;
    name: string;
    port: number;
    service_type: string;
    status: 'alive' | 'timeout' | 'fail';
  };

  export type ServiceDetail =
    | {
        service_name: string;
        status: 'alive' | 'timeout';
        message: string | Record<string, any> | Record<string, any>[];
      }
    | {
        service_name: 'task_executor';
        status: 'alive' | 'timeout';
        message: AdminService.TaskExecutorInfo;
      };

  export type PermissionData = {
    enable: boolean;
    read: boolean;
    write: boolean;
    share: boolean;
  };

  export type ListRoleItem = {
    id: string;
    role_name: string;
    description: string;
    create_date: string;
    update_date: string;
  };

  export type ListRoleItemWithPermission = ListRoleItem & {
    permissions: Record<string, PermissionData>;
  };

  export type RoleDetailWithPermission = {
    role: {
      id: string;
      name: string;
      description: string;
    };
    permissions: Record<string, PermissionData>;
  };

  export type RoleDetail = {
    id: string;
    name: string;
    description: string;
    create_date: string;
    update_date: string;
  };

  export type AssignRolePermissionsInput = Record<
    string,
    Partial<PermissionData>
  >;
  export type RevokeRolePermissionInput = AssignRolePermissionsInput;

  export type UserDetailWithPermission = {
    user: {
      id: string;
      username: string;
      role: string;
    };
    role_permissions: Record<string, PermissionData>;
  };

  export type ResourceType = {
    resource_types: string[];
  };

  export type ListWhitelistItem = {
    id: number;
    email: string;
    create_date: string;
    create_time: number;
    update_date: string;
    update_time: number;
  };

  // Sandbox settings types
  export type SandboxProvider = {
    id: string;
    name: string;
    description: string;
    tags: string[];
  };

  export type SandboxConfigFieldBase = {
    required?: boolean;
    label?: string;
    placeholder?: string;
    description?: string;
    multiline?: boolean;
    readonly?: boolean;
    scope?: 'runtime' | 'deployment';
  };

  export type SandboxConfigStringField = SandboxConfigFieldBase & {
    type: 'string';
    default?: string;
    secret?: boolean;
  };

  export type SandboxConfigIntegerField = SandboxConfigFieldBase & {
    type: 'integer';
    default?: number;
    min?: number;
    max?: number;
  };

  export type SandboxConfigBooleanField = SandboxConfigFieldBase & {
    type: 'boolean';
    default?: boolean;
  };

  export type SandboxConfigJsonField = SandboxConfigFieldBase & {
    type: 'json';
    default?: unknown;
  };

  export type SandboxConfigField =
    | SandboxConfigStringField
    | SandboxConfigIntegerField
    | SandboxConfigBooleanField
    | SandboxConfigJsonField;

  export type SandboxConfig = {
    provider_type: string;
    config: Record<string, unknown>;
  };

  export type PaymentTransactionItem = {
    id: string;
    transaction_id: string;
    user_id: string;
    tenant_id: string;
    account_email: string;
    plan_type: string;
    duration_months: number;
    expected_amount_uzs: number;
    paid_amount_uzs: number | null;
    currency: string;
    payment_method: string;
    status: 'PAID' | 'PENDING' | 'FAILED' | 'REQUIRES_AUDIT' | 'EXPIRED' | 'CANCELLED';
    error_code?: string | null;
    error_message?: string | null;
    is_provisioned: boolean;
    audit_note?: string | null;
    create_date: string;
    update_date: string;
  };

  export type PaymentAnalyticsSummary = {
    total_revenue_uzs: number;
    mrr_uzs: number;
    total_initiated_count: number;
    paid_transactions_count: number;
    conversion_rate_pct: number;
    plan_breakdown: Record<string, { count: number; total_paid_uzs: number }>;
    status_distribution: Record<string, number>;
  };
}
