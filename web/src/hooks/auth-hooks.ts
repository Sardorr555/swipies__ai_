import authorizationUtil from '@/utils/authorization-util';
import request from '@/utils/request';
import api from '@/utils/api';
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
      const handleOAuthLogin = async () => {
        try {
          // Remove "Bearer " prefix if present (backend sends JWT token without prefix)
          // We store it without prefix, and add prefix only when sending requests
          const token = auth.startsWith('Bearer ') ? auth.replace('Bearer ', '') : auth;

          // Save token WITHOUT "Bearer " prefix (same as regular login)
          // The prefix will be added automatically by getAuthorization() when making API requests
          localStorage.setItem('Authorization', token);
          authorizationUtil.setAuthorization(token);

          // Verify token was saved correctly
          const savedToken = localStorage.getItem('Authorization');
          if (!savedToken || savedToken !== token) {
            console.error('OAuth callback: Failed to save authorization token, retrying...');
            localStorage.setItem('Authorization', token);
          }

          // Fetch user info using the saved token
          try {
            const { data: userInfoResponse } = await request.get(api.user_info);

            if (userInfoResponse && userInfoResponse.code === 0) {
              const userData = userInfoResponse.data;

              // Save user info and token to localStorage (matching regular login behavior)
              const userInfo = {
                avatar: userData.avatar,
                name: userData.nickname,
                email: userData.email,
              };

              authorizationUtil.setItems({
                Authorization: token,
                userInfo: JSON.stringify(userInfo),
                Token: token, // Use the same token for compatibility
              });

              console.log('OAuth callback: User data saved successfully');
            } else {
              console.warn('OAuth callback: Failed to fetch user info, but continuing with auth token');
            }
          } catch (userInfoError) {
            console.error('OAuth callback: Error fetching user info:', userInfoError);
            // Continue anyway - we have the auth token
          }

          // Trigger auth state update events
          window.dispatchEvent(new Event('auth-storage-change'));

          // Remove auth parameter from URL
          newQueryParameters.delete('auth');
          setSearchParams(newQueryParameters, { replace: true });

          // Navigate to knowledge page after ensuring token is saved
          // Use a small delay to ensure React state updates propagate
          setTimeout(() => {
            const verifyToken = localStorage.getItem('Authorization');
            if (verifyToken && verifyToken.trim().length > 0) {
              navigate('/knowledge', { replace: true });
            } else {
              // Fallback: try one more time
              localStorage.setItem('Authorization', token);
              navigate('/knowledge', { replace: true });
            }
          }, 100);
        } catch (error) {
          console.error('OAuth callback error:', error);
          message.error('Failed to complete OAuth login');
          navigate('/login');
        }
      };

      handleOAuthLogin();
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
  // Initialize state by checking localStorage immediately (synchronous)
  const [isLogin, setIsLogin] = useState<Nullable<boolean>>(() => {
    try {
      // Synchronous check on initial render - read directly from localStorage
      const storedAuth = localStorage.getItem('Authorization');
      const queryAuth = auth;
      const hasAuth = !!(storedAuth && storedAuth.trim().length > 0) || !!queryAuth;
      return hasAuth;
    } catch (e) {
      console.error('Error initializing auth state:', e);
      return null;
    }
  });

  // Check authentication status function
  const checkAuthStatus = useCallback(() => {
    try {
      // Always check localStorage directly for most up-to-date value
      const storedAuth = localStorage.getItem('Authorization');
      const queryAuth = auth;
      // Check if we have valid authorization (must be non-empty string)
      const hasAuth = !!(storedAuth && storedAuth.trim().length > 0) || !!queryAuth;
      setIsLogin(hasAuth);
      return hasAuth;
    } catch (e) {
      console.error('Error checking auth status:', e);
      return false;
    }
  }, [auth]);

  // Use useLayoutEffect for synchronous check before paint (runs on mount and when auth changes)
  useLayoutEffect(() => {
    checkAuthStatus();
  }, [checkAuthStatus]);

  // Continuously verify auth status, especially after OAuth callback
  useEffect(() => {
    const verifyAuth = () => {
      try {
        const storedAuth = localStorage.getItem('Authorization');
        const queryAuth = auth;
        const hasAuth = !!(storedAuth && storedAuth.trim().length > 0) || !!queryAuth;
        if (hasAuth !== isLogin) {
          setIsLogin(hasAuth);
        }
        return hasAuth;
      } catch (e) {
        console.error('Error in verifyAuth:', e);
        return false;
      }
    };

    // Immediate check
    verifyAuth();

    // Multiple delayed checks to catch rapid changes (like OAuth callback)
    const timeouts = [
      setTimeout(verifyAuth, 5),
      setTimeout(verifyAuth, 25),
      setTimeout(verifyAuth, 50),
      setTimeout(verifyAuth, 100),
    ];

    return () => {
      timeouts.forEach(clearTimeout);
    };
  }, [auth, isLogin]);

  // Listen to storage changes (for cross-tab updates and same-tab updates)
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'Authorization') {
        checkAuthStatus();
      }
    };

    // Custom event for same-tab localStorage changes (dispatched by setAuthorization)
    const handleCustomStorageChange = () => {
      // Use requestAnimationFrame to ensure DOM is ready
      requestAnimationFrame(() => {
        checkAuthStatus();
      });
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
