import SvgIcon from '@/components/svg-icon';
import message from '@/components/ui/message';
import { useAuth } from '@/hooks/auth-hooks';
import {
  useActivateAccount,
  useLogin,
  useLoginChannels,
  useLoginWithChannel,
  useRegister,
  useResendActivationCode,
} from '@/hooks/use-login-request';
import { useSystemConfig } from '@/hooks/use-system-request';
import { rsaPsw } from '@/utils';
import { useContext, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useSearchParams } from 'react-router';

import Spotlight from '@/components/spotlight';
import { Button, ButtonLoading } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { BRAND } from '@/constants/branding';
import { cn } from '@/lib/utils';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm, UseFormReturn } from 'react-hook-form';
import { z } from 'zod';
import { NICKNAME_PATTERN } from '../user-setting/profile/constants';
import { BgSvg } from './bg';
import FlipCard3D, { FlipFaceContext } from './card';
import './index.less';

type LoginFormContentProps = {
  isLoginPage: boolean;
  title: string;
  form: UseFormReturn<any>;
  loading: boolean;
  onCheck: (params: any) => Promise<void>;
  changeTitle: () => void;
  registerEnabled: boolean;
  channels: { channel: string; icon?: string; display_name: string }[];
  handleLoginWithChannel: (channel: string) => void;
  t: ReturnType<typeof useTranslation>['t'];
  disablePasswordLogin?: boolean;
};

function LoginFormContent({
  isLoginPage,
  title,
  form,
  loading,
  onCheck,
  changeTitle,
  registerEnabled,
  channels,
  handleLoginWithChannel,
  t,
  disablePasswordLogin,
}: LoginFormContentProps) {
  const face = useContext(FlipFaceContext);
  const isActiveFace = isLoginPage ? face === 'front' : face === 'back';

  return (
    <div className="flex flex-col items-center justify-center w-full">
      <div className="text-center mb-8">
        <h2 className="text-xl font-semibold text-text-primary">
          {title === 'login' ? t('loginTitle') : t('signUpTitle')}
        </h2>
      </div>
      <div className=" w-full max-w-[540px] bg-bg-component backdrop-blur-sm rounded-2xl shadow-xl pt-14 pl-10 pr-10 pb-2 border border-border-button ">
        {!disablePasswordLogin && (
          <Form {...form}>
            <form
              className="flex flex-col gap-8 text-text-primary "
              data-testid="auth-form"
              data-active={isActiveFace ? 'true' : undefined}
              onSubmit={form.handleSubmit(onCheck)}
            >
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>{t('emailLabel')}</FormLabel>
                    <FormControl>
                      <Input
                        data-testid="auth-email"
                        placeholder={t('emailPlaceholder')}
                        autoComplete="email"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {title === 'register' && (
                <FormField
                  control={form.control}
                  name="nickname"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel required>{t('nicknameLabel')}</FormLabel>
                      <FormControl>
                        <Input
                          data-testid="auth-nickname"
                          placeholder={t('nicknamePlaceholder')}
                          autoComplete="username"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              {title === 'register' && (
                <FormField
                  control={form.control}
                  name="phone"
                  render={({ field }) => {
                    const cleanPhone = (field.value || '').replace(
                      /[^\d+]/g,
                      '',
                    );
                    let country = null;
                    if (
                      cleanPhone.startsWith('+998') ||
                      cleanPhone.startsWith('998')
                    ) {
                      country = { flag: '🇺🇿', name: 'Uzbekistan' };
                    } else if (
                      cleanPhone.startsWith('+7') ||
                      cleanPhone.startsWith('7')
                    ) {
                      country = { flag: '🇷🇺', name: 'Russia/Kazakhstan' };
                    } else if (
                      cleanPhone.startsWith('+86') ||
                      cleanPhone.startsWith('86')
                    ) {
                      country = { flag: '🇨🇳', name: 'China' };
                    } else if (
                      cleanPhone.startsWith('+996') ||
                      cleanPhone.startsWith('996')
                    ) {
                      country = { flag: '🇰🇬', name: 'Kyrgyzstan' };
                    } else if (
                      cleanPhone.startsWith('+992') ||
                      cleanPhone.startsWith('992')
                    ) {
                      country = { flag: '🇹🇯', name: 'Tajikistan' };
                    } else if (
                      cleanPhone.startsWith('+1') ||
                      cleanPhone.startsWith('1')
                    ) {
                      country = { flag: '🇺🇸', name: 'USA/Canada' };
                    } else if (
                      cleanPhone.startsWith('+380') ||
                      cleanPhone.startsWith('380')
                    ) {
                      country = { flag: '🇺🇦', name: 'Ukraine' };
                    } else if (
                      cleanPhone.startsWith('+375') ||
                      cleanPhone.startsWith('375')
                    ) {
                      country = { flag: '🇧🇾', name: 'Belarus' };
                    } else if (
                      cleanPhone.startsWith('+44') ||
                      cleanPhone.startsWith('44')
                    ) {
                      country = { flag: '🇬🇧', name: 'United Kingdom' };
                    } else if (cleanPhone.startsWith('+')) {
                      country = { flag: '🌐', name: 'International' };
                    }

                    return (
                      <FormItem>
                        <FormLabel required>
                          {t('phoneLabel')}{' '}
                          {country && (
                            <span className="ml-1 text-xs text-text-secondary">
                              ({country.flag} {country.name})
                            </span>
                          )}
                        </FormLabel>
                        <FormControl>
                          <div className="relative flex items-center">
                            {country && (
                              <span className="absolute left-3 text-lg select-none">
                                {country.flag}
                              </span>
                            )}
                            <Input
                              data-testid="auth-phone"
                              placeholder={t('phonePlaceholder')}
                              type="tel"
                              className={country ? 'pl-9' : ''}
                              {...field}
                            />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    );
                  }}
                />
              )}

              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel required>{t('passwordLabel')}</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          data-testid="auth-password"
                          type={'password'}
                          placeholder={t('passwordPlaceholder')}
                          autoComplete={
                            title === 'login'
                              ? 'current-password'
                              : 'new-password'
                          }
                          {...field}
                        />
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {title === 'register' && (
                <FormField
                  control={form.control}
                  name="confirmPassword"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel required>
                        {t('confirmPasswordLabel')}
                      </FormLabel>
                      <FormControl>
                        <Input
                          data-testid="auth-confirm-password"
                          type="password"
                          placeholder={t('confirmPasswordPlaceholder')}
                          autoComplete="new-password"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              {title === 'register' && (
                <FormField
                  control={form.control}
                  name="acceptTerms"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <div className="flex gap-2 items-start">
                          <Checkbox
                            data-testid="auth-accept-terms"
                            checked={field.value}
                            onCheckedChange={(checked) => {
                              field.onChange(checked);
                            }}
                            className="mt-0.5"
                          />
                          <FormLabel
                            className={cn(
                              'text-sm leading-snug cursor-pointer hover:text-text-primary',
                              {
                                'text-text-disabled': !field.value,
                                'text-text-primary': field.value,
                              },
                            )}
                          >
                            {t('termsLabel')}{' '}
                            <Link
                              to="/privacy-policy"
                              target="_blank"
                              className="text-accent-primary/90 hover:text-accent-primary underline underline-offset-2 transition-colors duration-200"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {t('termsLink')}
                            </Link>
                          </FormLabel>
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              {title === 'login' && (
                <FormField
                  control={form.control}
                  name="remember"
                  render={({ field }) => (
                    <FormItem>
                      <div className="flex gap-2 group">
                        <FormControl>
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={(checked) => {
                              field.onChange(checked);
                            }}
                            className="group-hover:border-border-default group-hover:bg-border-button"
                          />
                        </FormControl>
                        <FormLabel
                          className={cn('cursor-pointer', {
                            'text-text-disabled': !field.value,
                            'text-text-primary': field.value,
                          })}
                        >
                          {t('rememberMe')}
                        </FormLabel>
                      </div>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}
              <ButtonLoading
                data-testid="auth-submit"
                type="submit"
                loading={loading}
                className="bg-metallic-gradient border-b-[#00BEB4] border-b-2 hover:bg-metallic-gradient hover:border-b-[#02bcdd] w-full my-8"
              >
                {title === 'login' ? t('login') : t('continue')}
              </ButtonLoading>
            </form>
          </Form>
        )}

        {channels && channels.length > 0 && (
          <div className="w-full mt-6">
            {!disablePasswordLogin && (
              <div className="relative flex py-4 items-center justify-center">
                <div className="flex-grow border-t border-border-button"></div>
                <span className="flex-shrink mx-4 text-xs text-text-disabled uppercase tracking-wider">
                  {t('or')}
                </span>
                <div className="flex-grow border-t border-border-button"></div>
              </div>
            )}
            <div className="flex flex-col gap-3 w-full">
              {channels.map((item) => (
                <Button
                  variant={'outline'}
                  key={item.channel}
                  onClick={() => handleLoginWithChannel(item.channel)}
                  className="w-full h-11 flex items-center justify-center gap-3 border border-border-button hover:bg-border-button/40 rounded-xl transition-all duration-200"
                >
                  <SvgIcon name={item.icon || 'sso'} width={20} height={20} />
                  <span className="font-medium text-sm text-text-primary">
                    {title === 'login'
                      ? t('signInWith', { name: item.display_name })
                      : t('signUpWith', { name: item.display_name })}
                  </span>
                </Button>
              ))}
            </div>
          </div>
        )}

        {!disablePasswordLogin && title === 'login' && registerEnabled && (
          <div className="mt-10 text-right">
            <p className="text-text-disabled text-sm">
              {t('signInTip')}
              <Button
                data-testid="auth-toggle-register"
                variant={'transparent'}
                onClick={changeTitle}
                className="text-accent-primary/90 hover:text-accent-primary hover:bg-transparent font-medium border-none transition-colors duration-200"
              >
                {t('signUp')}
              </Button>
            </p>
          </div>
        )}
        {!disablePasswordLogin && title === 'register' && (
          <div className="mt-10 text-right">
            <p className="text-text-disabled text-sm">
              {t('signUpTip')}
              <Button
                data-testid="auth-toggle-login"
                variant={'transparent'}
                onClick={changeTitle}
                className="text-accent-primary/90 hover:text-accent-primary hover:bg-transparent font-medium border-none transition-colors duration-200"
              >
                {t('login')}
              </Button>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

type ActivationFormContentProps = {
  email: string;
  onSuccess: () => void;
  onCancel: () => void;
};

function ActivationFormContent({
  email,
  onSuccess,
  onCancel,
}: ActivationFormContentProps) {
  const [code, setCode] = useState('');
  const [cooldown, setCooldown] = useState(0);
  const { activateAccount, loading: activating } = useActivateAccount();
  const { resendActivationCode, loading: resending } = useResendActivationCode();

  useEffect(() => {
    let timer: any;
    if (cooldown > 0) {
      timer = setInterval(() => {
        setCooldown((prev) => prev - 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [cooldown]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code || code.length < 6) {
      message.error('Please enter a 6-digit activation code.');
      return;
    }
    const res = await activateAccount({ email, code });
    if (res?.code === 0) {
      onSuccess();
    }
  };

  const handleResend = async () => {
    if (cooldown > 0 || resending) return;
    const res = await resendActivationCode({ email });
    if (res?.code === 0) {
      setCooldown(60);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center w-full">
      <div className="text-center mb-8">
        <h2 className="text-xl font-semibold text-text-primary">
          Verify Your Email
        </h2>
        <p className="text-sm text-text-secondary mt-1 max-w-sm mx-auto">
          We sent a 6-digit activation code to{' '}
          <span className="font-semibold text-accent-primary">{email}</span>
        </p>
      </div>
      <div className="w-full max-w-[540px] bg-bg-component backdrop-blur-sm rounded-2xl shadow-xl pt-10 pl-10 pr-10 pb-8 border border-border-button">
        <form onSubmit={handleSubmit} className="flex flex-col gap-6 text-text-primary">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-text-primary">
              Activation Code
            </label>
            <Input
              type="text"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              placeholder="123456"
              className="text-center tracking-[0.5em] text-2xl font-bold h-14"
              autoFocus
            />
          </div>

          <ButtonLoading
            type="submit"
            loading={activating}
            className="bg-metallic-gradient border-b-[#00BEB4] border-b-2 hover:bg-metallic-gradient hover:border-b-[#02bcdd] w-full h-11"
          >
            Activate Account & Continue
          </ButtonLoading>

          <div className="flex items-center justify-between text-sm pt-2">
            <Button
              type="button"
              variant="transparent"
              disabled={cooldown > 0 || resending}
              onClick={handleResend}
              className="text-accent-primary hover:underline p-0 h-auto font-medium"
            >
              {cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend Code'}
            </Button>

            <Button
              type="button"
              variant="transparent"
              onClick={onCancel}
              className="text-text-secondary hover:text-text-primary p-0 h-auto"
            >
              Back to Login
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

const Login = () => {
  const [title, setTitle] = useState('login');
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const refFromQuery = searchParams.get('ref') || searchParams.get('referrer') || searchParams.get('utm_content') || '';
  useEffect(() => {
    if (refFromQuery) {
      try {
        localStorage.setItem('swipies_referrer', refFromQuery);
      } catch {}
    }
  }, [refFromQuery]);
  const ref = refFromQuery || (typeof window !== 'undefined' ? localStorage.getItem('swipies_referrer') || '' : '');
  const [activationEmail, setActivationEmail] = useState<string | null>(null);
  const { login, loading: signLoading } = useLogin();
  const { register, loading: registerLoading } = useRegister();
  const { channels, loading: channelsLoading } = useLoginChannels();
  const { login: loginWithChannel, loading: loginWithChannelLoading } =
    useLoginWithChannel();
  const { t } = useTranslation('translation', { keyPrefix: 'login' });
  const { t: tSetting } = useTranslation('translation', {
    keyPrefix: 'setting',
  });
  const [isLoginPage, setIsLoginPage] = useState(true);

  const loading =
    signLoading ||
    registerLoading ||
    channelsLoading ||
    loginWithChannelLoading;
  const { config } = useSystemConfig();
  const registerEnabled = config?.registerEnabled !== 0;

  const { isLogin } = useAuth();
  useEffect(() => {
    if (isLogin) {
      navigate('/');
    }
  }, [isLogin, navigate]);

  const handleLoginWithChannel = async (channel: string) => {
    await loginWithChannel(channel);
  };

  const changeTitle = () => {
    setIsLoginPage(title !== 'login');
    if (title === 'login' && !registerEnabled) {
      return;
    }

    setTimeout(() => {
      setTitle(title === 'login' ? 'register' : 'login');
    }, 200);
  };

  const FormSchema = z
    .object({
      nickname: z.string().optional(),
      email: z
        .string()
        .email()
        .min(1, { message: t('emailPlaceholder') }),
      password: z.string().min(1, { message: t('passwordPlaceholder') }),
      remember: z.boolean().optional(),
      phone: z.string().optional(),
      confirmPassword: z.string().optional(),
      acceptTerms: z.boolean().optional(),
    })
    .superRefine((data, ctx) => {
      if (title === 'register') {
        if (!data.nickname) {
          ctx.addIssue({
            path: ['nickname'],
            message: 'nicknamePlaceholder',
            code: z.ZodIssueCode.custom,
          });
        } else if (!NICKNAME_PATTERN.test(data.nickname)) {
          ctx.addIssue({
            path: ['nickname'],
            message: tSetting('usernameInvalidCharacters'),
            code: z.ZodIssueCode.custom,
          });
        }
        if (!data.phone) {
          ctx.addIssue({
            path: ['phone'],
            message: 'phonePlaceholder',
            code: z.ZodIssueCode.custom,
          });
        }
        const pwd = data.password || '';
        if (pwd.length < 8) {
          ctx.addIssue({
            path: ['password'],
            message: 'Password must be at least 8 characters long',
            code: z.ZodIssueCode.custom,
          });
        } else if (!/[A-Za-z]/.test(pwd) || !/[0-9]/.test(pwd)) {
          ctx.addIssue({
            path: ['password'],
            message: 'Password must contain both letters and numbers',
            code: z.ZodIssueCode.custom,
          });
        } else if (
          ['123456', '12345678', '123456789', 'password', 'qwerty', '12345', '1234567'].includes(
            pwd.toLowerCase(),
          )
        ) {
          ctx.addIssue({
            path: ['password'],
            message: 'This password is too common and weak',
            code: z.ZodIssueCode.custom,
          });
        }
        if (!data.confirmPassword) {
          ctx.addIssue({
            path: ['confirmPassword'],
            message: 'confirmPasswordPlaceholder',
            code: z.ZodIssueCode.custom,
          });
        } else if (data.confirmPassword !== data.password) {
          ctx.addIssue({
            path: ['confirmPassword'],
            message: 'passwordMismatch',
            code: z.ZodIssueCode.custom,
          });
        }
        if (!data.acceptTerms) {
          ctx.addIssue({
            path: ['acceptTerms'],
            message: t('termsRequired'),
            code: z.ZodIssueCode.custom,
          });
        }
      }
    });
  type FormValues = z.infer<typeof FormSchema>;
  const form = useForm<FormValues>({
    defaultValues: {
      nickname: '',
      email: '',
      password: '',
      remember: false,
      phone: '',
      confirmPassword: '',
      acceptTerms: false,
    },
    resolver: zodResolver(FormSchema),
  });

  const onCheck = async (params: FormValues) => {
    try {
      const rsaPassWord = rsaPsw(params.password) as string;

      if (title === 'login') {
        const res = await login({
          email: `${params.email}`.trim(),
          password: rsaPassWord,
        });
        if (res?.code === 0) {
          navigate('/');
        } else if (res?.code === 403 && (res?.data?.requires_activation || res?.message?.includes('not activated'))) {
          setActivationEmail(`${params.email}`.trim());
        }
      } else {
        const res = await register({
          nickname: params.nickname,
          email: params.email,
          password: rsaPassWord,
          phone: params.phone,
          referred_by_id: ref,
        });
        if (res?.code === 0 && res?.data?.requires_activation) {
          setActivationEmail(params.email);
        } else if (res?.code === 0) {
          setTitle('login');
        }
      }
    } catch {
      // Failed to login or register
    }
  };

  return (
    <>
      <Spotlight opcity={0.4} coverage={60} color={'rgb(128, 255, 248)'} />
      <Spotlight
        opcity={0.3}
        coverage={12}
        X={'10%'}
        Y={'-10%'}
        color={'rgb(128, 255, 248)'}
      />
      <Spotlight
        opcity={0.3}
        coverage={12}
        X={'90%'}
        Y={'-10%'}
        color={'rgb(128, 255, 248)'}
      />
      <div className=" h-[inherit] relative overflow-auto">
        <BgSvg isPaused />

        <div className="z-20 absolute top-3 flex flex-col items-center mb-12 w-full text-text-primary">
          <div className="flex items-center mb-4 w-full pl-10 pt-10 ">
            <div className="w-12 h-12 p-2 rounded-lg flex items-center justify-center mr-3">
              <img
                src={'/logo.svg'}
                alt="logo"
                className="size-8 mr-[12] cursor-pointer"
              />
            </div>
            <div className="text-xl font-bold self-center">{BRAND.name}</div>
          </div>
        </div>
        <div className="relative z-10 flex flex-col items-center justify-center min-h-[1250px] px-4 sm:px-6 lg:px-8 py-8">
          {activationEmail ? (
            <ActivationFormContent
              email={activationEmail}
              onSuccess={() => {
                navigate('/');
              }}
              onCancel={() => setActivationEmail(null)}
            />
          ) : (
            <FlipCard3D isLoginPage={isLoginPage}>
              <LoginFormContent
                isLoginPage={isLoginPage}
                title={title}
                form={form}
                loading={loading}
                onCheck={onCheck}
                changeTitle={changeTitle}
                registerEnabled={registerEnabled}
                channels={channels || []}
                handleLoginWithChannel={handleLoginWithChannel}
                t={t}
                disablePasswordLogin={!!config?.disablePasswordLogin}
              />
            </FlipCard3D>
          )}
        </div>
      </div>
    </>
  );
};

export default Login;
