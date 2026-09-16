const VISITOR_ID_STORAGE_KEY = 'swipies_visitor_id';

const UUIDV4_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

let inMemoryVisitorId: string | null = null;

export const isValidUuidV4 = (id: string | null | undefined): boolean => {
  if (!id || typeof id !== 'string') return false;
  return UUIDV4_REGEX.test(id.trim());
};

const generateCsprngUuidV4 = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    // Per RFC 4122 sec. 4.4, set version 4 and variant bits
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }
  // Safe fallback (never sequential)
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

/**
 * Retrieves the stable visitor ID from localStorage, or generates a new CSPRNG UUIDv4.
 * Gracefully degrades to in-memory storage if localStorage is blocked (Safari ITP / Private Browsing).
 */
export const getOrCreateVisitorId = (): string => {
  // 1. Try to read from localStorage first
  try {
    const stored = window.localStorage.getItem(VISITOR_ID_STORAGE_KEY);
    if (stored && isValidUuidV4(stored)) {
      inMemoryVisitorId = stored.trim();
      return inMemoryVisitorId;
    }
  } catch {
    // localStorage access blocked (e.g. cross-origin iframe or private mode)
  }

  // 2. If inMemory fallback was set during a degraded session, keep using it
  if (inMemoryVisitorId && isValidUuidV4(inMemoryVisitorId)) {
    return inMemoryVisitorId;
  }

  // 3. Generate new CSPRNG UUIDv4
  const newId = generateCsprngUuidV4();
  inMemoryVisitorId = newId;

  // 4. Attempt to persist to localStorage
  try {
    window.localStorage.setItem(VISITOR_ID_STORAGE_KEY, newId);
  } catch {
    // Storage blocked; inMemoryVisitorId will serve for this session
  }

  return newId;
};

/**
 * Checks whether localStorage is accessible and writable.
 * Returns false when blocked by Safari ITP, third-party iframe restrictions,
 * or private/incognito browsing mode.
 */
export const isStorageAvailable = (): boolean => {
  try {
    const testKey = '__swipies_storage_test__';
    window.localStorage.setItem(testKey, testKey);
    window.localStorage.removeItem(testKey);
    return true;
  } catch {
    return false;
  }
};

export const _resetVisitorIdForTesting = (): void => {
  inMemoryVisitorId = null;
};

