import authorizationUtil, {
  AUTH_COOKIE_NAME,
  LOGGED_IN_COOKIE_NAME,
  getRootDomain,
  getCookie,
  setCookie,
  deleteCookie,
  getMainLoginUrl,
  getAuthorization,
} from '../../utils/authorization-util';
import { Authorization } from '../../constants/authorization';

describe('Cross-Subdomain Authorization & Session Sync Test Suite', () => {
  const originalLocation = window.location;

  beforeEach(() => {
    // Clear cookies and localStorage before each test
    document.cookie.split(';').forEach((c) => {
      const eqPos = c.indexOf('=');
      const name = eqPos > -1 ? c.substr(0, eqPos).trim() : c.trim();
      document.cookie = `${name}=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
    });
    localStorage.clear();
  });

  afterAll(() => {
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
    });
  });

  const mockHostname = (hostname: string, protocol = 'http:') => {
    Object.defineProperty(window, 'location', {
      value: {
        ...originalLocation,
        hostname,
        protocol,
        origin: `${protocol}//${hostname}`,
        href: `${protocol}//${hostname}/`,
        pathname: '/',
        search: '',
      },
      writable: true,
    });
  };

  describe('Root Domain Resolution (getRootDomain)', () => {
    it('resolves .swipies.app for app.swipies.app', () => {
      mockHostname('app.swipies.app');
      expect(getRootDomain()).toBe('.swipies.app');
    });

    it('resolves .swipies.app for ads.swipies.app', () => {
      mockHostname('ads.swipies.app');
      expect(getRootDomain()).toBe('.swipies.app');
    });

    it('resolves .swipies.app for demo.swipies.app', () => {
      mockHostname('demo.swipies.app');
      expect(getRootDomain()).toBe('.swipies.app');
    });

    it('returns empty string for localhost and 127.0.0.1 (host-only cookie)', () => {
      mockHostname('localhost');
      expect(getRootDomain()).toBe('');

      mockHostname('127.0.0.1');
      expect(getRootDomain()).toBe('');
    });
  });

  describe('Canonical Login Portal Resolution (getMainLoginUrl)', () => {
    it('redirects ads.swipies.app to app.swipies.app/login with return redirect param', () => {
      mockHostname('ads.swipies.app', 'https:');
      const loginUrl = getMainLoginUrl('https://ads.swipies.app/dashboard');
      expect(loginUrl).toContain('https://app.swipies.app/login?redirect=');
      expect(loginUrl).toContain(encodeURIComponent('https://ads.swipies.app/dashboard'));
    });

    it('redirects demo.swipies.app to demo.swipies.app/login', () => {
      mockHostname('demo.swipies.app', 'https:');
      const loginUrl = getMainLoginUrl('https://demo.swipies.app/chat');
      expect(loginUrl).toContain('https://demo.swipies.app/login?redirect=');
    });

    it('uses relative /login on localhost', () => {
      mockHostname('localhost', 'http:');
      const loginUrl = getMainLoginUrl();
      expect(loginUrl).toMatch(/^\/login/);
    });
  });

  describe('Cookie Management & Session Storage', () => {
    it('sets and gets cookie correctly', () => {
      mockHostname('localhost');
      setCookie('test_cookie', 'test_value');
      expect(getCookie('test_cookie')).toBe('test_value');
    });

    it('deleteCookie purges the cookie', () => {
      mockHostname('localhost');
      setCookie('test_cookie', 'test_value');
      expect(getCookie('test_cookie')).toBe('test_value');

      deleteCookie('test_cookie');
      expect(getCookie('test_cookie')).toBeNull();
    });

    it('setAuthorization writes to both localStorage and shared cookies', () => {
      mockHostname('ads.swipies.app');
      authorizationUtil.setAuthorization('token_xyz_123');

      expect(localStorage.getItem(Authorization)).toBe('Bearer token_xyz_123');
      expect(getCookie(AUTH_COOKIE_NAME)).toBe('Bearer token_xyz_123');
      expect(getCookie(LOGGED_IN_COOKIE_NAME)).toBe('1');
    });

    it('removeAll removes localStorage and all shared authentication cookies', () => {
      mockHostname('app.swipies.app');
      authorizationUtil.setAuthorization('token_xyz_123');
      expect(authorizationUtil.getAuthorization()).toBe('Bearer token_xyz_123');

      authorizationUtil.removeAll();

      expect(localStorage.getItem(Authorization)).toBeNull();
      expect(getCookie(AUTH_COOKIE_NAME)).toBeNull();
      expect(getCookie(LOGGED_IN_COOKIE_NAME)).toBeNull();
    });

    it('cross-subdomain logout detection: if cookie was cleared on another subdomain, getAuthorization wipes local storage and returns empty string', () => {
      mockHostname('ads.swipies.app');

      // Simulate ads having a leftover token in localStorage
      localStorage.setItem(Authorization, 'Bearer leftover_stale_token');

      // But the shared cookie is absent (user logged out on app.swipies.app)
      deleteCookie(AUTH_COOKIE_NAME);
      deleteCookie(LOGGED_IN_COOKIE_NAME);

      // Calling getAuthorization() should detect the missing cookie, wipe localStorage, and return empty
      const result = getAuthorization();
      expect(result).toBe('');
      expect(localStorage.getItem(Authorization)).toBeNull();
    });

    it('cross-subdomain login detection: if cookie exists, getAuthorization syncs into localStorage', () => {
      mockHostname('ads.swipies.app');

      // Simulate user logging in on app.swipies.app which set the cookie
      setCookie(AUTH_COOKIE_NAME, 'Bearer user_valid_token');
      setCookie(LOGGED_IN_COOKIE_NAME, '1');

      // ads.swipies.app currently has empty localStorage
      expect(localStorage.getItem(Authorization)).toBeNull();

      // Calling getAuthorization() should discover the cookie and sync to localStorage
      const result = getAuthorization();
      expect(result).toBe('Bearer user_valid_token');
      expect(localStorage.getItem(Authorization)).toBe('Bearer user_valid_token');
    });
  });
});
