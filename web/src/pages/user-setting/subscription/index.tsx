import Spotlight from '@/components/spotlight';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { useFetchTenantInfo } from '@/hooks/use-user-setting-request';
import { formatDate } from '@/utils/date';
import {
  ArrowUpRight,
  Calendar,
  CheckCircle,
  Cpu,
  CreditCard,
  HardDrive,
  HelpCircle,
  ShieldCheck,
  Users,
  Zap,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';
import { ProfileSettingWrapperCard } from '../components/user-setting-header';
import { Routes } from '@/routes';

const pricingTranslations: Record<string, any> = {
  en: {
    title: 'Subscription & Billing',
    subtitle: 'Manage your plan, check resource utilization limits, and view credits.',
    activePlan: 'Active Plan',
    creditBalance: 'Credit Balance',
    expiryDate: 'Expiry Date',
    lifetimeAccess: 'Lifetime Access',
    upgradeButton: 'Change Plan / Upgrade',
    pricingRedirectTip: 'Want to view other pricing options or billing details? Go to the Pricing page.',
    featuresInclude: 'What is included in your plan:',
    statusActive: 'Active',
    resources: {
      storage: 'Dataset Storage',
      apps: 'Agents & Chat Apps',
      team: 'Team Members',
      credits: 'Monthly Credits',
    },
    unlimited: 'Unlimited',
    selfHostedUnlimited: 'Self-hosted (Unlimited)',
    planDetails: {
      free: {
        name: 'Free / Trial',
        description: 'For personal and trial usage',
      },
      plus: {
        name: 'Plus Plan',
        description: 'For active individual users',
      },
      pro: {
        name: 'Pro Plan',
        description: 'For professionals and small teams',
      },
      license: {
        name: 'Self-Hosted License',
        description: 'Run Swipies on your own infrastructure',
      },
      enterprise: {
        name: 'Enterprise Plan',
        description: 'Custom plan tailored for organizations',
      },
    },
  },
  ru: {
    title: 'Подписка и Оплата',
    subtitle: 'Управляйте вашим тарифом, проверяйте лимиты ресурсов и баланс кредитов.',
    activePlan: 'Активный тариф',
    creditBalance: 'Баланс кредитов',
    expiryDate: 'Срок действия',
    lifetimeAccess: 'Бессрочный доступ',
    upgradeButton: 'Изменить тариф / Обновить',
    pricingRedirectTip: 'Хотите посмотреть другие тарифы или детали оплаты? Перейдите на страницу тарифов.',
    featuresInclude: 'Что входит в ваш тариф:',
    statusActive: 'Активен',
    resources: {
      storage: 'Хранилище данных',
      apps: 'Агенты и чат-приложения',
      team: 'Участники команды',
      credits: 'Месячные кредиты',
    },
    unlimited: 'Без лимита',
    selfHostedUnlimited: 'Локальное хранилище (Без лимита)',
    planDetails: {
      free: {
        name: 'Бесплатный / Пробный',
        description: 'Для личного использования и тестирования',
      },
      plus: {
        name: 'Тариф Plus',
        description: 'Для активных индивидуальных пользователей',
      },
      pro: {
        name: 'Тариф Pro',
        description: 'Для профессионалов и небольших команд',
      },
      license: {
        name: 'Self-Hosted лицензия',
        description: 'Запуск Swipies на вашей собственной инфраструктуре',
      },
      enterprise: {
        name: 'Тариф Enterprise',
        description: 'Индивидуальное решение для организаций',
      },
    },
  },
  uz: {
    title: 'Obuna va Toʻlov',
    subtitle: 'Tarifingizni boshqaring, resurslar limitlari va kreditlar qoldig‘ini tekshiring.',
    activePlan: 'Faol Tarif',
    creditBalance: 'Kreditlar Balansi',
    expiryDate: 'Amal Qilish Muddati',
    lifetimeAccess: 'Cheksiz Kirish',
    upgradeButton: 'Tarifni Oʻzgartirish / Yangilash',
    pricingRedirectTip: 'Boshqa tariflar yoki toʻlov tafsilotlarini koʻrmoqchimisiz? Tariflar sahifasiga oʻting.',
    featuresInclude: 'Tarifingizga quyidagilar kiradi:',
    statusActive: 'Faol',
    resources: {
      storage: 'Dataset xotirasi',
      apps: 'Agentlar va suhbat ilovalari',
      team: 'Jamoa a’zolari',
      credits: 'Oylik kreditlar',
    },
    unlimited: 'Cheksiz',
    selfHostedUnlimited: 'Lokal xotira (Cheksiz)',
    planDetails: {
      free: {
        name: 'Bepul / Sinov',
        description: 'Shaxsiy va sinov tariqasida foydalanish uchun',
      },
      plus: {
        name: 'Plus Tarifi',
        description: 'Faol yakka tartibdagi foydalanuvchilar uchun',
      },
      pro: {
        name: 'Pro Tarifi',
        description: 'Mutaxassislar va kichik jamoalar uchun',
      },
      license: {
        name: 'Self-Hosted Litsenziya',
        description: 'Swipies dasturini shaxsiy infratuzilmangizda ishlating',
      },
      enterprise: {
        name: 'Enterprise Tarifi',
        description: 'Tashkilotlar uchun maxsus moslashtirilgan tarif',
      },
    },
  },
  zh: {
    title: '订阅与计费',
    subtitle: '管理您的订阅计划，查看资源使用额度及信用点余额。',
    activePlan: '当前计划',
    creditBalance: '信用额度余额',
    expiryDate: '到期时间',
    lifetimeAccess: '永久有效',
    upgradeButton: '更改计划 / 升级',
    pricingRedirectTip: '想要查看其他定价方案或账单详情？请前往定价页面。',
    featuresInclude: '您的计划包含以下权益：',
    statusActive: '生效中',
    resources: {
      storage: '知识库存储空间',
      apps: '智能体及聊天应用数',
      team: '团队成员数',
      credits: '每月信用额度',
    },
    unlimited: '无限制',
    selfHostedUnlimited: '本地部署（无限制）',
    planDetails: {
      free: {
        name: '免费版 / 试用',
        description: '个人使用与功能试用',
      },
      plus: {
        name: 'Plus 计划',
        description: '适合活跃的个人用户',
      },
      pro: {
        name: 'Pro 计划',
        description: '适合专业人士与小型团队',
      },
      license: {
        name: '企业授权版 (Self-Hosted)',
        description: '在您自己的基础设施上部署和运行 Swipies',
      },
      enterprise: {
        name: '企业定制版',
        description: '为大中型组织量身定制的专属方案',
      },
    },
  },
};

const SubscriptionPage = () => {
  const { i18n } = useTranslation();
  const navigate = useNavigate();
  const { data: tenantInfo, loading } = useFetchTenantInfo();

  const lang = pricingTranslations[i18n.language] ? i18n.language : 'en';
  const tLocal = pricingTranslations[lang];

  // Helper to extract plan type
  const rawPlan = (tenantInfo?.plan_type || 'free').toLowerCase();
  let planKey = 'free';
  if (rawPlan.includes('plus')) planKey = 'plus';
  else if (rawPlan.includes('pro')) planKey = 'pro';
  else if (rawPlan.includes('license')) planKey = 'license';
  else if (rawPlan.includes('enterprise')) planKey = 'enterprise';

  const planInfo = tLocal.planDetails[planKey];

  // Map resource limits dynamically based on plan
  const getResourceLimits = () => {
    switch (planKey) {
      case 'plus':
        return {
          storage: '5 GB',
          apps: '50',
          team: '5',
          credits: '5,000',
        };
      case 'pro':
        return {
          storage: '15 GB',
          apps: tLocal.unlimited,
          team: '15',
          credits: '10,000',
        };
      case 'license':
        return {
          storage: tLocal.selfHostedUnlimited,
          apps: tLocal.unlimited,
          team: tLocal.unlimited,
          credits: tLocal.unlimited,
        };
      case 'enterprise':
        return {
          storage: tLocal.unlimited,
          apps: tLocal.unlimited,
          team: tLocal.unlimited,
          credits: tLocal.unlimited,
        };
      default:
        return {
          storage: '50 MB',
          apps: '3',
          team: '1',
          credits: '100',
        };
    }
  };

  const limits = getResourceLimits();

  const handleUpgradeRedirect = () => {
    navigate(Routes.Pricing);
  };

  return (
    <ProfileSettingWrapperCard
      header={
        <header className="flex flex-col gap-1">
          <h2 className="text-2xl font-bold tracking-tight text-text-primary flex items-center gap-2">
            <CreditCard className="text-accent-primary" size={24} />
            {tLocal.title}
          </h2>
          <p className="text-text-secondary text-sm">
            {tLocal.subtitle}
          </p>
        </header>
      }
    >
      <Spotlight />

      <div className="h-full overflow-x-hidden overflow-y-auto space-y-6 pb-8 pr-1">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-2">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-solid border-accent-primary border-r-transparent"></div>
            <span className="text-sm text-text-secondary">Loading subscription details...</span>
          </div>
        ) : (
          <>
            {/* Active Plan Detail Hero Card */}
            <Card className="border border-border-default bg-bg-component/40 backdrop-blur-md overflow-hidden relative">
              <div className="absolute top-0 right-0 p-6 opacity-[0.03] pointer-events-none">
                <ShieldCheck size={180} />
              </div>
              <CardHeader className="pb-3 flex flex-row items-center justify-between">
                <div>
                  <span className="text-xs font-semibold uppercase tracking-wider text-accent-primary bg-accent-primary/10 px-2.5 py-1 rounded-full">
                    {tLocal.activePlan}
                  </span>
                  <h3 className="text-2xl font-extrabold text-text-primary mt-2 flex items-center gap-2">
                    {planInfo.name}
                    <CheckCircle className="text-emerald-500 shrink-0" size={20} />
                  </h3>
                </div>
                <div className="text-right">
                  <span className="text-xs text-text-secondary">{tLocal.creditBalance}</span>
                  <div className="text-2xl font-extrabold text-text-primary">
                    {tenantInfo?.credit !== undefined ? tenantInfo.credit.toLocaleString() : '0'}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 pt-0">
                <p className="text-text-secondary text-sm max-w-xl">
                  {planInfo.description}
                </p>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-4 border-t border-border-default">
                  <div className="flex items-center gap-2 text-sm text-text-secondary">
                    <Calendar size={16} className="text-accent-primary" />
                    <span>
                      {tLocal.expiryDate}:{' '}
                      <span className="font-semibold text-text-primary">
                        {tenantInfo?.plan_expiry_date
                          ? formatDate(tenantInfo.plan_expiry_date)
                          : tLocal.lifetimeAccess}
                      </span>
                    </span>
                  </div>

                  <Button
                    onClick={handleUpgradeRedirect}
                    className="bg-accent-primary hover:bg-accent-primary/95 text-white flex items-center gap-2 px-5 py-2 font-medium transition-all duration-200"
                  >
                    {tLocal.upgradeButton}
                    <ArrowUpRight size={16} />
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Plan Features / Resource Limits Title */}
            <h4 className="text-lg font-bold tracking-tight text-text-primary pt-2">
              {tLocal.featuresInclude}
            </h4>

            {/* Resource Limit cards grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Card 1: Storage Limit */}
              <Card className="border border-border-default bg-bg-component/25 backdrop-blur-sm transition-all duration-300 hover:border-accent-primary/45">
                <CardContent className="p-5 flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-text-secondary uppercase tracking-wider">
                      {tLocal.resources.storage}
                    </p>
                    <p className="text-2xl font-extrabold text-text-primary tracking-tight">
                      {limits.storage}
                    </p>
                  </div>
                  <div className="p-3 bg-accent-primary/10 rounded-xl text-accent-primary">
                    <HardDrive size={22} />
                  </div>
                </CardContent>
              </Card>

              {/* Card 2: Agent/App Limit */}
              <Card className="border border-border-default bg-bg-component/25 backdrop-blur-sm transition-all duration-300 hover:border-accent-primary/45">
                <CardContent className="p-5 flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-text-secondary uppercase tracking-wider">
                      {tLocal.resources.apps}
                    </p>
                    <p className="text-2xl font-extrabold text-text-primary tracking-tight">
                      {limits.apps}
                    </p>
                  </div>
                  <div className="p-3 bg-accent-primary/10 rounded-xl text-accent-primary">
                    <Cpu size={22} />
                  </div>
                </CardContent>
              </Card>

              {/* Card 3: Team Limit */}
              <Card className="border border-border-default bg-bg-component/25 backdrop-blur-sm transition-all duration-300 hover:border-accent-primary/45">
                <CardContent className="p-5 flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-text-secondary uppercase tracking-wider">
                      {tLocal.resources.team}
                    </p>
                    <p className="text-2xl font-extrabold text-text-primary tracking-tight">
                      {limits.team}
                    </p>
                  </div>
                  <div className="p-3 bg-accent-primary/10 rounded-xl text-accent-primary">
                    <Users size={22} />
                  </div>
                </CardContent>
              </Card>

              {/* Card 4: Credits/month */}
              <Card className="border border-border-default bg-bg-component/25 backdrop-blur-sm transition-all duration-300 hover:border-accent-primary/45">
                <CardContent className="p-5 flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-text-secondary uppercase tracking-wider">
                      {tLocal.resources.credits}
                    </p>
                    <p className="text-2xl font-extrabold text-text-primary tracking-tight">
                      {limits.credits}
                    </p>
                  </div>
                  <div className="p-3 bg-accent-primary/10 rounded-xl text-accent-primary">
                    <Zap size={22} />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Extra information banner */}
            <div className="p-4 rounded-xl border border-accent-primary/20 bg-accent-primary/5 flex items-start gap-3 mt-6">
              <HelpCircle className="text-accent-primary shrink-0 mt-0.5" size={18} />
              <p className="text-xs text-text-secondary leading-relaxed">
                {tLocal.pricingRedirectTip}
              </p>
            </div>
          </>
        )}
      </div>
    </ProfileSettingWrapperCard>
  );
};

export default SubscriptionPage;
