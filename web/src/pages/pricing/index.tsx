import { Button } from '@/components/ui/button';
import { BRAND } from '@/constants/branding';
import { useSystemConfig } from '@/hooks/use-system-request';
import { useFetchUserInfo, useFetchTenantInfo } from '@/hooks/use-user-setting-request';
import { Routes } from '@/routes';
import {
  CheckCircle,
  CreditCard,
  Gift,
  Loader2,
  LucideArrowLeft,
  LucideCheck,
  LucideZap,
  ShieldCheck,
} from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams, useNavigate } from 'react-router';

// UZS Formatter
const formatUZS = (amount: number) => {
  return new Intl.NumberFormat('uz-UZ', {
    style: 'currency',
    currency: 'UZS',
    maximumFractionDigits: 0,
  }).format(amount);
};

// Fallback UUID generator
const generateUUID = () => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

const safeFetchJson = async (url: string, options?: RequestInit) => {
  let res: Response;
  try {
    res = await fetch(url, options);
  } catch (err: any) {
    throw new Error(`Не удалось подключиться к серверу (${err.message || 'Network Error'}). Проверьте подключение.`);
  }

  const text = await res.text();
  let data: any = null;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    if (!res.ok) {
      if (res.status === 502 || res.status === 503 || res.status === 504) {
        throw new Error(`Платежный шлюз временно перезапускается (Код ${res.status}). Сервис автоматически восстанавливается, повторите попытку через несколько секунд.`);
      }
      throw new Error(`Ошибка сервиса оплаты (${res.status}): ${text.slice(0, 120)}`);
    }
  }

  if (!res.ok) {
    const errorMsg = data?.error || data?.detail || data?.result?.description || data?.message;
    if (errorMsg) {
      throw new Error(errorMsg);
    }
    throw new Error(`Ошибка запроса к платежному шлюзу (${res.status})`);
  }
  return data;
};

const pricingTranslations = {
  en: {
    backToDashboard: 'Back to dashboard',
    title: 'AI Subscription Plans',
    subtitle:
      'Choose the subscription that fits your workload. Pay securely via card using our local and international gateways.',
    oneMonth: '1 Month',
    sixMonths: '6 Months',
    oneYear: '12 Months',
    mo: '/mo',
    billedTotal: 'Billed as {{total}} for {{months}} months',
    customPricing: 'Custom Pricing',
    popularBadge: 'Most Popular',
    secureFooter:
      'All payments are secured and processed via Atmos payment gateway. You can modify or cancel your subscription at any time.',
    checkoutTitle: 'Pay via Atmos',
    checkoutSubtitle: 'Uzcard, Humo, Visa or Mastercard',
    checkoutPlan: 'Plan',
    checkoutTotal: 'Total price',
    cardNumber: 'Card Number',
    expiryDate: 'Expiry Date',
    cvc: 'CVC',
    cardholderName: 'Cardholder Name',
    processing: 'Processing...',
    payNow: 'Pay Now',
    otpTitle: 'Confirm Payment',
    otpSubtitle:
      'An SMS with a 6-digit verification code was sent to your phone',
    verifying: 'Verifying...',
    confirmOtp: 'Confirm OTP',
    cancelUseAnother: 'Cancel and use another card',
    paymentSuccessful: 'Payment Successful!',
    successSubtitle: 'Your transaction has been processed securely.',
    subActivated: 'Subscription Activated',
    subDelayed:
      'Payment was completed successfully, but there was an activation delay. Please contact support.',
    continueToSwipies: 'Continue to Swipies',
    protectedByAtmos: 'Protected by Atmos Secure',
    plans: {
      plus: {
        name: 'Plus',
        description: 'For active users',
        features: [
          '50 Apps (Chats & Agents)',
          '5 Team members',
          '5 GB Dataset storage',
          '5,000 Credits / month',
        ],
        cta: 'Choose Plus',
      },
      pro: {
        name: 'Pro',
        description: 'For professionals and teams',
        features: [
          'Unlimited Apps',
          '15 Team members',
          '15 GB Dataset storage',
          '10,000 Credits / month',
        ],
        cta: 'Choose Pro',
      },
      enterprise: {
        name: 'Enterprise',
        description: 'For organizations with advanced needs',
        features: [
          'Unlimited Knowledge Bases & Apps',
          'Unlimited Storage & Team members',
          'Dedicated Server / On-Premise',
          'Maximum Security & SLA',
          'Dedicated Account Manager',
          'Custom Integrations',
        ],
        cta: 'Contact Us',
      },
      license: {
        name: 'Self-Hosted License',
        description: 'Run Swipies AI on your own infrastructure',
        features: [
          'Self-hosted (Docker/k8s) deployment',
          'Activate via license key',
          'No ingestion or team limits',
          'GPU & Vector database acceleration',
          'Offline / Air-gapped environment support',
          'Regular security and feature updates',
        ],
        cta: 'Purchase Key',
      },
    },
    referralTitle: 'Want to expand your limits for free?',
    referralSubtitle:
      'Invite friends to Swipies and get +1 GB storage and +5 agents/apps for each referral!',
    referralButton: 'Get Referral Link',
    activePlanBadge: 'Your Active Plan',
    activePlanExpiry: 'Expires on {{date}}',
    activePlanLifetime: 'Lifetime access',
  },
  ru: {
    backToDashboard: 'Назад на главную',
    title: 'Планы подписки AI',
    subtitle:
      'Выберите подписку, соответствующую вашей нагрузке. Безопасная оплата картой через местные и международные шлюзы.',
    oneMonth: '1 месяц',
    sixMonths: '6 месяцев',
    oneYear: '12 месяцев',
    mo: '/мес',
    billedTotal: 'Всего: {{total}} за {{months}} мес.',
    customPricing: 'Индивидуальная цена',
    popularBadge: 'Самый популярный',
    secureFooter:
      'Все платежи защищены и обрабатываются через платежный шлюз Atmos. Вы можете изменить или отменить подписку в любое время.',
    checkoutTitle: 'Оплата через Atmos',
    checkoutSubtitle: 'Uzcard, Humo, Visa или Mastercard',
    checkoutPlan: 'Тариф',
    checkoutTotal: 'Итого к оплате',
    cardNumber: 'Номер карты',
    expiryDate: 'Срок действия',
    cvc: 'CVC',
    cardholderName: 'Имя держателя карты',
    processing: 'Обработка...',
    payNow: 'Оплатить сейчас',
    otpTitle: 'Подтверждение платежа',
    otpSubtitle:
      'SMS с 6-значным кодом подтверждения отправлено на ваш телефон',
    verifying: 'Проверка...',
    confirmOtp: 'Подтвердить код',
    cancelUseAnother: 'Отмена и другая карта',
    paymentSuccessful: 'Оплата прошла успешно!',
    successSubtitle: 'Ваша транзакция была безопасно обработана.',
    subActivated: 'Подписка активирована',
    subDelayed:
      'Платеж успешно завершен, но произошла задержка активации. Пожалуйста, свяжитесь с поддержкой.',
    continueToSwipies: 'Продолжить в Swipies',
    protectedByAtmos: 'Защищено Atmos Secure',
    plans: {
      plus: {
        name: 'Plus',
        description: 'Для активных пользователей',
        features: [
          '50 приложений (чаты и агенты)',
          '5 участников команды',
          '5 ГБ хранилища данных',
          '5 000 кредитов в месяц',
        ],
        cta: 'Выбрать Plus',
      },
      pro: {
        name: 'Pro',
        description: 'Для профессионалов и команд',
        features: [
          'Безлимитные приложения',
          '15 участников команды',
          '15 ГБ хранилища данных',
          '10 000 кредитов в месяц',
        ],
        cta: 'Выбрать Pro',
      },
      enterprise: {
        name: 'Enterprise',
        description: 'Для организаций с особыми потребностями',
        features: [
          'Безлимитные приложения и базы знаний',
          'Безлимитное хранилище и участники',
          'Выделенный сервер / On-Premise',
          'Максимальная безопасность и SLA',
          'Персональный менеджер',
          'Кастомные интеграции',
        ],
        cta: 'Связаться с нами',
      },
      license: {
        name: 'Self-Hosted License',
        description: 'Запуск Swipies AI на вашей собственной инфраструктуре',
        features: [
          'Локальное развертывание (Docker/k8s)',
          'Активация по лицензионному ключу',
          'Нет ограничений на загрузку и команду',
          'Ускорение графического процессора и векторной базы данных',
          'Работа в закрытом контуре / Офлайн-режим',
          'Регулярные обновления безопасности и функций',
        ],
        cta: 'Купить ключ',
      },
    },
    referralTitle: 'Хотите бесплатно расширить свои лимиты?',
    referralSubtitle:
      'Приглашайте друзей в Swipies и получайте +1 ГБ диска и +5 агентов/приложений за каждого!',
    referralButton: 'Получить реферальную ссылку',
    activePlanBadge: 'Ваш активный тариф',
    activePlanExpiry: 'Истекает {{date}}',
    activePlanLifetime: 'Бессрочный доступ',
  },
  uz: {
    backToDashboard: 'Boshqaruv paneliga qaytish',
    title: 'AI obuna rejalari',
    subtitle:
      'Ish yukingizga mos keladigan obunani tanlang. Mahalliy va xalqaro toʻlov tizimlari orqali karta bilan xavfsiz toʻlang.',
    oneMonth: '1 oy',
    sixMonths: '6 oy',
    oneYear: '12 oy',
    mo: '/oy',
    billedTotal: 'Jami: {{total}} {{months}} oy uchun',
    customPricing: 'Maxsus narxlar',
    popularBadge: 'Eng ommabop',
    secureFooter:
      'Barcha toʻlovlar xavfsiz va Atmos toʻlov shlyuzi orqali amalga oshiriladi. Obunangizni istalgan vaqtda oʻzgartirishingiz yoki bekor qilishingiz mumkin.',
    checkoutTitle: 'Atmos orqali toʻlash',
    checkoutSubtitle: 'Uzcard, Humo, Visa yoki Mastercard',
    checkoutPlan: 'Tarif',
    checkoutTotal: 'Jami toʻlov',
    cardNumber: 'Karta raqami',
    expiryDate: 'Amal qilish muddati',
    cvc: 'CVC',
    cardholderName: 'Karta egasining ismi',
    processing: 'Jarayonda...',
    payNow: 'Hozir toʻlash',
    otpTitle: 'Toʻlovni tasdiqlash',
    otpSubtitle:
      'Telefoningizga 6 xonali tasdiqlash kodi yozilgan SMS yuborildi',
    verifying: 'Tasdiqlanmoqda...',
    confirmOtp: 'OTP kodini tasdiqlash',
    cancelUseAnother: 'Bekor qilish va boshqa karta',
    paymentSuccessful: 'Toʻlov muvaffaqiyatli bajarildi!',
    successSubtitle: 'Tranzaksiyangiz xavfsiz tarzda amalga oshirildi.',
    subActivated: 'Obuna faollashtirildi',
    subDelayed:
      'Toʻlov muvaffaqiyatli yakunlandi, ammo faollashtirishda kechikish yuz berdi. Iltimos, qoʻllab-quvvatlash xizmatiga murojaat qiling.',
    continueToSwipies: 'Swipies-da davom etish',
    protectedByAtmos: 'Atmos Secure himoyasi ostida',
    plans: {
      plus: {
        name: 'Plus',
        description: 'Faol foydalanuvchilar uchun',
        features: [
          '50 ta ilova (chatlar va agentlar)',
          "5 ta jamoa a'zosi",
          "5 GB ma'lumotlar ombori",
          'Oyiga 5 000 kredit',
        ],
        cta: 'Plus-ni tanlang',
      },
      pro: {
        name: 'Pro',
        description: 'Professionallar va jamoalar uchun',
        features: [
          'Cheksiz ilovalar',
          "15 ta jamoa a'zosi",
          "15 GB ma'lumotlar ombori",
          'Oyiga 10 000 kredit',
        ],
        cta: 'Pro-ni tanlang',
      },
      enterprise: {
        name: 'Enterprise',
        description: 'Kengaytirilgan ehtiyojlarga ega tashkilotlar uchun',
        features: [
          'Cheksiz ilovalar va bilimlar bazalari',
          "Cheksiz jamoa a'zolari va saqlash joyi",
          'Maxsus server / On-Premise',
          'Maksimal xavfsizlik va SLA',
          'Shaxsiy menejer',
          'Maxsus integratsiyalar',
        ],
        cta: 'Biz bilan bogʻlaning',
      },
      license: {
        name: 'Self-Hosted License',
        description: "Swipies AI-ni o'zingizning infratuzilmangizda ishga tushiring",
        features: [
          'Mahalliy joylashtirish (Docker/k8s)',
          'Litsenziya kaliti orqali faollashtirish',
          "Yuklash va jamoa a'zolariga cheklovlar yo'q",
          'Grafik protsessor va vektor bazasi tezlashuvi',
          'Yopiq tarmoqda ishlash / Oflayn rejim',
          'Muntazam xavfsizlik va yangilanishlar',
        ],
        cta: 'Kalitni sotib olish',
      },
    },
    referralTitle: 'Limitlaringizni bepul kengaytirmoqchimisiz?',
    referralSubtitle:
      'Do‘stlaringizni Swipies-ga taklif qiling va har bir referal uchun +1 GB xotira va +5 ta agent/ilova oling!',
    referralButton: 'Referal havolasini olish',
    activePlanBadge: 'Sizning faol tarifingiz',
    activePlanExpiry: 'Amal qilish muddati: {{date}}',
    activePlanLifetime: 'Muddatsiz kirish',
  },
  zh: {
    backToDashboard: '返回仪表板',
    title: 'AI 订阅计划',
    subtitle:
      '选择适合您工作负载的订阅。通过我们的本地 and 国际网关使用卡安全支付。',
    oneMonth: '1个月',
    sixMonths: '6个月',
    oneYear: '12个月',
    mo: '/月',
    billedTotal: '总计: {{total}} / {{months}}个月',
    customPricing: '定制价格',
    popularBadge: '最受欢迎',
    secureFooter:
      '所有支付均通过 Atmos 支付网关安全处理。您可以随时修改或取消您的订阅。',
    checkoutTitle: '通过 Atmos 支付',
    checkoutSubtitle: 'Uzcard, Humo, Visa 或 Mastercard',
    checkoutPlan: '计划',
    checkoutTotal: '总价',
    cardNumber: '卡号',
    expiryDate: '有效期',
    cvc: 'CVC',
    cardholderName: '持卡人姓名',
    processing: '处理中...',
    payNow: '立即支付',
    otpTitle: '确认支付',
    otpSubtitle: '包含 6 位数验证码的短信已发送至您的手机',
    verifying: '验证中...',
    confirmOtp: '确认验证码',
    cancelUseAnother: '取消并使用其他卡',
    paymentSuccessful: '支付成功！',
    successSubtitle: '您的交易已安全处理。',
    subActivated: '订阅已激活',
    subDelayed: '支付已成功完成，但激活出现延迟。请联系客服。',
    continueToSwipies: '继续使用 Swipies',
    protectedByAtmos: '受 Atmos 安全保护',
    plans: {
      plus: {
        name: 'Plus',
        description: '适合活跃用户',
        features: [
          '50 个应用 (聊天与智能体)',
          '5 个团队成员',
          '5 GB 数据集存储',
          '每月 5,000 点积分',
        ],
        cta: '选择 Plus',
      },
      pro: {
        name: 'Pro',
        description: '适合专业人士和团队',
        features: [
          '无限应用',
          '15 个团队成员',
          '15 GB 数据集存储',
          '每月 10,000 点积分',
        ],
        cta: '选择 Pro',
      },
      enterprise: {
        name: 'Enterprise',
        description: '适合有高级需求的企业',
        features: [
          '无限应用与知识库',
          '无限存储空间与团队成员',
          '专用服务器 / 私有化部署',
          '最高安全级别与 SLA',
          '专属客户经理',
          '定制化集成',
        ],
        cta: '联系我们',
      },
      license: {
        name: '自主托管许可证',
        description: '在您自己的基础设施上运行 Swipies AI',
        features: [
          '自主托管 (Docker/k8s) 部署',
          '通过许可证密钥激活',
          '无摄取或团队限制',
          'GPU 和向量数据库加速',
          '支持离线/气隙环境',
          '定期安全和功能更新',
        ],
        cta: '购买密钥',
      },
    },
    referralTitle: '想要免费扩展您的额度吗？',
    referralSubtitle:
      '邀请好友加入 Swipies，每成功邀请一位即可获得 +1 GB 存储空间和 +5 个 Agent/应用！',
    referralButton: '获取推荐链接',
    activePlanBadge: '您的当前订阅',
    activePlanExpiry: '有效期至 {{date}}',
    activePlanLifetime: '终身访问权限',
  },
};

export default function PricingPage() {
  const { i18n } = useTranslation();
  const navigate = useNavigate();
  const currentLang = i18n.language || 'en';
  const lang = currentLang.startsWith('ru')
    ? 'ru'
    : currentLang.startsWith('uz')
      ? 'uz'
      : currentLang.startsWith('zh')
        ? 'zh'
        : 'en';

  const tPrice = pricingTranslations[lang];

  const { data: userInfo } = useFetchUserInfo();
  const userEmail = userInfo?.email || '';

  const { data: tenantInfo } = useFetchTenantInfo();
  const currentPlan = (tenantInfo?.plan_type || 'free').toLowerCase();
  const expiryDate = tenantInfo?.plan_expiry_date;

  const getExpiryText = (dateStr?: string) => {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return '';
      if (d.getFullYear() > new Date().getFullYear() + 20) {
        return tPrice.activePlanLifetime;
      }
      return tPrice.activePlanExpiry.replace(
        '{{date}}',
        d.toLocaleDateString(
          lang === 'zh'
            ? 'zh-CN'
            : lang === 'ru'
              ? 'ru-RU'
              : lang === 'uz'
                ? 'uz-UZ'
                : 'en-US',
        ),
      );
    } catch {
      return '';
    }
  };

  // Determine if the user is from Uzbekistan
  const isUzbekistanUser = (() => {
    const phone = userInfo?.phone || userInfo?.phone_number || '';
    if (phone) {
      const cleanPhone = phone.replace(/[^\d+]/g, '');
      if (cleanPhone.startsWith('+998') || cleanPhone.startsWith('998')) {
        return true;
      }
    }
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (tz === 'Asia/Tashkent') {
        return true;
      }
    } catch {
      // Ignore
    }
    const langs = navigator.languages || [navigator.language];
    if (langs.some((l) => l.toLowerCase().includes('uz'))) {
      return true;
    }
    return false;
  })();

  const { config } = useSystemConfig();
  const pricing = config?.pricing || {};
  const plusPrice = isUzbekistanUser
    ? Number(pricing.plus_uzs || 199000)
    : Number(pricing.plus_usd || 20);
  const proPrice = isUzbekistanUser
    ? Number(pricing.pro_uzs || 400000)
    : Number(pricing.pro_usd || 40);

  const USD_RATE = 13000; // 1 USD = 13,000 UZS exchange rate

  // USD Formatter
  const formatUSD = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const displayedPrice = (amount: number) => {
    return isUzbekistanUser ? formatUZS(amount) : formatUSD(amount);
  };

  const PLANS = {
    plus: {
      name: tPrice.plans.plus.name,
      pricePerMonth: plusPrice,
      description: tPrice.plans.plus.description,
      features: tPrice.plans.plus.features,
      cta: tPrice.plans.plus.cta,
      disabled: false,
    },
    pro: {
      name: tPrice.plans.pro.name,
      pricePerMonth: proPrice,
      description: tPrice.plans.pro.description,
      features: tPrice.plans.pro.features,
      cta: tPrice.plans.pro.cta,
      disabled: false,
      popular: true,
    },
    license: {
      name: tPrice.plans.license.name,
      pricePerMonth: isUzbekistanUser ? 2470000 : 190,
      description: tPrice.plans.license.description,
      features: tPrice.plans.license.features,
      cta: tPrice.plans.license.cta,
      disabled: false,
    },
    enterprise: {
      name: tPrice.plans.enterprise.name,
      pricePerMonth: 0,
      description: tPrice.plans.enterprise.description,
      features: tPrice.plans.enterprise.features,
      cta: tPrice.plans.enterprise.cta,
      disabled: false,
    },
  };

  const PERIODS = [
    { months: 1, label: tPrice.oneMonth, discount: 0, badge: null },
    { months: 6, label: tPrice.sixMonths, discount: 0.1, badge: '−10%' },
    { months: 12, label: tPrice.oneYear, discount: 0.2, badge: '−20%' },
  ];

  const [selectedPeriod, setSelectedPeriod] = useState(1);
  const [activePlanKey] = useState<
    'plus' | 'pro' | 'license' | null
  >(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [step, setStep] = useState<
    'card' | 'processing_card' | 'otp' | 'processing_otp' | 'success'
  >('card');
  const [cardNumber, setCardNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [cvc, setCvc] = useState('');
  const [cardName, setCardName] = useState('');
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [transactionId, setTransactionId] = useState<string | null>(null);
  const [maskedPhone, setMaskedPhone] = useState('');
  const [ragflowResult, setRagflowResult] = useState<any>(null);

  const activePlan = activePlanKey ? PLANS[activePlanKey] : null;
  const activePeriod = PERIODS.find((p) => p.months === selectedPeriod)!;

  // Calculations
  const calculatePrices = (pricePerMonth: number) => {
    const base = pricePerMonth * selectedPeriod;
    const discount = isUzbekistanUser
      ? Math.round(base * activePeriod.discount)
      : Number((base * activePeriod.discount).toFixed(2));
    const total = base - discount;
    const perMonth =
      selectedPeriod > 1 ? Math.round(total / selectedPeriod) : pricePerMonth;
    return { perMonth, total };
  };

  const plusPrices = calculatePrices(PLANS.plus.pricePerMonth);
  const proPrices = calculatePrices(PLANS.pro.pricePerMonth);
  const licensePrices = calculatePrices(PLANS.license.pricePerMonth);

  const baseAmount = activePlan ? activePlan.pricePerMonth * selectedPeriod : 0;
  const discountAmount = isUzbekistanUser
    ? Math.round(baseAmount * activePeriod.discount)
    : Number((baseAmount * activePeriod.discount).toFixed(2));
  const finalAmount = baseAmount - discountAmount;

  // Card check
  const cleanCardNumber = cardNumber.replace(/\s/g, '');
  const isLocalCard =
    cleanCardNumber.startsWith('8600') ||
    cleanCardNumber.startsWith('9860') ||
    cleanCardNumber.startsWith('5614') ||
    cleanCardNumber.startsWith('5440');
  const isVisaOrMastercard =
    !isUzbekistanUser ||
    (!isLocalCard &&
      (cleanCardNumber.startsWith('4') || cleanCardNumber.startsWith('5')));

  const [searchParams] = useSearchParams();

  const handleOpenCheckout = useCallback(
    (key: 'plus' | 'pro' | 'license' | 'enterprise') => {
      if (key === 'enterprise') {
        window.open('https://t.me/albakiev01', '_blank');
        return;
      }
      navigate(`/checkout?plan=${key}&period=${selectedPeriod}`);
    },
    [navigate, selectedPeriod],
  );

  useEffect(() => {
    const planParam = searchParams.get('plan');
    if (planParam) {
      const lowerParam = planParam.toLowerCase();
      if (lowerParam === 'plus') {
        handleOpenCheckout('plus');
      } else if (lowerParam === 'pro') {
        handleOpenCheckout('pro');
      } else if (
        lowerParam === 'license' ||
        lowerParam === 'self-hosted' ||
        lowerParam === 'self_hosted'
      ) {
        handleOpenCheckout('license');
      }
    }
  }, [searchParams, handleOpenCheckout]);

  const handleCardSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (cleanCardNumber.length < 16 || expiry.length < 5) {
      setError('Please enter a valid card number and expiry date');
      return;
    }
    setError('');
    setStep('processing_card');

    try {
      const [month, year] = expiry.split('/');
      const formattedExpiry = `${year}${month}`;

      if (isVisaOrMastercard) {
        if (cvc.length < 3 || cardName.trim().length === 0) {
          setError(
            'CVC and Cardholder Name are required for international cards',
          );
          setStep('card');
          return;
        }

        const mpsAmount = isUzbekistanUser
          ? finalAmount
          : Math.round(finalAmount * USD_RATE);

        const txData = await safeFetchJson('/api/pay/mps', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pan: cleanCardNumber,
            expiry: formattedExpiry,
            amount: mpsAmount,
            card_name: cardName,
            cvc2: cvc,
            ext_id: generateUUID(),
          }),
        });

        if (txData.payload?.redirect_uri) {
          window.location.href = txData.payload.redirect_uri;
          return;
        }
        await triggerProvision();
      } else {
        // Uzcard / Humo
        const txData = await safeFetchJson('/api/pay/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            amount: finalAmount,
            account: userEmail || 'guest',
          }),
        });

        setTransactionId(txData.transaction_id);

        const preData = await safeFetchJson('/api/pay/pre-apply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            transaction_id: txData.transaction_id,
            card_number: cleanCardNumber,
            expiry: formattedExpiry,
          }),
        });

        const phone =
          preData.phone ||
          preData.phone_number ||
          preData.phoneMask ||
          (preData.payload && preData.payload.phone) ||
          '';
        setMaskedPhone(phone);
        setStep('otp');
      }
    } catch (err: any) {
      setError(err.message || 'Payment gateway error. Please try again.');
      setStep('card');
    }
  };

  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.length < 6) {
      setError('Please enter the 6-digit confirmation code');
      return;
    }
    setError('');
    setStep('processing_otp');

    try {
      const applyRes = await safeFetchJson('/api/pay/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transaction_id: transactionId,
          otp,
          email: userEmail,
          plan: activePlanKey,
          months: selectedPeriod,
        }),
      });

      setRagflowResult(applyRes.provision || { success: true });
      setStep('success');
    } catch (err: any) {
      setError(err.message || 'Invalid code or system error.');
      setStep('otp');
    }
  };

  const formatCardNumberInput = (val: string) => {
    const v = val.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    const parts = [];
    for (let i = 0; i < v.length; i += 4) {
      parts.push(v.substring(i, i + 4));
    }
    setCardNumber(parts.join(' '));
  };

  const formatExpiryInput = (val: string) => {
    const v = val.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    if (v.length >= 2) {
      setExpiry(v.substring(0, 2) + '/' + v.substring(2, 4));
    } else {
      setExpiry(v);
    }
  };

  return (
    <div className="w-full h-screen bg-bg-body overflow-y-auto p-4 sm:p-6 md:p-8 lg:p-12 flex flex-col items-center justify-start">
      <div className="w-full max-w-7xl mx-auto flex flex-col gap-6 sm:gap-8">
        <div>
          {/* Back Link */}
          <Link
            to={Routes.Root}
            className="inline-flex items-center gap-2 text-text-secondary hover:text-text-primary mb-6 transition-colors text-sm font-medium"
          >
            <LucideArrowLeft className="size-4" />
            {tPrice.backToDashboard}
          </Link>

          {/* Title Section */}
          <div className="text-center mb-6 sm:mb-8">
            <h1 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-extrabold text-text-primary tracking-tight mb-3">
              {BRAND.name} {tPrice.title}
            </h1>
            <p className="text-xs sm:text-sm md:text-base text-text-secondary max-w-2xl mx-auto leading-relaxed">
              {tPrice.subtitle}
            </p>

            {/* Active Subscription Banner */}
            {currentPlan && currentPlan !== 'free' && (
              <div className="max-w-md mx-auto mt-4 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl flex items-center justify-center gap-3">
                <ShieldCheck className="size-6 text-emerald-500 shrink-0" />
                <div className="text-left">
                  <h4 className="text-sm font-bold text-text-primary">
                    {tPrice.activePlanBadge}: <span className="text-[#478AF5] capitalize">{currentPlan}</span>
                  </h4>
                  {expiryDate && (
                    <p className="text-xs text-text-secondary">
                      {getExpiryText(expiryDate)}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Billing Period Selector */}
            <div className="inline-flex items-center gap-2 bg-bg-component border border-border p-1 rounded-xl mt-4 sm:mt-6">
              {PERIODS.map((period) => (
                <button
                  key={period.months}
                  onClick={() => setSelectedPeriod(period.months)}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all relative ${
                    selectedPeriod === period.months
                      ? 'bg-[#478AF5] text-white shadow-sm'
                      : 'text-text-secondary hover:text-text-primary hover:bg-bg-body'
                  }`}
                >
                  {period.badge && (
                    <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-emerald-500 text-white text-[8px] font-bold px-1.5 py-0.5 rounded-full shadow-sm">
                      {period.badge}
                    </span>
                  )}
                  {period.label}
                </button>
              ))}
            </div>
          </div>

          {/* Pricing Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 lg:gap-8 items-stretch max-w-7xl mx-auto w-full">
            {/* Plus Card */}
            <div className="border border-border bg-bg-component rounded-2xl p-5 sm:p-6 flex flex-col justify-between transition-all hover:border-[#478AF5] hover:shadow-lg min-h-[480px]">
              <div>
                <div className="mb-4">
                  <h3 className="text-lg sm:text-xl font-bold text-text-primary mb-1">
                    {PLANS.plus.name}
                  </h3>
                  <p className="text-xs text-text-secondary">
                    {PLANS.plus.description}
                  </p>
                </div>
                <div className="mb-4">
                  <span className="text-xl sm:text-2xl lg:text-3xl font-extrabold text-text-primary">
                    {displayedPrice(plusPrices.perMonth)}
                  </span>
                  <span className="text-text-secondary text-xs sm:text-sm">
                    {tPrice.mo}
                  </span>
                  {selectedPeriod > 1 && (
                    <div className="text-[11px] text-emerald-500 font-semibold mt-1">
                      {tPrice.billedTotal
                        .replace('{{total}}', displayedPrice(plusPrices.total))
                        .replace('{{months}}', selectedPeriod.toString())}
                    </div>
                  )}
                </div>
                <ul className="space-y-2 mb-6">
                  {PLANS.plus.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-start gap-2 text-xs sm:text-sm text-text-secondary"
                    >
                      <LucideCheck className="size-4 text-[#42D7E7] shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
              {currentPlan === 'plus' ? (
                <div className="w-full mt-auto">
                  <Button
                    className="w-full bg-emerald-600 hover:bg-emerald-600 text-white font-bold py-2.5 rounded-xl text-xs sm:text-sm flex items-center justify-center gap-1.5 cursor-default"
                    disabled
                  >
                    <ShieldCheck className="size-4 shrink-0" />
                    {tPrice.activePlanBadge}
                  </Button>
                  {expiryDate && (
                    <p className="text-[10px] text-emerald-500 font-semibold text-center mt-1">
                      {getExpiryText(expiryDate)}
                    </p>
                  )}
                </div>
              ) : (
                <Button
                  className="w-full bg-[#478AF5]/10 hover:bg-[#478AF5]/20 text-[#478AF5] border border-[#478AF5]/20 font-bold py-2.5 rounded-xl transition-all text-xs sm:text-sm mt-auto"
                  onClick={() => handleOpenCheckout('plus')}
                >
                  {PLANS.plus.cta}
                </Button>
              )}
            </div>

            {/* Pro Card */}
            <div className="relative border-2 border-[#478AF5] bg-gradient-to-b from-[#478AF5]/5 to-[#42D7E7]/5 rounded-2xl p-5 sm:p-6 flex flex-col justify-between shadow-md transition-all hover:shadow-xl scale-[1.01] md:scale-[1.02] min-h-[480px]">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[10px] font-semibold text-white rounded-full bg-gradient-to-r from-[#478AF5] to-[#42D7E7] shadow-sm">
                  <LucideZap className="size-3" />
                  {tPrice.popularBadge}
                </span>
              </div>
              <div>
                <div className="mb-4 mt-2">
                  <h3 className="text-lg sm:text-xl font-bold text-text-primary mb-1">
                    {PLANS.pro.name}
                  </h3>
                  <p className="text-xs text-text-secondary">
                    {PLANS.pro.description}
                  </p>
                </div>
                <div className="mb-4">
                  <span className="text-xl sm:text-2xl lg:text-3xl font-extrabold text-text-primary">
                    {displayedPrice(proPrices.perMonth)}
                  </span>
                  <span className="text-text-secondary text-xs sm:text-sm">
                    {tPrice.mo}
                  </span>
                  {selectedPeriod > 1 && (
                    <div className="text-[11px] text-emerald-500 font-semibold mt-1">
                      {tPrice.billedTotal
                        .replace('{{total}}', displayedPrice(proPrices.total))
                        .replace('{{months}}', selectedPeriod.toString())}
                    </div>
                  )}
                </div>
                <ul className="space-y-2 mb-6">
                  {PLANS.pro.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-start gap-2 text-xs sm:text-sm text-text-secondary"
                    >
                      <LucideCheck className="size-4 text-[#42D7E7] shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
              {currentPlan === 'pro' ? (
                <div className="w-full mt-auto">
                  <Button
                    className="w-full bg-emerald-600 hover:bg-emerald-600 text-white font-bold py-2.5 rounded-xl text-xs sm:text-sm flex items-center justify-center gap-1.5 cursor-default"
                    disabled
                  >
                    <ShieldCheck className="size-4 shrink-0" />
                    {tPrice.activePlanBadge}
                  </Button>
                  {expiryDate && (
                    <p className="text-[10px] text-emerald-500 font-semibold text-center mt-1">
                      {getExpiryText(expiryDate)}
                    </p>
                  )}
                </div>
              ) : (
                <Button
                  className="w-full bg-gradient-to-r from-[#478AF5] to-[#42D7E7] text-white hover:from-[#3a7ae0] hover:to-[#35c5d4] shadow-md border-0 font-bold py-2.5 rounded-xl transition-all text-xs sm:text-sm mt-auto"
                  onClick={() => handleOpenCheckout('pro')}
                >
                  {PLANS.pro.cta}
                </Button>
              )}
            </div>

            {/* Self-Hosted License Card */}
            <div className="border border-border bg-bg-component rounded-2xl p-5 sm:p-6 flex flex-col justify-between transition-all hover:border-[#478AF5] hover:shadow-lg min-h-[480px]">
              <div>
                <div className="mb-4">
                  <h3 className="text-lg sm:text-xl font-bold text-text-primary mb-1">
                    {PLANS.license.name}
                  </h3>
                  <p className="text-xs text-text-secondary">
                    {PLANS.license.description}
                  </p>
                </div>
                <div className="mb-4">
                  <span className="text-xl sm:text-2xl lg:text-3xl font-extrabold text-text-primary">
                    {displayedPrice(licensePrices.perMonth)}
                  </span>
                  <span className="text-text-secondary text-xs sm:text-sm">
                    {tPrice.mo}
                  </span>
                  {selectedPeriod > 1 && (
                    <div className="text-[11px] text-emerald-500 font-semibold mt-1">
                      {tPrice.billedTotal
                        .replace('{{total}}', displayedPrice(licensePrices.total))
                        .replace('{{months}}', selectedPeriod.toString())}
                    </div>
                  )}
                </div>
                <ul className="space-y-2 mb-6">
                  {PLANS.license.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-start gap-2 text-xs sm:text-sm text-text-secondary"
                    >
                      <LucideCheck className="size-4 text-[#42D7E7] shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
              {currentPlan === 'license' ? (
                <div className="w-full mt-auto">
                  <Button
                    className="w-full bg-emerald-600 hover:bg-emerald-600 text-white font-bold py-2.5 rounded-xl text-xs sm:text-sm flex items-center justify-center gap-1.5 cursor-default"
                    disabled
                  >
                    <ShieldCheck className="size-4 shrink-0" />
                    {tPrice.activePlanBadge}
                  </Button>
                  {expiryDate && (
                    <p className="text-[10px] text-emerald-500 font-semibold text-center mt-1">
                      {getExpiryText(expiryDate)}
                    </p>
                  )}
                </div>
              ) : (
                <Button
                  className="w-full bg-[#478AF5]/10 hover:bg-[#478AF5]/20 text-[#478AF5] border border-[#478AF5]/20 font-bold py-2.5 rounded-xl transition-all text-xs sm:text-sm mt-auto"
                  onClick={() => handleOpenCheckout('license')}
                >
                  {PLANS.license.cta}
                </Button>
              )}
            </div>

            {/* Enterprise Card */}
            <div className="border border-border bg-bg-component rounded-2xl p-5 sm:p-6 flex flex-col justify-between transition-all hover:border-[#478AF5] hover:shadow-lg min-h-[480px]">
              <div>
                <div className="mb-4">
                  <h3 className="text-lg sm:text-xl font-bold text-text-primary mb-1">
                    {PLANS.enterprise.name}
                  </h3>
                  <p className="text-xs text-text-secondary">
                    {PLANS.enterprise.description}
                  </p>
                </div>
                <div className="mb-4">
                  <span className="text-xl sm:text-2xl lg:text-3xl font-extrabold text-text-primary block">
                    {PLANS.enterprise.name}
                  </span>
                  <span className="text-text-secondary text-[11px]">
                    {tPrice.customPricing}
                  </span>
                </div>
                <ul className="space-y-2 mb-6">
                  {PLANS.enterprise.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-start gap-2 text-xs sm:text-sm text-text-secondary"
                    >
                      <LucideCheck className="size-4 text-[#42D7E7] shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <Button
                className="w-full bg-bg-component text-text-primary hover:bg-bg-body border border-border font-bold py-2.5 rounded-xl transition-all text-xs sm:text-sm mt-auto"
                onClick={() => handleOpenCheckout('enterprise')}
              >
                {PLANS.enterprise.cta}
              </Button>
            </div>
          </div>
        </div>

        {/* Referral Program Banner */}
        <div className="mt-12 max-w-4xl mx-auto border border-border bg-bg-component rounded-2xl p-6 sm:p-8 flex flex-col md:flex-row items-center justify-between gap-6 shadow-xl relative overflow-hidden transition-all hover:border-[#478AF5]/40 hover:shadow-2xl">
          <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none translate-x-4 -translate-y-4">
            <Gift size={160} className="text-[#478AF5]" />
          </div>
          <div className="flex items-center gap-4 relative z-10">
            <div className="p-4 bg-[#478AF5]/10 rounded-2xl text-[#478AF5] shrink-0">
              <Gift size={32} className="animate-pulse" />
            </div>
            <div className="space-y-1 text-left">
              <h4 className="text-base sm:text-lg font-bold text-text-primary">
                {tPrice.referralTitle}
              </h4>
              <p className="text-xs sm:text-sm text-text-secondary max-w-lg">
                {tPrice.referralSubtitle}
              </p>
            </div>
          </div>
          <Link
            to={`${Routes.UserSetting}${Routes.Referrals}`}
            className="relative z-10 shrink-0 w-full md:w-auto text-center"
          >
            <Button className="w-full md:w-auto bg-gradient-to-r from-[#478AF5] to-[#42D7E7] text-white hover:from-[#3a7ae0] hover:to-[#35c5d4] shadow-md border-0 font-bold py-2.5 px-6 rounded-xl transition-all text-xs sm:text-sm">
              {tPrice.referralButton}
            </Button>
          </Link>
        </div>

        <p className="text-center text-[11px] sm:text-xs text-text-secondary mt-6 pb-8">
          {tPrice.secureFooter}
        </p>
      </div>

      {/* Checkout Modal */}
      {isModalOpen && activePlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-bg-component border border-border rounded-2xl w-full max-w-md p-6 sm:p-8 relative flex flex-col shadow-2xl overflow-y-auto max-h-[90vh]">
            {/* Close */}
            {(step === 'card' || step === 'otp') && (
              <button
                onClick={() => setIsModalOpen(false)}
                className="absolute top-4 right-4 text-text-secondary hover:text-text-primary text-2xl p-1 leading-none transition-colors"
              >
                &times;
              </button>
            )}

            {/* Step: Card Details Entry */}
            {(step === 'card' || step === 'processing_card') && (
              <div className="w-full">
                <div className="text-center mb-6">
                  <div className="w-12 h-12 rounded-full bg-[#478AF5]/10 flex items-center justify-center mx-auto mb-3">
                    <CreditCard className="w-6 h-6 text-[#478AF5]" />
                  </div>
                  <h3 className="text-xl sm:text-2xl font-bold text-text-primary">
                    {tPrice.checkoutTitle}
                  </h3>
                  <p className="text-text-secondary text-xs sm:text-sm mt-1">
                    {tPrice.checkoutSubtitle}
                  </p>
                </div>

                {/* Summary Box */}
                <div className="bg-bg-body border border-border rounded-xl p-4 mb-6 text-sm">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-text-secondary">
                      {tPrice.checkoutPlan}:
                    </span>
                    <span className="font-semibold text-text-primary">
                      {activePlan.name} ({activePeriod.label})
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">
                      {tPrice.checkoutTotal}:
                    </span>
                    <span className="font-bold text-[#478AF5] text-base sm:text-lg">
                      {displayedPrice(finalAmount)}
                    </span>
                  </div>
                </div>

                <form onSubmit={handleCardSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-text-secondary mb-1">
                      {tPrice.cardNumber}
                    </label>
                    <input
                      type="text"
                      placeholder="8600 0000 0000 0000"
                      value={cardNumber}
                      onChange={(e) => formatCardNumberInput(e.target.value)}
                      maxLength={19}
                      disabled={step === 'processing_card'}
                      className="w-full bg-white border border-border rounded-xl px-4 py-2.5 text-black text-sm sm:text-base focus:outline-none focus:border-[#478AF5] font-mono tracking-wider transition-colors"
                      required
                    />
                  </div>

                  <div
                    className={
                      isVisaOrMastercard ? 'grid grid-cols-2 gap-4' : 'w-full'
                    }
                  >
                    <div>
                      <label className="block text-xs font-semibold text-text-secondary mb-1">
                        {tPrice.expiryDate}
                      </label>
                      <input
                        type="text"
                        placeholder="MM/YY"
                        value={expiry}
                        onChange={(e) => formatExpiryInput(e.target.value)}
                        maxLength={5}
                        disabled={step === 'processing_card'}
                        className="w-full bg-white border border-border rounded-xl px-4 py-2.5 text-black text-sm sm:text-base focus:outline-none focus:border-[#478AF5] font-mono tracking-wider transition-colors"
                        required
                      />
                    </div>

                    {isVisaOrMastercard && (
                      <div>
                        <label className="block text-xs font-semibold text-text-secondary mb-1">
                          {tPrice.cvc}
                        </label>
                        <input
                          type="password"
                          placeholder="123"
                          value={cvc}
                          onChange={(e) =>
                            setCvc(
                              e.target.value.replace(/\D/g, '').slice(0, 3),
                            )
                          }
                          disabled={step === 'processing_card'}
                          className="w-full bg-white border border-border rounded-xl px-4 py-2.5 text-black text-sm sm:text-base focus:outline-none focus:border-[#478AF5] font-mono tracking-wider transition-colors"
                          required
                        />
                      </div>
                    )}
                  </div>

                  {isVisaOrMastercard && (
                    <div>
                      <label className="block text-xs font-semibold text-text-secondary mb-1">
                        {tPrice.cardholderName}
                      </label>
                      <input
                        type="text"
                        placeholder="JOHN DOE"
                        value={cardName}
                        onChange={(e) =>
                          setCardName(e.target.value.toUpperCase())
                        }
                        disabled={step === 'processing_card'}
                        className="w-full bg-white border border-border rounded-xl px-4 py-2.5 text-black text-sm sm:text-base focus:outline-none focus:border-[#478AF5] font-mono tracking-wider transition-colors"
                        required
                      />
                    </div>
                  )}

                  {error && (
                    <p className="text-red-500 text-xs sm:text-sm text-center font-medium">
                      {error}
                    </p>
                  )}

                  <Button
                    type="submit"
                    disabled={step === 'processing_card'}
                    className="w-full bg-gradient-to-r from-[#478AF5] to-[#42D7E7] text-white py-2.5 sm:py-3 rounded-xl font-bold flex justify-center items-center gap-2 mt-4 hover:scale-[1.01] transition-transform"
                  >
                    {step === 'processing_card' ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        {tPrice.processing}
                      </>
                    ) : (
                      tPrice.payNow
                    )}
                  </Button>
                </form>
              </div>
            )}

            {/* Step: OTP SMS Verification */}
            {(step === 'otp' || step === 'processing_otp') && (
              <div className="w-full text-center">
                <div className="w-12 h-12 rounded-full bg-[#478AF5]/10 flex items-center justify-center mx-auto mb-3">
                  <ShieldCheck className="w-6 h-6 text-[#478AF5]" />
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-text-primary">
                  {tPrice.otpTitle}
                </h3>
                <p className="text-text-secondary text-xs sm:text-sm mt-2 mb-6">
                  {tPrice.otpSubtitle}
                  {maskedPhone ? ` (${maskedPhone})` : ''}.
                </p>

                <form onSubmit={handleOtpSubmit} className="space-y-4">
                  <div>
                    <input
                      type="text"
                      placeholder="000000"
                      value={otp}
                      onChange={(e) =>
                        setOtp(
                          e.target.value.replace(/\D/g, '').substring(0, 6),
                        )
                      }
                      disabled={step === 'processing_otp'}
                      className="w-full bg-white border border-border rounded-xl px-4 py-2.5 text-black text-center text-lg sm:text-xl tracking-[0.3em] sm:tracking-[0.4em] focus:outline-none focus:border-[#478AF5] font-mono transition-colors"
                      required
                    />
                  </div>

                  {error && (
                    <p className="text-red-500 text-xs sm:text-sm font-medium">
                      {error}
                    </p>
                  )}

                  <Button
                    type="submit"
                    disabled={step === 'processing_otp'}
                    className="w-full bg-gradient-to-r from-[#478AF5] to-[#42D7E7] text-white py-2.5 sm:py-3 rounded-xl font-bold flex justify-center items-center gap-2 hover:scale-[1.01] transition-transform"
                  >
                    {step === 'processing_otp' ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        {tPrice.verifying}
                      </>
                    ) : (
                      tPrice.confirmOtp
                    )}
                  </Button>

                  {step === 'otp' && (
                    <button
                      type="button"
                      onClick={() => setStep('card')}
                      className="text-text-secondary hover:text-text-primary text-xs font-semibold mt-4 transition-colors"
                    >
                      {tPrice.cancelUseAnother}
                    </button>
                  )}
                </form>
              </div>
            )}

            {/* Step: Success Screen */}
            {step === 'success' && (
              <div className="w-full text-center animate-in zoom-in-95 duration-300">
                <div className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mb-4 mx-auto">
                  <CheckCircle className="w-8 h-8 text-emerald-500" />
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-text-primary">
                  {tPrice.paymentSuccessful}
                </h3>
                <p className="text-emerald-500 text-xs sm:text-sm font-medium mt-1 mb-6">
                  {tPrice.successSubtitle}
                </p>

                {ragflowResult?.success ? (
                  <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4 mb-6 text-left text-xs sm:text-sm">
                    <p className="text-emerald-500 font-bold mb-1">
                      ✅ {tPrice.subActivated}
                    </p>
                    <p className="text-text-secondary mb-1">
                      {tPrice.checkoutPlan}:{' '}
                      <span className="text-text-primary font-semibold">
                        {activePlan?.name}
                      </span>
                    </p>
                    <p className="text-text-secondary mb-3">
                      Account:{' '}
                      <span className="text-text-primary font-semibold">
                        {userEmail}
                      </span>
                    </p>
                    {ragflowResult?.licenseKey && (
                      <div className="mt-3 pt-3 border-t border-emerald-500/10">
                        <p className="text-emerald-500 font-bold mb-2">
                          🔑 Your License Key:
                        </p>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            readOnly
                            value={ragflowResult.licenseKey}
                            onClick={(e) => (e.target as HTMLInputElement).select()}
                            className="flex-1 bg-white border border-border rounded-lg px-3 py-1.5 text-black text-xs font-mono select-all focus:outline-none"
                          />
                          <Button
                            onClick={() => {
                              navigator.clipboard.writeText(ragflowResult.licenseKey);
                              alert('License key copied to clipboard!');
                            }}
                            className="bg-[#478AF5] text-white hover:bg-[#3a7ae0] text-xs px-3 py-1.5 h-auto rounded-lg"
                          >
                            Copy
                          </Button>
                        </div>
                        <p className="text-text-secondary text-[10px] mt-2 leading-relaxed">
                          Copy this key and paste it in the System License Activation page to activate your instance.
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bg-yellow-500/5 border border-yellow-500/20 rounded-xl p-4 mb-6 text-left text-xs sm:text-sm text-yellow-600">
                    {tPrice.subDelayed}
                  </div>
                )}

                <Button
                  onClick={() => setIsModalOpen(false)}
                  className="w-full bg-gradient-to-r from-[#478AF5] to-[#42D7E7] text-white py-2.5 sm:py-3 rounded-xl font-bold shadow-md hover:scale-[1.01] transition-transform"
                >
                  {tPrice.continueToSwipies}
                </Button>
              </div>
            )}

            <div className="mt-6 flex items-center justify-center gap-1.5 text-[10px] sm:text-xs text-text-secondary border-t border-border pt-4 w-full">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />{' '}
              {tPrice.protectedByAtmos}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
