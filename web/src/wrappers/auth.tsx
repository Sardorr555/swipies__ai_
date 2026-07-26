import { useAuth } from '@/hooks/auth-hooks';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';
import { redirectToLogin } from '@/utils/authorization-util';
import { Outlet } from 'react-router';
import { OnboardingModal } from '@/components/onboarding-modal';

export default function AuthWrapper() {
  const { isLogin } = useAuth();
  const { data: userInfo } = useFetchUserInfo();

  if (isLogin === true) {
    return (
      <>
        <Outlet />
        <OnboardingModal userInfo={userInfo} />
      </>
    );
  } else if (isLogin === false) {
    redirectToLogin();
  }

  return <></>;
}
