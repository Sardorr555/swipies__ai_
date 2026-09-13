import { Authorization, Token, UserInfo } from '@/constants/authorization';
import { getSearchValue } from './common-util';

export const AUTH_COOKIE_NAME = 'swipies_auth_token';
export const LOGGED_IN_COOKIE_NAME = 'swipies_logged_in';
const KeySet = [Authorization, Token, UserInfo];

/**
 * Resolves the parent root domain for cookies (e.g. '.swipies.app')
 * so that app.swipies.app, demo.swipies.app, and ads.swipies.app share sessions.
 */
export function getRootDomain(): string {
  if (typeof window === 'undefined') return '';
  const hostname = window.location.hostname.toLowerCase();
  if (
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    /^(?:\d{1,3}\.){3}\d{1,3}$/.test(hostname)
  ) {
    return '';
  }
  if (hostname.endsWith('swipies.app')) {
    return '.swipies.app';
  }
  const parts = hostname.split('.');
  if (parts.length >= 2) {
    return '.' + parts.slice(-2).join('.');
  }
  return '';
}

export function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(
    new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)'),
  );
  return match ? decodeURIComponent(match[1]) : null;
}

export function setCookie(name: string, value: string, days = 30) {
  if (typeof document === 'undefined') return;
  const rootDomain = getRootDomain();
  const domainPart = rootDomain ? `; domain=${rootDomain}` : '';
  const securePart =
    typeof window !== 'undefined' && window.location.protocol === 'https:'
      ? '; secure'
      : '';
  const maxAge = days * 24 * 60 * 60;
  
  if (rootDomain) {
    document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAge}; samesite=lax${domainPart}${securePart}`;
  }
  // Also set at host level for direct access and fallback
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAge}; samesite=lax${securePart}`;
}

export function deleteCookie(name: string) {
  if (typeof document === 'undefined') return;
  const rootDomain = getRootDomain();
  const host = typeof window !== 'undefined' ? window.location.hostname : '';
  const domains = [rootDomain, host, ''];

  domains.forEach((dom) => {
    const domainPart = dom ? `; domain=${dom}` : '';
    document.cookie = `${name}=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT; samesite=lax${domainPart}`;
    document.cookie = `${name}=; path=; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT; samesite=lax${domainPart}`;
  });
  document.cookie = `${name}=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT; samesite=lax`;
  document.cookie = `${name}=; path=; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT; samesite=lax`;
}

/**
 * Resolves the primary login URL across subdomains with a return redirect parameter.
 */
export function getMainLoginUrl(returnUrl?: string): string {
  if (typeof window === 'undefined') return '/login';
  const host = window.location.hostname.toLowerCase();
  const target = returnUrl || window.location.href;
  const redirectParam = target ? `?redirect=${encodeURIComponent(target)}` : '';

  if (
    host === 'localhost' ||
    host === '127.0.0.1' ||
    /^(?:\d{1,3}\.){3}\d{1,3}$/.test(host)
  ) {
    return `/login${redirectParam}`;
  }

  if (host.includes('demo.')) {
    return `${window.location.protocol}//demo.swipies.app/login${redirectParam}`;
  }

  if (host.endsWith('swipies.app')) {
    // If on ads or other subdomains, send to main platform portal app.swipies.app
    return `${window.location.protocol}//app.swipies.app/login${redirectParam}`;
  }

  return `${window.location.origin}/login${redirectParam}`;
}

export function redirectToLogin(returnUrl?: string) {
  if (typeof window === 'undefined') return;
  window.location.href = getMainLoginUrl(returnUrl);
}

const storage = {
  getAuthorization: (): string => {
    return getAuthorization();
  },
  getToken: () => {
    return localStorage.getItem(Token);
  },
  getUserInfo: () => {
    return localStorage.getItem(UserInfo);
  },
  getUserInfoObject: () => {
    const userInfoStr = localStorage.getItem(UserInfo);
    return userInfoStr ? JSON.parse(userInfoStr) : null;
  },
  setAuthorization: (value: string) => {
    if (!value) return;
    const formatted = value.startsWith('Bearer ') ? value : `Bearer ${value}`;
    localStorage.setItem(Authorization, formatted);
    setCookie(AUTH_COOKIE_NAME, formatted);
    setCookie(LOGGED_IN_COOKIE_NAME, '1');
  },
  setToken: (value: string) => {
    localStorage.setItem(Token, value);
    if (value) {
      const formatted = value.startsWith('Bearer ') ? value : `Bearer ${value}`;
      setCookie(AUTH_COOKIE_NAME, formatted);
      setCookie(LOGGED_IN_COOKIE_NAME, '1');
    }
  },
  setUserInfo: (value: string | Record<string, unknown>) => {
    const valueStr = typeof value !== 'string' ? JSON.stringify(value) : value;
    localStorage.setItem(UserInfo, valueStr);
  },
  setItems: (pairs: Record<string, string>) => {
    Object.entries(pairs).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        localStorage.setItem(key, value);
      }
    });
    const authVal = pairs[Authorization] || (pairs[Token] ? `Bearer ${pairs[Token]}` : '');
    if (authVal) {
      const formatted = authVal.startsWith('Bearer ') ? authVal : `Bearer ${authVal}`;
      setCookie(AUTH_COOKIE_NAME, formatted);
      setCookie(LOGGED_IN_COOKIE_NAME, '1');
    }
  },
  removeAuthorization: () => {
    localStorage.removeItem(Authorization);
    deleteCookie(AUTH_COOKIE_NAME);
    deleteCookie(LOGGED_IN_COOKIE_NAME);
    deleteCookie('swipies_token');
    deleteCookie('ragflow_auth');
  },
  removeAll: () => {
    KeySet.forEach((x) => {
      localStorage.removeItem(x);
    });
    deleteCookie(AUTH_COOKIE_NAME);
    deleteCookie(LOGGED_IN_COOKIE_NAME);
    deleteCookie('swipies_token');
    deleteCookie('ragflow_auth');
    deleteCookie(Authorization);
    deleteCookie(Token);
  },
  setLanguage: (lng: string) => {
    localStorage.setItem('lng', lng);
  },
  getLanguage: (): string => {
    return localStorage.getItem('lng') as string;
  },
};

/**
 * Cross-subdomain aware authorization getter.
 * Synchronizes token between shared cookie and origin-scoped localStorage.
 * If the shared cookie was deleted on another subdomain (e.g. user logged out on app.swipies.app),
 * it wipes localStorage and returns an empty string immediately.
 */
export const getAuthorization = (): string => {
  if (typeof window === 'undefined') return '';

  const authParam = getSearchValue('auth');
  if (authParam) {
    const formatted = authParam.startsWith('Bearer ') ? authParam : `Bearer ${authParam}`;
    localStorage.setItem(Authorization, formatted);
    setCookie(AUTH_COOKIE_NAME, formatted);
    setCookie(LOGGED_IN_COOKIE_NAME, '1');
    return formatted;
  }

  const rootDomain = getRootDomain();
  const cookieAuth = getCookie(AUTH_COOKIE_NAME);
  const loggedInCookie = getCookie(LOGGED_IN_COOKIE_NAME);
  const localAuth = localStorage.getItem(Authorization);

  // If in multi-subdomain environment (e.g. .swipies.app)
  if (rootDomain) {
    // If cookie is missing or explicitly logged out:
    if (!cookieAuth && !loggedInCookie) {
      if (localAuth) {
        // Session was terminated on another subdomain! Clear stale storage.
        KeySet.forEach((x) => localStorage.removeItem(x));
      }
      return '';
    }

    // Cookie is present: synchronize with localStorage
    if (cookieAuth) {
      if (localAuth !== cookieAuth) {
        localStorage.setItem(Authorization, cookieAuth);
      }
      return cookieAuth;
    }
  }

  // Fallback for localhost or environments without root domain cookie
  if (localAuth) {
    return localAuth;
  }

  if (cookieAuth) {
    localStorage.setItem(Authorization, cookieAuth);
    return cookieAuth;
  }

  return '';
};

/**
 * Subscribes to cross-domain auth state changes (storage events, visibility change, window focus, cookie polling)
 */
export function subscribeToAuthChanges(callback: (isAuthenticated: boolean) => void): () => void {
  if (typeof window === 'undefined') return () => {};

  let lastState = Boolean(getAuthorization());

  const check = () => {
    const current = Boolean(getAuthorization());
    if (current !== lastState) {
      lastState = current;
      callback(current);
    }
  };

  const handleStorage = (e: StorageEvent) => {
    if (!e.key || e.key === Authorization || e.key === Token) {
      check();
    }
  };

  const handleVisibility = () => {
    if (document.visibilityState === 'visible') {
      check();
    }
  };

  window.addEventListener('storage', handleStorage);
  window.addEventListener('focus', check);
  document.addEventListener('visibilitychange', handleVisibility);

  // Polling interval (1.5s) to catch cookie deletion across subdomains without delay
  const intervalId = window.setInterval(check, 1500);

  return () => {
    window.removeEventListener('storage', handleStorage);
    window.removeEventListener('focus', check);
    document.removeEventListener('visibilitychange', handleVisibility);
    window.clearInterval(intervalId);
  };
}

export default storage;

