import authorizationUtil from '@/utils/authorization-util';
import { message } from 'antd';
import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'umi';

export const useOAuthCallback = () => {
  const [currentQueryParameters, setSearchParams] = useSearchParams();
  const error = currentQueryParameters.get('error');
  const newQueryParameters: URLSearchParams = useMemo(
    () => new URLSearchParams(currentQueryParameters.toString()),
    [currentQueryParameters],
  );
  const navigate = useNavigate();

  useEffect(() => {
    if (error) {
      message.error(error);
      setTimeout(() => {
        navigate('/login');
        newQueryParameters.delete('error');
        setSearchParams(newQueryParameters);
      }, 1000);
      return;
    }

    const auth = currentQueryParameters.get('auth');
    if (auth) {
      authorizationUtil.setAuthorization(auth);
      // Trigger immediate auth check by dispatching event
      window.dispatchEvent(new Event('auth-storage-change'));
      newQueryParameters.delete('auth');
      setSearchParams(newQueryParameters);
      // Small delay to ensure state updates propagate before navigation
      setTimeout(() => {
        navigate('/knowledge');
      }, 100);
    }
  }, [
    error,
    currentQueryParameters,
    newQueryParameters,
    navigate,
    setSearchParams,
  ]);

  console.debug(currentQueryParameters.get('auth'));
  return currentQueryParameters.get('auth');
};

export const useAuth = () => {
  const auth = useOAuthCallback();
  const [isLogin, setIsLogin] = useState<Nullable<boolean>>(null);

  // Check authentication status function
  const checkAuthStatus = useCallback(() => {
    const storedAuth = authorizationUtil.getAuthorization();
    const isAuthenticated = !!storedAuth || !!auth;
    setIsLogin(isAuthenticated);
  }, [auth]);

  // Use useLayoutEffect for synchronous check before paint (runs on mount and when auth changes)
  useLayoutEffect(() => {
    checkAuthStatus();
  }, [checkAuthStatus]);

  // Listen to storage changes (for cross-tab updates and same-tab updates)
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'Authorization') {
        checkAuthStatus();
      }
    };

    // Custom event for same-tab localStorage changes (dispatched by setAuthorization)
    const handleCustomStorageChange = () => {
      checkAuthStatus();
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('auth-storage-change', handleCustomStorageChange);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('auth-storage-change', handleCustomStorageChange);
    };
  }, [checkAuthStatus]);

  return { isLogin };
};
