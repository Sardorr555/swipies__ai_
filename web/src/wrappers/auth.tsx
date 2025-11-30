import { useAuth } from '@/hooks/auth-hooks';
import { redirectToLogin } from '@/utils/authorization-util';
import { useEffect, useLayoutEffect, useState } from 'react';
import { Outlet, useLocation } from 'umi';

export default () => {
  const { isLogin } = useAuth();
  const location = useLocation();
  const [hasToken, setHasToken] = useState<boolean | null>(null);

  // Synchronous check on mount - read localStorage directly
  // This runs before paint, so we can check auth state immediately
  useLayoutEffect(() => {
    const checkToken = () => {
      try {
        // Check if token exists in localStorage (stored without "Bearer " prefix)
        const token = localStorage.getItem('Authorization');
        const tokenExists = !!token && token.trim().length > 0;
        setHasToken(tokenExists);
        return tokenExists;
      } catch (e) {
        console.error('Error checking auth token:', e);
        setHasToken(false);
        return false;
      }
    };
    
    checkToken();
  }, [location.pathname]);

  // Also check when isLogin state changes
  useEffect(() => {
    const token = localStorage.getItem('Authorization');
    const tokenExists = !!token && token.trim().length > 0;
    if (tokenExists !== hasToken) {
      setHasToken(tokenExists);
    }
  }, [isLogin, hasToken]);

  // Listen for storage changes (OAuth callback, logout, etc.)
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'Authorization') {
        const tokenExists = !!e.newValue && e.newValue.trim().length > 0;
        setHasToken(tokenExists);
      }
    };

    const handleCustomStorageChange = () => {
      const token = localStorage.getItem('Authorization');
      const tokenExists = !!token && token.trim().length > 0;
      setHasToken(tokenExists);
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('auth-storage-change', handleCustomStorageChange);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('auth-storage-change', handleCustomStorageChange);
    };
  }, []);

  // Determine authentication status
  // User is authenticated if:
  // 1. isLogin is true (from useAuth hook), OR
  // 2. hasToken is true (token exists in localStorage)
  const isAuthenticated = isLogin === true || hasToken === true;
  
  // User is NOT authenticated only if:
  // 1. isLogin is explicitly false, AND
  // 2. hasToken is explicitly false (no token in localStorage)
  const isNotAuthenticated = isLogin === false && hasToken === false;

  // Render content if authenticated
  if (isAuthenticated) {
    return <Outlet />;
  }

  // Show loading state while checking (null means still checking)
  if (hasToken === null && isLogin === null) {
    return <></>;
  }

  // Handle redirect when not authenticated
  // Give it a moment to ensure token isn't being set asynchronously
  useEffect(() => {
    if (isNotAuthenticated) {
      const timeoutId = setTimeout(() => {
        const finalToken = localStorage.getItem('Authorization');
        if (!finalToken || finalToken.trim().length === 0) {
          redirectToLogin();
        }
      }, 100);
      return () => clearTimeout(timeoutId);
    }
  }, [isNotAuthenticated]);

  return <></>;
};
