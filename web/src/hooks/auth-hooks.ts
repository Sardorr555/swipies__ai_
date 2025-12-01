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
          console.log('[OAuth] ==================== OAuth Callback Start ====================');
          console.log('[OAuth] Received auth token from URL, length:', auth.length);
          console.log('[OAuth] Token preview:', auth.substring(0, 20) + '...');

          // Remove "Bearer " prefix if present (backend sends JWT token without prefix)
          const token = auth.startsWith('Bearer ') ? auth.replace('Bearer ', '') : auth;
          console.log('[OAuth] Processed token, length:', token.length);

          // CRITICAL FIX: Remove auth parameter from URL FIRST!
          // This ensures that getAuthorization() will use localStorage instead of URL param
          console.log('[OAuth] Removing auth parameter from URL...');
          newQueryParameters.delete('auth');
          setSearchParams(newQueryParameters, { replace: true });
          console.log('[OAuth] ✓ Auth parameter removed from URL');

          // Save token WITHOUT "Bearer " prefix (same as regular login)
          console.log('[OAuth] Saving token to localStorage...');
          localStorage.setItem('Authorization', token);
          authorizationUtil.setAuthorization(token);
          console.log('[OAuth] ✓ Token saved to localStorage');

          // Verify token was saved correctly
          const savedToken = localStorage.getItem('Authorization');
          if (!savedToken || savedToken !== token) {
            console.error('[OAuth] ✗ Token verification FAILED! Retrying...');
            localStorage.setItem('Authorization', token);
            const recheck = localStorage.getItem('Authorization');
            console.log('[OAuth] Recheck result:', recheck === token ? '✓ Success' : '✗ Still failed');
          } else {
            console.log('[OAuth] ✓ Token verified successfully in localStorage');
          }

          // Small delay to ensure localStorage is written and URL is updated
          await new Promise(resolve => setTimeout(resolve, 50));
          console.log('[OAuth] Delay complete, proceeding to fetch user info...');

          // Fetch user info using the saved token from localStorage
          try {
            console.log('[OAuth] Making request to /v1/user/info...');
            const { data: userInfoResponse } = await request.get(api.user_info);
            console.log('[OAuth] User info response received:', userInfoResponse);

            if (userInfoResponse && userInfoResponse.code === 0) {
              const userData = userInfoResponse.data;
              console.log('[OAuth] ✓ User data received successfully');
              console.log('[OAuth] User email:', userData.email);
              console.log('[OAuth] User nickname:', userData.nickname);

              // Save user info and token to localStorage (matching regular login behavior)
              const userInfo = {
                avatar: userData.avatar,
                name: userData.nickname,
                email: userData.email,
              };

              console.log('[OAuth] Saving complete user data to localStorage...');
              authorizationUtil.setItems({
                Authorization: token,
                userInfo: JSON.stringify(userInfo),
                Token: token,
              });

              console.log('[OAuth] ✓ User data saved to localStorage successfully');
              console.log('[OAuth] localStorage keys:', Object.keys(localStorage).filter(k => ['Authorization', 'userInfo', 'Token'].includes(k)));
            } else {
              console.warn('[OAuth] ✗ Failed to fetch user info');
              console.warn('[OAuth] Response code:', userInfoResponse?.code);
              console.warn('[OAuth] Response message:', userInfoResponse?.message);
              console.warn('[OAuth] Continuing with auth token only (no user info)');
            }
          } catch (userInfoError: any) {
            console.error('[OAuth] ✗ Error fetching user info:', userInfoError);
            console.error('[OAuth] Error message:', userInfoError?.message);
            console.error('[OAuth] Error response status:', userInfoError?.response?.status);
            console.error('[OAuth] Error response data:', userInfoError?.data);
            console.error('[OAuth] Full error:', JSON.stringify(userInfoError, null, 2));
            // Continue anyway - we have the auth token
            console.log('[OAuth] Continuing anyway - auth token is saved');
          }

          // Trigger auth state update events
          window.dispatchEvent(new Event('auth-storage-change'));
          console.log('[OAuth] ✓ Dispatched auth-storage-change event');

          // Final verification before navigation
          const finalToken = localStorage.getItem('Authorization');
          const finalUserInfo = localStorage.getItem('userInfo');
          const finalTokenItem = localStorage.getItem('Token');
          console.log('[OAuth] ==================== Final State Check ====================');
          console.log('[OAuth] Authorization in localStorage:', !!finalToken, 'Length:', finalToken?.length);
          console.log('[OAuth] userInfo in localStorage:', !!finalUserInfo);
          console.log('[OAuth] Token in localStorage:', !!finalTokenItem);
          console.log('[OAuth] All localStorage items:', Object.keys(localStorage));

          if (!finalToken || finalToken.trim().length === 0) {
            console.error('[OAuth] ✗ CRITICAL: No token in localStorage before navigation!');
            throw new Error('Token not found in localStorage after save');
          }

          console.log('[OAuth] ✓ All checks passed, navigating to /knowledge');
          console.log('[OAuth] ==================== OAuth Callback End ====================');
          navigate('/knowledge', { replace: true });

        } catch (error: any) {
          console.error('[OAuth] ==================== CRITICAL ERROR ====================');
          console.error('[OAuth] Error in OAuth callback:', error);
          console.error('[OAuth] Error message:', error?.message);
          console.error('[OAuth] Error stack:', error?.stack);
          console.error('[OAuth] ===========================================================');
          message.error('Failed to complete OAuth login: ' + (error?.message || 'Unknown error'));
          setTimeout(() => {
            console.log('[OAuth] Redirecting to /login after error');
            navigate('/login');
          }, 1000);
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
      console.log('[Auth] Initial auth state:', { hasAuth, hasStoredAuth: !!storedAuth, hasQueryAuth: !!queryAuth });
      return hasAuth;
    } catch (e) {
      console.error('[Auth] Error initializing auth state:', e);
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
      console.log('[Auth] Auth status checked:', { hasAuth, hasStoredAuth: !!storedAuth, hasQueryAuth: !!queryAuth });
      return hasAuth;
    } catch (e) {
      console.error('[Auth] Error checking auth status:', e);
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
          console.log('[Auth] Auth state changed:', isLogin, '->', hasAuth);
          setIsLogin(hasAuth);
        }
        return hasAuth;
      } catch (e) {
        console.error('[Auth] Error in verifyAuth:', e);
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
        console.log('[Auth] Storage change detected for Authorization key');
        checkAuthStatus();
      }
    };

    // Custom event for same-tab localStorage changes (dispatched by setAuthorization)
    const handleCustomStorageChange = () => {
      console.log('[Auth] Custom auth-storage-change event received');
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
