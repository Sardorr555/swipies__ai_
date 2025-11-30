import { Authorization, Token, UserInfo } from '@/constants/authorization';
import { getSearchValue } from './common-util';
const KeySet = [Authorization, Token, UserInfo];

const storage = {
  getAuthorization: () => {
    return localStorage.getItem(Authorization);
  },
  getToken: () => {
    return localStorage.getItem(Token);
  },
  getUserInfo: () => {
    return localStorage.getItem(UserInfo);
  },
  getUserInfoObject: () => {
    return JSON.parse(localStorage.getItem('userInfo') || '');
  },
  setAuthorization: (value: string) => {
    localStorage.setItem(Authorization, value);
    // Dispatch custom event to notify auth hook of changes
    window.dispatchEvent(new Event('auth-storage-change'));
  },
  setToken: (value: string) => {
    localStorage.setItem(Token, value);
  },
  setUserInfo: (value: string | Record<string, unknown>) => {
    let valueStr = typeof value !== 'string' ? JSON.stringify(value) : value;
    localStorage.setItem(UserInfo, valueStr);
  },
  setItems: (pairs: Record<string, string>) => {
    Object.entries(pairs).forEach(([key, value]) => {
      localStorage.setItem(key, value);
    });
  },
  removeAuthorization: () => {
    localStorage.removeItem(Authorization);
    // Dispatch custom event to notify auth hook of changes
    window.dispatchEvent(new Event('auth-storage-change'));
  },
  removeAll: () => {
    KeySet.forEach((x) => {
      localStorage.removeItem(x);
    });
    // Dispatch custom event to notify auth hook of changes
    window.dispatchEvent(new Event('auth-storage-change'));
  },
  setLanguage: (lng: string) => {
    localStorage.setItem('lng', lng);
  },
  getLanguage: (): string => {
    return localStorage.getItem('lng') as string;
  },
};

export const getAuthorization = () => {
  // First check URL query params (for OAuth callback)
  // Backend sends JWT token without "Bearer " prefix in URL
  const auth = getSearchValue('auth');
  if (auth && auth.trim().length > 0) {
    // Remove "Bearer " prefix if present (shouldn't be, but just in case)
    const token = auth.startsWith('Bearer ') ? auth.replace('Bearer ', '') : auth;
    // Add "Bearer " prefix for API requests
    return 'Bearer ' + token;
  }
  
  // Then check localStorage
  // Token is stored WITHOUT "Bearer " prefix (same as regular login)
  const storedAuth = storage.getAuthorization();
  if (!storedAuth || storedAuth.trim().length === 0) {
    return '';
  }
  
  // Remove "Bearer " prefix if present (shouldn't be in storage, but handle it)
  const token = storedAuth.startsWith('Bearer ') ? storedAuth.replace('Bearer ', '') : storedAuth;
  
  // Add "Bearer " prefix for API requests (backend expects it in Authorization header)
  return 'Bearer ' + token;
};

export default storage;

// Will not jump to the login page
export function redirectToLogin() {
  window.location.href = location.origin + `/login`;
}
