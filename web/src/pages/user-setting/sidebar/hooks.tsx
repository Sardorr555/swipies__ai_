import { useLogout } from '@/hooks/use-login-request';
import { Routes } from '@/routes';
import authorizationUtil from '@/utils/authorization-util';
import { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router';

export const useHandleMenuClick = () => {
  const navigate = useNavigate();
  const [active, setActive] = useState<Routes>();
  const { logout } = useLogout();
  const location = useLocation();
  useEffect(() => {
    const path = (location.pathname.split('/')?.[2] || '') as Routes;
    if (path) {
      setActive(('/' + path) as Routes);
    }
  }, [location]);

  const handleMenuClick = useCallback(
    (key: Routes) => () => {
      if (key === Routes.Logout) {
        logout();
      } else if (key === Routes.Ads) {
        const token = authorizationUtil.getAuthorization();
        const authQuery = token ? `?auth=${encodeURIComponent(token)}` : '';
        const hostname =
          typeof window !== 'undefined'
            ? window.location.hostname.toLowerCase()
            : '';
        const isLocal = hostname === 'localhost' || hostname === '127.0.0.1';
        const targetUrl = isLocal
          ? `/ads${authQuery}`
          : `${window.location.protocol}//ads.swipies.app/${authQuery}`;
        window.open(targetUrl, '_blank', 'noopener,noreferrer');
      } else {
        setActive(key);
        navigate(`${Routes.UserSetting}${key}`);
      }
    },
    [logout, navigate],
  );

  return { handleMenuClick, active, setActive };
};
