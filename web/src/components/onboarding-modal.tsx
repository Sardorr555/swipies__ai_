import { useState, useEffect } from 'react';
import { Modal } from '@/components/ui/modal/modal';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import message from '@/components/ui/message';
import request from '@/utils/request';
import { LucideBuilding, LucideBriefcase, LucideTarget, LucideSparkles, LucideCheckCircle2 } from 'lucide-react';

interface OnboardingModalProps {
  userInfo?: any;
}

export function OnboardingModal({ userInfo }: OnboardingModalProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  // Form State
  const [purpose, setPurpose] = useState('');
  const [intendedUse, setIntendedUse] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [companySize, setCompanySize] = useState('11-50');
  const [industry, setIndustry] = useState('IT / Технологии');
  const [role, setRole] = useState('');
  const [platformGoals, setPlatformGoals] = useState('');

  const [step, setStep] = useState(1);

  const checkOnboardingStatus = async () => {
    if (userInfo && typeof userInfo.is_onboarded === 'boolean') {
      if (!userInfo.is_onboarded) {
        setOpen(true);
        return;
      } else {
        setOpen(false);
        return;
      }
    }

    try {
      const res = await request.get('/api/v1/user/onboarding');
      if (res && res.data && res.data.code === 0) {
        const completed = res.data.data?.completed;
        if (!completed) {
          setOpen(true);
        } else {
          setOpen(false);
        }
      } else {
        setOpen(true);
      }
    } catch {
      setOpen(true);
    }
  };

  useEffect(() => {
    checkOnboardingStatus();
  }, [userInfo?.id, userInfo?.is_onboarded]);

  const handleSubmit = async () => {
    if (!purpose.trim()) {
      message.warning('Пожалуйста, укажите основную цель регистрации.');
      return;
    }
    if (!companyName.trim()) {
      message.warning('Пожалуйста, укажите название компании или организации.');
      return;
    }

    setLoading(true);
    try {
      const res = await request.post('/api/v1/user/onboarding', {
        data: {
          purpose,
          intended_use: intendedUse,
          company_name: companyName,
          company_size: companySize,
          industry,
          role,
          platform_goals: platformGoals,
        },
      });

      if (res && res.data && res.data.code === 0) {
        message.success('Спасибо! Анкета успешно сохранена.');
        setOpen(false);
      } else {
        message.error(res?.data?.message || 'Ошибка сохранения анкеты.');
      }
    } catch (err: any) {
      message.error(err?.response?.data?.message || 'Не удалось отправить анкету.');
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  const PURPOSES = [
    'Управление знаниями (RAG & Knowledge Base)',
    'Создание ИИ-ассистентов для сотрудников',
    'Автоматизация процессов и Canvas Wokflows',
    'Поиск и аналитика по документам',
    'Поддержка клиентов (Customer Support AI)',
    'Личные или научные исследования',
  ];

  const COMPANY_SIZES = ['1-10', '11-50', '51-200', '201-1000', '1000+'];
  const INDUSTRIES = [
    'IT / Технологии',
    'Финансы & Банки',
    'Здравоохранение',
    'Образование',
    'Ритейл & E-commerce',
    'Консалтинг & Услуги',
    'Другое',
  ];

  return (
    <Modal
      open={open}
      onCancel={() => {}} // Cannot close without completing onboarding
      footer={null}
      closable={false}
      maskClosable={false}
      width={680}
      title={null}
    >
      <div className="p-6 text-text-primary">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-border-button">
          <div className="w-10 h-10 rounded-xl bg-accent-primary/10 flex items-center justify-center text-accent-primary">
            <LucideSparkles className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold">Добро пожаловать в платформу!</h2>
            <p className="text-sm text-text-disabled">
              Пожалуйста, ответьте на несколько вопросов, чтобы мы настроили систему под ваши задачи.
            </p>
          </div>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center justify-between mb-8 px-4">
          <div className={`flex items-center gap-2 ${step >= 1 ? 'text-accent-primary font-semibold' : 'text-text-disabled'}`}>
            <span className="w-6 h-6 rounded-full bg-accent-primary/20 flex items-center justify-center text-xs">1</span>
            <span>Цели и использование</span>
          </div>
          <div className="h-0.5 w-16 bg-border-button" />
          <div className={`flex items-center gap-2 ${step >= 2 ? 'text-accent-primary font-semibold' : 'text-text-disabled'}`}>
            <span className="w-6 h-6 rounded-full bg-accent-primary/20 flex items-center justify-center text-xs">2</span>
            <span>Компания и роль</span>
          </div>
        </div>

        {/* Step 1 */}
        {step === 1 && (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                <LucideTarget className="w-4 h-4 text-accent-primary" />
                Зачем вы зарегистрировались? (Основная цель) <span className="text-red-500">*</span>
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {PURPOSES.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => setPurpose(item)}
                    className={`p-3 text-left rounded-xl border text-xs transition-all ${
                      purpose === item
                        ? 'border-accent-primary bg-accent-primary/10 font-semibold'
                        : 'border-border-button hover:border-border-default bg-bg-component'
                    }`}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Для чего именно будете использовать платформу?
              </label>
              <Textarea
                value={intendedUse}
                onChange={(e) => setIntendedUse(e.target.value)}
                placeholder="Опишите ваши задачи или сценарии (например: поиск по договорам, база знаний команды)..."
                rows={3}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Какую главную проблему должна решить система?
              </label>
              <Textarea
                value={platformGoals}
                onChange={(e) => setPlatformGoals(e.target.value)}
                placeholder="Например: сократить время поиска информации с 30 минут до нескольких секунд..."
                rows={2}
              />
            </div>

            <div className="flex justify-end pt-4">
              <Button
                onClick={() => {
                  if (!purpose) {
                    message.warning('Укажите основную цель регистрации.');
                    return;
                  }
                  setStep(2);
                }}
                className="bg-accent-primary text-white hover:bg-accent-primary/90"
              >
                Далее
              </Button>
            </div>
          </div>
        )}

        {/* Step 2 */}
        {step === 2 && (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                <LucideBuilding className="w-4 h-4 text-accent-primary" />
                В какой компании вы работаете или работали? <span className="text-red-500">*</span>
              </label>
              <Input
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="Название компании или проекта..."
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Размер компании</label>
                <div className="flex flex-wrap gap-2">
                  {COMPANY_SIZES.map((sz) => (
                    <button
                      key={sz}
                      type="button"
                      onClick={() => setCompanySize(sz)}
                      className={`px-3 py-1.5 rounded-lg border text-xs ${
                        companySize === sz
                          ? 'border-accent-primary bg-accent-primary/10 font-semibold'
                          : 'border-border-button bg-bg-component'
                      }`}
                    >
                      {sz} чел.
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Сфера деятельности</label>
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-border-button bg-bg-component text-sm"
                >
                  {INDUSTRIES.map((ind) => (
                    <option key={ind} value={ind}>
                      {ind}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                <LucideBriefcase className="w-4 h-4 text-accent-primary" />
                Ваша должность / роль
              </label>
              <Input
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="Например: Архитектор ИИ, Руководитель отделом, Разработчик..."
              />
            </div>

            <div className="flex justify-between pt-4">
              <Button variant="outline" onClick={() => setStep(1)}>
                Назад
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={loading}
                className="bg-accent-primary text-white hover:bg-accent-primary/90 flex items-center gap-2"
              >
                <LucideCheckCircle2 className="w-4 h-4" />
                Завершить регистрацию
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
