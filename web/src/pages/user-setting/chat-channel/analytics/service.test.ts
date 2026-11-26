import { number, dateTime, periodQuery, publicSnapshot } from './service';

jest.mock('@/utils/authorization-util', () => ({ getAuthorization: () => 'owner-session' }));

describe('Telegram analytics viewer boundaries', () => {
  afterEach(() => jest.restoreAllMocks());

  it('distinguishes zero from missing observations', () => {
    expect(number(0)).toBe('0');
    expect(number(null)).toBe('Нет данных');
    expect(number(undefined)).toBe('Нет данных');
  });

  it('formats a UTC instant in the selected timezone', () => {
    expect(dateTime('2026-06-01T20:30:00Z', 'Asia/Tashkent')).toMatch(/02\.06\.(?:2026|26), 01:30/);
    expect(dateTime(null, 'UTC')).toBe('Нет данных');
  });

  it('preserves custom bounds and timezone in the request', () => {
    const query = new URLSearchParams(periodQuery({ period: 'custom', timezone: 'Asia/Tashkent', start: '2026-06-01', end: '2026-06-02' }));
    expect(query.get('timezone')).toBe('Asia/Tashkent');
    expect(query.get('start')).toBe('2026-06-01');
    expect(query.get('end')).toBe('2026-06-02');
  });

  it('sends the capability in a body without the owner session', async () => {
    const fetcher = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ code: 0, data: { title: 'Public' } }) });
    global.fetch = fetcher;
    await expect(publicSnapshot('synthetic-capability')).resolves.toEqual({ title: 'Public' });
    const [url, options] = fetcher.mock.calls[0];
    expect(url).toBe('/api/v1/telegram-analytics/public');
    expect(options.credentials).toBe('omit');
    expect(options.cache).toBe('no-store');
    expect(options.referrerPolicy).toBe('no-referrer');
    expect(options.headers.Authorization).toBeUndefined();
    expect(JSON.parse(options.body)).toEqual({ token: 'synthetic-capability' });
  });

  it('propagates revocation instead of returning stale data', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, json: async () => ({ code: 410, message: 'revoked' }) });
    await expect(publicSnapshot('synthetic-capability')).rejects.toThrow('Владелец отозвал эту ссылку');
  });
});
