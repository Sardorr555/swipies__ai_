import message from '@/components/ui/message';
import { Authorization } from '@/constants/authorization';
import userService, {
  getLoginChannels,
  loginWithChannel,
} from '@/services/user-service';
import {
  default as authorizationUtil,
  redirectToLogin,
  default as storage,
} from '@/utils/authorization-util';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router';
import { useSaveSetting } from './use-user-setting-request';

export interface ILoginRequestBody {
  email: string;
  password: string;
}

export interface IRegisterRequestBody extends ILoginRequestBody {
  nickname: string;
  referred_by_id?: string;
}

export interface ILoginChannel {
  channel: string;
  display_name: string;
  icon: string;
}

export const useLoginChannels = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['loginChannels'],
    queryFn: async () => {
      const { data: res = {} } = await getLoginChannels();
      return res.data || [];
    },
  });

  return { channels: data as ILoginChannel[], loading: isLoading };
};

export const useLoginWithChannel = () => {
  const [searchParams] = useSearchParams();
  const ref = searchParams.get('ref') || '';
  const { isPending: loading, mutateAsync } = useMutation({
    mutationKey: ['loginWithChannel'],
    mutationFn: async (channel: string) => {
      loginWithChannel(channel, ref);
      return Promise.resolve();
    },
  });

  return { loading, login: mutateAsync };
};

export const useLogin = () => {
  const { saveSetting } = useSaveSetting(true);
  const {
    data,
    isPending: loading,
    mutateAsync,
  } = useMutation({
    mutationKey: ['login'],
    mutationFn: async (params: { email: string; password: string }) => {
      const { data: res = {}, response } = await userService.login(params);
      if (res.code === 0) {
        saveSetting({ language: storage.getLanguage() });
        const { data } = res;
        const authorization = response.headers.get(Authorization);
        const token = data.access_token;
        const userInfo = {
          avatar: data.avatar,
          name: data.nickname,
          email: data.email,
        };
        authorizationUtil.setItems({
          Authorization: authorization,
          userInfo: JSON.stringify(userInfo),
          Token: token,
        });
      }
      return res;
    },
  });

  return { data, loading, login: mutateAsync };
};

export const useRegister = () => {
  const { t } = useTranslation();

  const {
    data,
    isPending: loading,
    mutateAsync,
  } = useMutation({
    mutationKey: ['register'],
    mutationFn: async (params: {
      email: string;
      password: string;
      nickname: string;
      phone?: string;
      referred_by_id?: string;
    }) => {
      const { data = {} } = await userService.register(params);
      if (data.code === 0) {
        message.success(data.message || t('message.registered'));
      } else if (
        data.message &&
        data.message.includes('registration is disabled')
      ) {
        message.error(
          t('message.registerDisabled') || 'User registration is disabled',
        );
      }
      return data;
    },
  });

  return { data, loading, register: mutateAsync };
};

export const useActivateAccount = () => {
  const { saveSetting } = useSaveSetting(true);
  const {
    data,
    isPending: loading,
    mutateAsync,
  } = useMutation({
    mutationKey: ['activateAccount'],
    mutationFn: async (params: { email: string; code: string }) => {
      const { data: res = {}, response } = await userService.activateAccount(params);
      if (res.code === 0) {
        message.success(res.message || 'Account activated successfully!');
        if (res.data) {
          saveSetting({ language: storage.getLanguage() });
          const authorization = response?.headers?.get(Authorization) || response?.headers?.get('authorization');
          const token = res.data.access_token || authorization;
          const userInfo = {
            avatar: res.data.avatar,
            name: res.data.nickname,
            email: res.data.email,
          };
          authorizationUtil.setItems({
            Authorization: authorization,
            userInfo: JSON.stringify(userInfo),
            Token: token,
          });
        }
      } else {
        message.error(res.message || 'Failed to activate account.');
      }
      return res;
    },
  });

  return { data, loading, activateAccount: mutateAsync };
};

export const useResendActivationCode = () => {
  const {
    data,
    isPending: loading,
    mutateAsync,
  } = useMutation({
    mutationKey: ['resendActivationCode'],
    mutationFn: async (params: { email: string }) => {
      const { data: res = {} } = await userService.resendActivationCode(params);
      if (res.code === 0) {
        message.success(res.message || 'New activation code sent to your email.');
      } else {
        message.error(res.message || 'Failed to resend code.');
      }
      return res;
    },
  });

  return { data, loading, resendActivationCode: mutateAsync };
};

export const useLogout = () => {
  const { t } = useTranslation();
  const {
    data,
    isPending: loading,
    mutateAsync,
  } = useMutation({
    mutationKey: ['logout'],
    mutationFn: async () => {
      const { data = {} } = await userService.logout();
      if (data.code === 0) {
        message.success(t('message.logout'));
        authorizationUtil.removeAll();
        redirectToLogin();
      }
      return data.code;
    },
  });

  return { data, loading, logout: mutateAsync };
};
