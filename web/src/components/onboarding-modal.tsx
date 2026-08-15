import React, { useState, useEffect } from 'react';
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
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SurveyOption {
  id: string;
  title: string;
  description?: string;
  icon: React.ReactNode;
}

interface StepConfig {
  key: string;
  title: string;
  subtitle: string;
  options: SurveyOption[];
}

const STEPS: StepConfig[] = [
  {
    key: 'purpose',
    title: 'Welcome to Swipies AI! 👋',
    subtitle: 'What brings you here today? Select your primary goal:',
    options: [
      {
        id: 'work',
        title: 'Work & Business Automation',
        description: 'Automate support, documentation, and team workflows',
        icon: <Briefcase className="w-5 h-5 text-teal-400" />,
      },
      {
        id: 'ai_agents',
        title: 'Build Custom AI Agents & RAG',
        description: 'Create knowledge bases, chatbots, and AI assistants',
        icon: <Bot className="w-5 h-5 text-cyan-400" />,
      },
      {
        id: 'study',
        title: 'Study & Academic Research',
        description: 'Analyze papers, manage knowledge, and organize notes',
        icon: <GraduationCap className="w-5 h-5 text-emerald-400" />,
      },
      {
        id: 'productivity',
        title: 'Personal Productivity Assistant',
        description: 'Boost daily organization and task management',
        icon: <Sparkles className="w-5 h-5 text-amber-400" />,
      },
      {
        id: 'exploring',
        title: 'Just Exploring Features',
        description: 'Test out Swipies AI capabilities and performance',
        icon: <Search className="w-5 h-5 text-blue-400" />,
      },
    ],
  },
  {
    key: 'role',
    title: 'What is your role? 💼',
    subtitle: 'Help us tailor your experience to your background:',
    options: [
      {
        id: 'developer',
        title: 'Software Engineer / Developer',
        icon: <Code className="w-5 h-5 text-sky-400" />,
      },
      {
        id: 'founder',
        title: 'Founder / CEO / Executive',
        icon: <UserCheck className="w-5 h-5 text-purple-400" />,
      },
      {
        id: 'pm',
        title: 'Product / Project Manager',
        icon: <Kanban className="w-5 h-5 text-pink-400" />,
      },
      {
        id: 'marketing',
        title: 'Marketing / Sales / Growth',
        icon: <Megaphone className="w-5 h-5 text-orange-400" />,
      },
      {
        id: 'student',
        title: 'Student / Researcher',
        icon: <GraduationCap className="w-5 h-5 text-indigo-400" />,
      },
      {
        id: 'other',
        title: 'Other Role / Freelancer',
        icon: <User className="w-5 h-5 text-gray-400" />,
      },
    ],
  },
  {
    key: 'team_size',
    title: 'How big is your team? 👥',
    subtitle: 'Select your team or organization size:',
    options: [
      {
        id: '1',
        title: 'Just Me (Solo)',
        description: 'Working independently',
        icon: <User className="w-5 h-5 text-teal-400" />,
      },
      {
        id: '2_10',
        title: '2 – 10 People',
        description: 'Small team or startup',
        icon: <Users className="w-5 h-5 text-cyan-400" />,
      },
      {
        id: '11_50',
        title: '11 – 50 People',
        description: 'Mid-size team',
        icon: <Building className="w-5 h-5 text-purple-400" />,
      },
      {
        id: '50_plus',
        title: '50+ People',
        description: 'Large company or enterprise',
        icon: <Building2 className="w-5 h-5 text-amber-400" />,
      },
    ],
  },
  {
    key: 'industry',
    title: 'What industry do you work in? 🏢',
    subtitle: 'Choose the option that best describes your domain:',
    options: [
      {
        id: 'tech',
        title: 'IT & Software Development',
        icon: <Code className="w-5 h-5 text-teal-400" />,
      },
      {
        id: 'ecommerce',
        title: 'E-Commerce & Retail',
        icon: <Briefcase className="w-5 h-5 text-blue-400" />,
      },
      {
        id: 'finance',
        title: 'Finance, Banking & Legal',
        icon: <Building className="w-5 h-5 text-emerald-400" />,
      },
      {
        id: 'education',
        title: 'Education & Science',
        icon: <GraduationCap className="w-5 h-5 text-indigo-400" />,
      },
      {
        id: 'creative',
        title: 'Media, Design & Marketing',
        icon: <Sparkles className="w-5 h-5 text-pink-400" />,
      },
      {
        id: 'other',
        title: 'Other Industry',
        icon: <Building2 className="w-5 h-5 text-gray-400" />,
      },
    ],
  },
];

export function OnboardingModal() {
  const { data: userInfo } = useFetchUserInfo();
  const [open, setOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

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
              Step {currentStep + 1} of {STEPS.length}
            </span>
          </div>

          <button
            onClick={() => finishSurvey(true)}
            className="text-xs text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-1 py-1 px-2.5 rounded-lg hover:bg-slate-800 cursor-pointer"
          >
            Skip for now <X className="w-3.5 h-3.5" />
          </button>
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
            {step.title}
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {step.subtitle}
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
                      {opt.title}
                    </span>
                    {isSelected && (
                      <CheckCircle2 className="w-4 h-4 text-teal-400 shrink-0" />
                    )}
                  </div>
                  {opt.description && (
                    <p className="text-xs text-slate-400 leading-snug mt-0.5">
                      {opt.description}
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
            className="text-slate-400 hover:text-slate-200 disabled:opacity-30 flex items-center gap-1.5 text-xs"
          >
            <ChevronLeft className="w-4 h-4" /> Back
          </Button>

          <Button
            type="button"
            onClick={handleNext}
            disabled={!selectedOptionId || loading}
            className="bg-gradient-to-r from-teal-500 to-cyan-500 hover:from-teal-400 hover:to-cyan-400 text-slate-950 font-semibold px-5 py-2 rounded-xl text-xs flex items-center gap-1.5 transition-all shadow-md disabled:opacity-40 cursor-pointer"
          >
            {loading ? (
              'Saving...'
            ) : currentStep === STEPS.length - 1 ? (
              'Complete Setup 🎉'
            ) : (
              <>
                Next <ChevronRight className="w-4 h-4" />
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
