import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import request from '@/utils/request';
import {
  Briefcase,
  Bot,
  GraduationCap,
  Sparkles,
  Search,
  Code,
  UserCheck,
  Kanban,
  Megaphone,
  User,
  Users,
  Building,
  Building2,
  CheckCircle2,
  ChevronRight,
  ChevronLeft,
  X,
  Globe,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SurveyOption {
  id: string;
  title: { en: string; ru: string };
  description?: { en: string; ru: string };
  icon: React.ReactNode;
}

interface StepConfig {
  key: string;
  title: { en: string; ru: string };
  subtitle: { en: string; ru: string };
  options: SurveyOption[];
}

const STEPS: StepConfig[] = [
  {
    key: 'purpose',
    title: {
      en: 'Welcome to Swipies AI! 👋',
      ru: 'Добро пожаловать в Swipies AI! 👋',
    },
    subtitle: {
      en: 'What brings you here today? Select your primary goal:',
      ru: 'Какова ваша основная цель использования платформы?',
    },
    options: [
      {
        id: 'work',
        title: {
          en: 'Work & Business Automation',
          ru: 'Автоматизация работы и бизнеса',
        },
        description: {
          en: 'Automate support, documentation, and team workflows',
          ru: 'Автоматизация поддержки, документации и процессов',
        },
        icon: <Briefcase className="w-5 h-5 text-teal-400" />,
      },
      {
        id: 'ai_agents',
        title: {
          en: 'Build Custom AI Agents & RAG',
          ru: 'Создание ИИ-агентов и Баз Знаний',
        },
        description: {
          en: 'Create knowledge bases, chatbots, and AI assistants',
          ru: 'Базы знаний, чат-боты и автономные ассистенты',
        },
        icon: <Bot className="w-5 h-5 text-cyan-400" />,
      },
      {
        id: 'study',
        title: {
          en: 'Study & Academic Research',
          ru: 'Учеба, исследования и заметки',
        },
        description: {
          en: 'Analyze papers, manage knowledge, and organize notes',
          ru: 'Анализ научных статей, база знаний и конспекты',
        },
        icon: <GraduationCap className="w-5 h-5 text-emerald-400" />,
      },
      {
        id: 'productivity',
        title: {
          en: 'Personal Productivity Assistant',
          ru: 'Личный ИИ-помощник',
        },
        description: {
          en: 'Boost daily organization and task management',
          ru: 'Повышение личной эффективности и решение задач',
        },
        icon: <Sparkles className="w-5 h-5 text-amber-400" />,
      },
      {
        id: 'exploring',
        title: {
          en: 'Just Exploring Features',
          ru: 'Тестирование возможностей',
        },
        description: {
          en: 'Test out Swipies AI capabilities and performance',
          ru: 'Ознакомление с функциями и возможностями',
        },
        icon: <Search className="w-5 h-5 text-blue-400" />,
      },
    ],
  },
  {
    key: 'role',
    title: {
      en: 'What is your role? 💼',
      ru: 'Кем вы работаете? 💼',
    },
    subtitle: {
      en: 'Help us tailor your experience to your background:',
      ru: 'Выберите вашу должность или специализацию:',
    },
    options: [
      {
        id: 'developer',
        title: {
          en: 'Software Engineer / Developer',
          ru: 'Разработчик / Инженер ПО',
        },
        icon: <Code className="w-5 h-5 text-sky-400" />,
      },
      {
        id: 'founder',
        title: {
          en: 'Founder / CEO / Executive',
          ru: 'Основатель / Руководитель (CEO)',
        },
        icon: <UserCheck className="w-5 h-5 text-purple-400" />,
      },
      {
        id: 'pm',
        title: {
          en: 'Product / Project Manager',
          ru: 'Менеджер продукта / проектов',
        },
        icon: <Kanban className="w-5 h-5 text-pink-400" />,
      },
      {
        id: 'marketing',
        title: {
          en: 'Marketing / Sales / Growth',
          ru: 'Маркетолог / Продажи / Growth',
        },
        icon: <Megaphone className="w-5 h-5 text-orange-400" />,
      },
      {
        id: 'student',
        title: {
          en: 'Student / Researcher',
          ru: 'Студент / Исследователь',
        },
        icon: <GraduationCap className="w-5 h-5 text-indigo-400" />,
      },
      {
        id: 'other',
        title: {
          en: 'Other Role / Freelancer',
          ru: 'Фрилансер / Другая должность',
        },
        icon: <User className="w-5 h-5 text-gray-400" />,
      },
    ],
  },
  {
    key: 'team_size',
    title: {
      en: 'How big is your team? 👥',
      ru: 'Сколько человек в вашей команде? 👥',
    },
    subtitle: {
      en: 'Select your team or organization size:',
      ru: 'Укажите размер вашей команды или компании:',
    },
    options: [
      {
        id: '1',
        title: {
          en: 'Just Me (Solo)',
          ru: 'Только я (1 человек)',
        },
        description: {
          en: 'Working independently',
          ru: 'Работаю самостоятельно',
        },
        icon: <User className="w-5 h-5 text-teal-400" />,
      },
      {
        id: '2_10',
        title: {
          en: '2 – 10 People',
          ru: '2 – 10 человек',
        },
        description: {
          en: 'Small team or startup',
          ru: 'Небольшая команда или стартап',
        },
        icon: <Users className="w-5 h-5 text-cyan-400" />,
      },
      {
        id: '11_50',
        title: {
          en: '11 – 50 People',
          ru: '11 – 50 человек',
        },
        description: {
          en: 'Mid-size team',
          ru: 'Средняя компания',
        },
        icon: <Building className="w-5 h-5 text-purple-400" />,
      },
      {
        id: '50_plus',
        title: {
          en: '50+ People',
          ru: 'Более 50 человек',
        },
        description: {
          en: 'Large company or enterprise',
          ru: 'Крупная организация или корпорация',
        },
        icon: <Building2 className="w-5 h-5 text-amber-400" />,
      },
    ],
  },
  {
    key: 'industry',
    title: {
      en: 'What industry do you work in? 🏢',
      ru: 'В какой сфере работаете? 🏢',
    },
    subtitle: {
      en: 'Choose the option that best describes your domain:',
      ru: 'Выберите отрасль вашей деятельности:',
    },
    options: [
      {
        id: 'tech',
        title: {
          en: 'IT & Software Development',
          ru: 'IT и разработка ПО',
        },
        icon: <Code className="w-5 h-5 text-teal-400" />,
      },
      {
        id: 'ecommerce',
        title: {
          en: 'E-Commerce & Retail',
          ru: 'Электронная коммерция и ритейл',
        },
        icon: <Briefcase className="w-5 h-5 text-blue-400" />,
      },
      {
        id: 'finance',
        title: {
          en: 'Finance, Banking & Legal',
          ru: 'Финансы, банки и консалтинг',
        },
        icon: <Building className="w-5 h-5 text-emerald-400" />,
      },
      {
        id: 'education',
        title: {
          en: 'Education & Science',
          ru: 'Образование и наука',
        },
        icon: <GraduationCap className="w-5 h-5 text-indigo-400" />,
      },
      {
        id: 'creative',
        title: {
          en: 'Media, Design & Marketing',
          ru: 'Медиа, дизайн и маркетинг',
        },
        icon: <Sparkles className="w-5 h-5 text-pink-400" />,
      },
      {
        id: 'other',
        title: {
          en: 'Other Industry',
          ru: 'Другая сфера',
        },
        icon: <Building2 className="w-5 h-5 text-gray-400" />,
      },
    ],
  },
];

export function OnboardingModal() {
  const { i18n } = useTranslation();
  const { data: userInfo } = useFetchUserInfo();
  const [open, setOpen] = useState(false);
  const [lang, setLang] = useState<'ru' | 'en'>('ru');
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (i18n && i18n.language) {
      if (i18n.language.toLowerCase().startsWith('en')) {
        setLang('en');
      } else {
        setLang('ru');
      }
    }
  }, [i18n?.language]);

  useEffect(() => {
    if (userInfo && userInfo.id) {
      const storageKey = `swipies_onboarded_${userInfo.id}`;
      const localOnboarded = localStorage.getItem(storageKey);
      const serverOnboarded = (userInfo as any).is_onboarded;

      if (!localOnboarded && !serverOnboarded) {
        setOpen(true);
      }
    }
  }, [userInfo]);

  if (!open || !userInfo) return null;

  const step = STEPS[currentStep];
  const selectedOptionId = answers[step.key];

  const handleSelectOption = (optionId: string) => {
    setAnswers((prev) => ({ ...prev, [step.key]: optionId }));
  };

  const handleNext = async () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep((prev) => prev + 1);
    } else {
      await finishSurvey();
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  const finishSurvey = async (skipped = false) => {
    setLoading(true);
    try {
      const finalAnswers = skipped ? { skipped: true } : answers;
      await request.post('/v1/users/me/onboarding', {
        data: finalAnswers,
      });
    } catch (e) {
      console.warn('Failed to submit onboarding survey to backend', e);
    } finally {
      localStorage.setItem(`swipies_onboarded_${userInfo.id}`, 'true');
      setLoading(false);
      setOpen(false);
    }
  };

  const toggleLanguage = () => {
    const nextLang = lang === 'ru' ? 'en' : 'ru';
    setLang(nextLang);
    if (i18n && i18n.changeLanguage) {
      i18n.changeLanguage(nextLang);
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-300">
      <div className="relative w-full max-w-xl bg-[#0f172a]/95 border border-slate-700/80 rounded-2xl p-6 sm:p-8 shadow-2xl text-slate-100 flex flex-col gap-6 overflow-hidden">
        {/* Top Header & Progress */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex items-center justify-center w-7 h-7 rounded-full bg-teal-500/20 text-teal-400 font-bold text-xs border border-teal-500/30">
              {currentStep + 1}
            </span>
            <span className="text-xs text-slate-400 font-medium">
              {lang === 'ru'
                ? `Шаг ${currentStep + 1} из ${STEPS.length}`
                : `Step ${currentStep + 1} of ${STEPS.length}`}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {/* Language Switcher Button */}
            <button
              onClick={toggleLanguage}
              className="text-xs text-slate-300 bg-slate-800/80 hover:bg-slate-700 border border-slate-700/60 px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Globe className="w-3.5 h-3.5 text-teal-400" />
              <span className="font-semibold uppercase">{lang}</span>
            </button>

            {/* Skip Button */}
            <button
              onClick={() => finishSurvey(true)}
              className="text-xs text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-1 py-1 px-2.5 rounded-lg hover:bg-slate-800 cursor-pointer"
            >
              {lang === 'ru' ? 'Пропустить' : 'Skip for now'}{' '}
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-teal-400 via-cyan-400 to-blue-500 transition-all duration-300 ease-out"
            style={{ width: `${((currentStep + 1) / STEPS.length) * 100}%` }}
          />
        </div>

        {/* Question Title & Subtitle */}
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            {step.title[lang]}
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {step.subtitle[lang]}
          </p>
        </div>

        {/* Options List */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[360px] overflow-y-auto pr-1">
          {step.options.map((opt) => {
            const isSelected = selectedOptionId === opt.id;
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => handleSelectOption(opt.id)}
                className={`flex items-start gap-3 p-3.5 rounded-xl border text-left transition-all duration-200 cursor-pointer ${
                  isSelected
                    ? 'border-teal-400 bg-teal-500/10 shadow-[0_0_15px_rgba(45,212,191,0.15)] ring-1 ring-teal-400/50'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-800/60'
                }`}
              >
                <div className="mt-0.5 p-2 rounded-lg bg-slate-800/80 border border-slate-700/50 shrink-0">
                  {opt.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-1">
                    <span className="font-semibold text-sm text-slate-100 truncate">
                      {opt.title[lang]}
                    </span>
                    {isSelected && (
                      <CheckCircle2 className="w-4 h-4 text-teal-400 shrink-0" />
                    )}
                  </div>
                  {opt.description && (
                    <p className="text-xs text-slate-400 leading-snug mt-0.5">
                      {opt.description[lang]}
                    </p>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {/* Bottom Actions */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
          <Button
            type="button"
            variant="ghost"
            onClick={handleBack}
            disabled={currentStep === 0}
            className="text-slate-400 hover:text-slate-200 disabled:opacity-30 flex items-center gap-1.5 text-xs cursor-pointer"
          >
            <ChevronLeft className="w-4 h-4" /> {lang === 'ru' ? 'Назад' : 'Back'}
          </Button>

          <Button
            type="button"
            onClick={handleNext}
            disabled={!selectedOptionId || loading}
            className="bg-gradient-to-r from-teal-500 to-cyan-500 hover:from-teal-400 hover:to-cyan-400 text-slate-950 font-semibold px-5 py-2 rounded-xl text-xs flex items-center gap-1.5 transition-all shadow-md disabled:opacity-40 cursor-pointer"
          >
            {loading ? (
              lang === 'ru' ? 'Сохранение...' : 'Saving...'
            ) : currentStep === STEPS.length - 1 ? (
              lang === 'ru' ? 'Завершить 🎉' : 'Complete Setup 🎉'
            ) : (
              <>
                {lang === 'ru' ? 'Далее' : 'Next'} <ChevronRight className="w-4 h-4" />
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
