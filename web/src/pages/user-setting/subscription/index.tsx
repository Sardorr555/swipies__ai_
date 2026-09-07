import { useEffect, useState } from 'react';
import Spotlight from '@/components/spotlight';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { useFetchTenantInfo, useFetchUserInfo } from '@/hooks/use-user-setting-request';
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
  Check,
  Sparkles,
  Key,
  Bot,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';
import { ProfileSettingWrapperCard } from '../components/user-setting-header';
import { Routes } from '@/routes';
import { getUserAiUsage, UserAIUsageSummary } from '@/services/ai-management-service';

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
    featuresInclude: 'What is included in your current plan:',
    allPlansTitle: 'Available Subscription Plans & Features',
    currentPlanBadge: 'Current Plan',
    selectPlan: 'Upgrade / Select',
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
    featuresInclude: 'Что входит в ваш текущий тариф:',
    allPlansTitle: 'Все доступные тарифные планы и их возможности:',
    currentPlanBadge: 'Текущий тариф',
    selectPlan: 'Перейти / Выбрать',
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
    featuresInclude: 'Joriy tarifingizga quyidagilar kiradi:',
    allPlansTitle: 'Barcha obuna tariflari va ularning imkoniyatlari:',
    currentPlanBadge: 'Joriy Tarif',
    selectPlan: 'Tanlash / Oʻtish',
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
};

const ALL_PLAN_CARDS = [
  {
    key: 'free',
    name: 'Free / Trial',
    price: 'Free',
    storage: '50 MB',
    apps: '3 Apps',
    team: '1 Member',
    credits: '100 Credits/mo',
    features: [
      '3 Agents & Chat Apps',
      '50 MB Dataset storage',
      '1 Team member',
      'Basic model support',
    ],
  },
  {
    key: 'plus',
    name: 'Plus Plan',
    price: '199,000 UZS / mo',
    storage: '5 GB',
    apps: '50 Apps',
    team: '5 Members',
    credits: '5,000 Credits/mo',
    features: [
      '50 Agents & Chat Apps',
      '5 GB Dataset storage',
      '5 Team members',
      '5,000 Credits / month',
      'Fast processing priority',
    ],
  },
  {
    key: 'pro',
    name: 'Pro Plan',
    price: '400,000 UZS / mo',
    storage: '15 GB',
    apps: 'Unlimited Apps',
    team: '15 Members',
    credits: '10,000 Credits/mo',
    popular: true,
    features: [
      'Unlimited Agents & Chat Apps',
      '15 GB Dataset storage',
      '15 Team members',
      '10,000 Credits / month',
      'Priority GPU execution & support',
    ],
  },
  {
    key: 'license',
    name: 'Self-Hosted License',
    price: 'Custom / 6–12 months',
    storage: 'Unlimited (Local)',
    apps: 'Unlimited Apps',
    team: 'Unlimited Members',
    credits: 'Unlimited',
    features: [
      'Self-hosted Docker/k8s deployment',
      'Activated via License Key',
      'Unlimited Dataset storage & team',
      'GPU & Vector DB acceleration',
      'Offline / Air-gapped environment',
    ],
  },
];

const SubscriptionPage = () => {
  const { i18n } = useTranslation();
  const navigate = useNavigate();
  const { data: userInfo } = useFetchUserInfo();
  const { data: tenantInfo, loading } = useFetchTenantInfo();
  const [aiUsage, setAiUsage] = useState<UserAIUsageSummary | null>(null);

  useEffect(() => {
    getUserAiUsage()
      .then((res) => {
        if (res && res.data) {
          setAiUsage(res.data);
        }
      })
      .catch(() => {});
  }, []);

  const currentLang = i18n.language || 'en';
  const lang = pricingTranslations[currentLang]
    ? currentLang
    : currentLang.startsWith('ru')
      ? 'ru'
      : currentLang.startsWith('uz')
        ? 'uz'
        : 'en';
  const tLocal = pricingTranslations[lang] || pricingTranslations.en;

  // Resolve plan type candidate tokens from all sources of truth
  const planCandidates = [
    tenantInfo?.plan_type,
    typeof aiUsage?.plan === 'object' ? (aiUsage?.plan?.id || aiUsage?.plan?.name) : aiUsage?.plan,
    userInfo?.is_superuser ? 'pro' : '',
  ]
    .filter(Boolean)
    .map((p) => String(p).toLowerCase());

  let planKey = 'free';
  if (planCandidates.some((p) => p.includes('enterprise'))) {
    planKey = 'enterprise';
  } else if (planCandidates.some((p) => p.includes('license'))) {
    planKey = 'license';
  } else if (planCandidates.some((p) => p.includes('pro'))) {
    planKey = 'pro';
  } else if (planCandidates.some((p) => p.includes('plus'))) {
    planKey = 'plus';
  }

  const planInfo =
    tLocal?.planDetails?.[planKey] ||
    pricingTranslations.en?.planDetails?.[planKey] || {
      name: `${planKey.toUpperCase()} Plan`,
      description: '',
    };

  const aiPlanName =
    typeof aiUsage?.plan === 'object' && aiUsage?.plan?.name
      ? aiUsage.plan.name
      : typeof aiUsage?.plan === 'string'
        ? (aiUsage.plan as string).toUpperCase()
        : planInfo?.name || 'Plus Plan';

  // Map resource limits dynamically based on plan
  const getResourceLimits = () => {
    const unlim = tLocal?.unlimited || 'Unlimited';
    const selfUnlim = tLocal?.selfHostedUnlimited || 'Self-hosted (Unlimited)';
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
          apps: unlim,
          team: '15',
          credits: '10,000',
        };
      case 'license':
        return {
          storage: selfUnlim,
          apps: unlim,
          team: unlim,
          credits: unlim,
        };
      case 'enterprise':
        return {
          storage: unlim,
          apps: unlim,
          team: unlim,
          credits: unlim,
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

  const handleUpgradeRedirect = (targetPlan?: string) => {
    if (targetPlan === 'license') {
      navigate('/user-setting/license');
    } else {
      navigate(Routes.Pricing);
    }
  };

  return (
    <ProfileSettingWrapperCard
      header={
        <header className="flex flex-col gap-1">
          <h2 className="text-2xl font-bold tracking-tight text-text-primary flex items-center gap-2">
            <CreditCard className="text-accent-primary" size={24} />
            {tLocal?.title || 'Plan & Billing'}
          </h2>
          <p className="text-text-secondary text-sm">
            {tLocal?.subtitle || 'Manage your subscription and view usage limits.'}
          </p>
        </header>
      }
    >
      <Spotlight />

      <div className="h-full overflow-x-hidden overflow-y-auto space-y-8 pb-12 pr-1">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-2">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-solid border-accent-primary border-r-transparent"></div>
            <span className="text-sm text-text-secondary">Loading subscription details...</span>
          </div>
        ) : (
          <>
            {/* Active Plan Detail Hero Card */}
            <Card className="border border-border-default bg-bg-component/40 backdrop-blur-md overflow-hidden relative shadow-md">
              <div className="absolute top-0 right-0 p-6 opacity-[0.03] pointer-events-none">
                <ShieldCheck size={180} />
              </div>
              <CardHeader className="pb-3 flex flex-row items-center justify-between">
                <div>
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/15 px-3 py-1 rounded-full border border-emerald-500/20 inline-flex items-center gap-1.5">
                    <CheckCircle size={14} /> {tLocal?.activePlan || 'Active Plan'}
                  </span>
                  <h3 className="text-3xl font-extrabold text-text-primary mt-3 flex items-center gap-2">
                    {planInfo?.name || planKey.toUpperCase()}
                  </h3>
                </div>
                <div className="text-right">
                  <span className="text-xs text-text-secondary font-medium">{tLocal?.creditBalance || 'Credits'}</span>
                  <div className="text-3xl font-extrabold text-accent-primary mt-0.5">
                    {tenantInfo?.credit !== undefined ? tenantInfo.credit.toLocaleString() : '0'}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 pt-0">
                <p className="text-text-secondary text-sm max-w-xl">
                  {planInfo?.description || ''}
                </p>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-4 border-t border-border-default">
                  <div className="flex items-center gap-2 text-sm text-text-secondary">
                    <Calendar size={16} className="text-accent-primary" />
                    <span>
                      {tLocal?.expiryDate || 'Expiry'}:{' '}
                      <span className="font-semibold text-text-primary">
                        {tenantInfo?.plan_expiry_date
                          ? formatDate(tenantInfo.plan_expiry_date)
                          : tLocal?.lifetimeAccess || 'Lifetime Access'}
                      </span>
                    </span>
                  </div>

                  <Button
                    onClick={() => handleUpgradeRedirect()}
                    className="bg-accent-primary hover:bg-accent-primary/95 text-white flex items-center gap-2 px-5 py-2.5 font-bold transition-all duration-200 shadow-md shadow-accent-primary/20"
                  >
                    {tLocal?.upgradeButton || 'Change Plan / Upgrade'}
                    <ArrowUpRight size={16} />
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Live AI Token Quota & Progress Card */}
            {aiUsage && (
              <Card className="border border-border-default bg-bg-component/30 backdrop-blur-md p-6 rounded-2xl shadow-sm space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border-default/50 pb-3">
                  <div>
                    <h4 className="text-lg font-bold text-text-primary flex items-center gap-2">
                      <Bot className="text-accent-primary" size={20} />
                      AI Monthly Token Consumption ({aiUsage?.period || ''})
                    </h4>
                    <p className="text-xs text-text-secondary">
                      Monthly token quota governed by {aiPlanName} policy. Resets monthly.
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-semibold text-text-secondary">Tokens Used</span>
                    <div className="text-xl font-extrabold text-accent-primary">
                      {((aiUsage?.total_used ?? aiUsage?.monthly_used ?? 0)).toLocaleString()} / {((aiUsage?.monthly_limit ?? 0)).toLocaleString()}
                    </div>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs font-medium">
                    <span className="text-text-secondary">Quota Progress</span>
                    <span className={(aiUsage?.percentage ?? 0) >= 90 ? 'text-rose-500 font-bold' : 'text-accent-primary font-bold'}>
                      {aiUsage?.percentage ?? 0}% Used
                    </span>
                  </div>
                  <div className="w-full h-3 bg-bg-card rounded-full overflow-hidden border border-border-default/60">
                    <div
                      className={`h-full transition-all duration-500 rounded-full ${
                        (aiUsage?.percentage ?? 0) >= 90
                          ? 'bg-gradient-to-r from-amber-500 to-rose-500'
                          : 'bg-gradient-to-r from-emerald-500 to-accent-primary'
                      }`}
                      style={{ width: `${Math.min(aiUsage?.percentage ?? 0, 100)}%` }}
                    />
                  </div>
                </div>

                {/* Model Breakdown */}
                {Array.isArray(aiUsage?.breakdown) && aiUsage.breakdown.length > 0 && (
                  <div className="pt-2">
                    <span className="text-xs font-bold text-text-secondary uppercase tracking-wider">
                      Usage Breakdown by Model
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 mt-2">
                      {aiUsage.breakdown.map((item, idx) => (
                        <div key={idx} className="p-2.5 rounded-xl border border-border-default/60 bg-bg-card/40 flex items-center justify-between text-xs">
                          <div>
                            <div className="font-semibold text-text-primary">{item?.model_id || 'Unknown'}</div>
                            <div className="text-[10px] text-text-secondary">{item?.model_type || 'Model'}</div>
                          </div>
                          <span className="font-mono font-bold text-accent-primary">
                            {(item?.tokens_used ?? 0).toLocaleString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </Card>
            )}

            {/* Plan Features / Resource Limits Title */}
            <div className="space-y-4">
              <h4 className="text-lg font-bold tracking-tight text-text-primary">
                {tLocal?.featuresInclude || 'What is included in your current plan:'}
              </h4>

              {/* Resource Limit cards grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Card 1: Storage Limit */}
                <Card className="border border-border-default bg-bg-component/25 backdrop-blur-sm transition-all duration-300 hover:border-accent-primary/45">
                  <CardContent className="p-5 flex items-center justify-between">
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-text-secondary uppercase tracking-wider">
                        {tLocal?.resources?.storage || 'Dataset Storage'}
                      </p>
                      <p className="text-2xl font-extrabold text-text-primary tracking-tight">
                        {limits?.storage || '50 MB'}
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
                        {tLocal?.resources?.apps || 'Agents & Apps'}
                      </p>
                      <p className="text-2xl font-extrabold text-text-primary tracking-tight">
                        {limits?.apps || '3'}
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
                        {tLocal?.resources?.team || 'Team Members'}
                      </p>
                      <p className="text-2xl font-extrabold text-text-primary tracking-tight">
                        {limits?.team || '1'}
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
                        {tLocal?.resources?.credits || 'Monthly Credits'}
                      </p>
                      <p className="text-2xl font-extrabold text-text-primary tracking-tight">
                        {limits?.credits || '100'}
                      </p>
                    </div>
                    <div className="p-3 bg-accent-primary/10 rounded-xl text-accent-primary">
                      <Zap size={22} />
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>

            <hr className="border-border-default/60 my-6" />

            {/* SECTION: ALL SUBSCRIPTION PLANS COMPARISON */}
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xl font-bold tracking-tight text-text-primary flex items-center gap-2">
                    <Sparkles className="text-accent-primary" size={22} />
                    {tLocal?.allPlansTitle || 'All Subscription Plans'}
                  </h4>
                  <p className="text-xs text-text-secondary mt-1">
                    Compare features across all Swipies AI subscription tiers.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 items-stretch">
                {ALL_PLAN_CARDS.map((card) => {
                  const isCurrent = planKey === card.key;

                  return (
                    <div
                      key={card.key}
                      className={`rounded-2xl border p-5 flex flex-col justify-between transition-all relative ${
                        isCurrent
                          ? 'border-emerald-500/50 bg-emerald-500/5 ring-1 ring-emerald-500/30'
                          : card.popular
                          ? 'border-accent-primary bg-accent-primary/5 ring-1 ring-accent-primary/30'
                          : 'border-border-default bg-bg-card/20 hover:border-accent-primary/40'
                      }`}
                    >
                      {card.popular && !isCurrent && (
                        <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-accent-primary text-white text-[10px] font-bold px-2.5 py-0.5 rounded-full shadow-sm uppercase tracking-wider">
                          Most Popular
                        </span>
                      )}

                      <div className="space-y-4">
                        <div>
                          <h5 className="font-extrabold text-base text-text-primary">{card.name}</h5>
                          <div className="text-lg font-bold text-accent-primary mt-1">{card.price}</div>
                        </div>

                        <ul className="space-y-2 border-t border-border-default/50 pt-3">
                          {card.features.map((feat, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-xs text-text-secondary">
                              <Check size={14} className="text-emerald-400 shrink-0 mt-0.5" />
                              <span>{feat}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div className="pt-6 mt-auto">
                        {isCurrent ? (
                          <div className="w-full bg-emerald-500/20 text-emerald-400 font-bold py-2 rounded-xl text-xs text-center border border-emerald-500/30 flex items-center justify-center gap-1.5">
                            <CheckCircle size={14} />
                            {tLocal?.currentPlanBadge || 'Current Plan'}
                          </div>
                        ) : (
                          <Button
                            onClick={() => handleUpgradeRedirect(card.key)}
                            variant={card.popular ? 'default' : 'outline'}
                            className={`w-full text-xs font-bold py-2 rounded-xl ${
                              card.popular
                                ? 'bg-accent-primary hover:bg-accent-primary/90 text-white'
                                : 'border-border-default text-text-primary hover:border-accent-primary/50'
                            }`}
                          >
                            {card.key === 'license' ? (
                              <span className="flex items-center gap-1.5">
                                <Key size={14} /> License Keys
                              </span>
                            ) : (
                              tLocal?.selectPlan || 'Select Plan'
                            )}
                          </Button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Extra information banner */}
            <div className="p-4 rounded-xl border border-accent-primary/20 bg-accent-primary/5 flex items-start gap-3 mt-6">
              <HelpCircle className="text-accent-primary shrink-0 mt-0.5" size={18} />
              <p className="text-xs text-text-secondary leading-relaxed">
                {tLocal?.pricingRedirectTip || 'To change or upgrade your plan, visit our Pricing page.'}
              </p>
            </div>
          </>
        )}
      </div>
    </ProfileSettingWrapperCard>
  );
};

export default SubscriptionPage;
