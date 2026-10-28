import authorizationUtil, {
  AUTH_COOKIE_NAME, LOGGED_IN_COOKIE_NAME, getAuthorization,
  getCookie, setCookie, isSharedChatView, redirectToLogin,
} from '../../utils/authorization-util';
import { Authorization } from '../../constants/authorization';

describe('Public chat credential isolation', () => {
  const originalLocation = window.location;
  beforeEach(() => {
    Object.defineProperty(window, 'location', {value: originalLocation, writable: true});
    localStorage.clear();
    document.cookie.split(';').forEach(c => {
      document.cookie = `${c.split('=')[0].trim()}=;path=/;max-age=0`;
    });
    setCookie(AUTH_COOKIE_NAME, 'Bearer owner-session');
    setCookie(LOGGED_IN_COOKIE_NAME, '1');
    localStorage.setItem(Authorization, 'Bearer owner-session');
  });
  afterAll(() => Object.defineProperty(window, 'location', {value: originalLocation, writable: true}));
  function view(path: string, search='?shared_id=public-chat&auth=embed-only') {
    Object.defineProperty(window, 'location', {
      value: {...originalLocation, pathname:path, search, href:`http://localhost${path}${search}`}, writable:true,
    });
  }
  function expectOwnerUntouched() {
    expect(getCookie(AUTH_COOKIE_NAME)).toBe('Bearer owner-session');
    expect(getCookie(LOGGED_IN_COOKIE_NAME)).toBe('1');
    expect(localStorage.getItem(Authorization)).toBe('Bearer owner-session');
  }
  it.each(['/chats/widget','/chats/share','/agent/share','/chats/widget/'])('%s uses embed auth without persisting it', path => {
    view(path);
    expect(getAuthorization()).toBe('Bearer embed-only');
    expectOwnerUntouched();
  });
  it('never borrows owner credentials if a widget URL has no auth', () => {
    view('/chats/widget','?shared_id=public-chat');
    expect(getAuthorization()).toBe('');
    expectOwnerUntouched();
  });
  it('leaves an anonymous visitor anonymous', () => {
    authorizationUtil.removeAll();
    view('/chats/widget');
    expect(getAuthorization()).toBe('Bearer embed-only');
    expect(getCookie(AUTH_COOKIE_NAME)).toBeNull();
    expect(getCookie(LOGGED_IN_COOKIE_NAME)).toBeNull();
    expect(localStorage.getItem(Authorization)).toBeNull();
  });
  it('preserves owner login when an expired widget triggers auth cleanup', () => {
    view('/chats/widget');
    authorizationUtil.removeAll();
    authorizationUtil.removeAuthorization();
    authorizationUtil.setAuthorization('embed-only');
    redirectToLogin();
    expect(window.location.pathname).toBe('/chats/widget');
    expectOwnerUntouched();
  });
  it('accepts an already formatted embed bearer token', () => {
    view('/chats/widget','?auth=Bearer%20embed-only');
    expect(getAuthorization()).toBe('Bearer embed-only');
    expectOwnerUntouched();
  });
  it('retains ordinary account sign-in and logout on platform pages', () => {
    view('/chats','');
    expect(isSharedChatView()).toBe(false);
    expect(getAuthorization()).toBe('Bearer owner-session');
    authorizationUtil.removeAll();
    expect(getAuthorization()).toBe('');
  });
});
