import {
  _resetVisitorIdForTesting,
  getOrCreateVisitorId,
  isStorageAvailable,
  isValidUuidV4,
} from '../visitor-identity';

describe('visitor-identity', () => {
  beforeEach(() => {
    window.localStorage.clear();
    _resetVisitorIdForTesting();
  });

  test('generates valid UUIDv4 complying with CSPRNG format', () => {
    const id = getOrCreateVisitorId();
    expect(isValidUuidV4(id)).toBe(true);
    // UUIDv4 format check: 8-4-4-4-12 hex with 4 in 3rd segment and 8,9,a,b in 4th
    expect(id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
  });

  test('persists and retrieves from localStorage', () => {
    const id1 = getOrCreateVisitorId();
    const id2 = getOrCreateVisitorId();
    expect(id1).toBe(id2);
    expect(window.localStorage.getItem('swipies_visitor_id')).toBe(id1);
  });

  test('degrades gracefully if localStorage throws (Safari ITP / private browsing)', () => {
    const originalGetItem = window.localStorage.getItem;
    const originalSetItem = window.localStorage.setItem;
    window.localStorage.getItem = () => {
      throw new Error('SecurityError: The operation is insecure.');
    };
    window.localStorage.setItem = () => {
      throw new Error('SecurityError: The operation is insecure.');
    };

    const id = getOrCreateVisitorId();
    expect(isValidUuidV4(id)).toBe(true);

    const id2 = getOrCreateVisitorId();
    expect(id2).toBe(id);

    window.localStorage.getItem = originalGetItem;
    window.localStorage.setItem = originalSetItem;
  });

  test('isStorageAvailable accurately detects localStorage accessibility', () => {
    // Normal environment
    expect(isStorageAvailable()).toBe(true);

    // Blocked environment (Safari ITP / Incognito)
    const setItemSpy = jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError / SecurityError: Storage blocked');
    });

    expect(isStorageAvailable()).toBe(false);

    setItemSpy.mockRestore();
    expect(isStorageAvailable()).toBe(true);
  });
});
