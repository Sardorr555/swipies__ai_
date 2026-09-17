import dayjs from 'dayjs';
import { formatRelativeTime, formatSecondsToHumanReadable } from '../date';

describe('formatRelativeTime', () => {
  it('returns empty string for null or undefined', () => {
    expect(formatRelativeTime(null)).toBe('');
    expect(formatRelativeTime(undefined)).toBe('');
    expect(formatRelativeTime('invalid-date-string')).toBe('');
  });

  it('returns "Just now" for dates less than 60 seconds ago', () => {
    const date = dayjs().subtract(30, 'second').toISOString();
    expect(formatRelativeTime(date)).toBe('Just now');
  });

  it('returns "Xm ago" for dates less than an hour ago', () => {
    const date = dayjs().subtract(15, 'minute').toISOString();
    expect(formatRelativeTime(date)).toBe('15m ago');
  });

  it('returns "Xh ago" for dates less than 24 hours ago', () => {
    const date = dayjs().subtract(3, 'hour').toISOString();
    expect(formatRelativeTime(date)).toBe('3h ago');
  });

  it('returns "Yesterday" for dates 1 day ago', () => {
    const date = dayjs().subtract(1, 'day').toISOString();
    expect(formatRelativeTime(date)).toBe('Yesterday');
  });

  it('returns "Xd ago" for dates between 2 and 6 days ago', () => {
    const date = dayjs().subtract(4, 'day').toISOString();
    expect(formatRelativeTime(date)).toBe('4d ago');
  });

  it('returns formatted date for dates older than a week', () => {
    const date = dayjs().subtract(14, 'day');
    expect(formatRelativeTime(date.toISOString())).toBe(date.format('MMM D'));
  });
});

describe('formatSecondsToHumanReadable', () => {
  test('formats sub-minute durations in seconds', () => {
    expect(formatSecondsToHumanReadable(0)).toBe('0s');
    expect(formatSecondsToHumanReadable(30)).toBe('30s');
  });

  test('strips trailing zeros from fractional seconds', () => {
    expect(formatSecondsToHumanReadable(1.5)).toBe('1.5s');
  });

  test('does not emit a trailing space for whole minutes or hours', () => {
    expect(formatSecondsToHumanReadable(60)).toBe('1m');
    expect(formatSecondsToHumanReadable(3600)).toBe('1h');
    expect(formatSecondsToHumanReadable(7200)).toBe('2h');
  });

  test('does not emit a trailing space when seconds are zero', () => {
    expect(formatSecondsToHumanReadable(3660)).toBe('1h 1m');
    expect(formatSecondsToHumanReadable(5400)).toBe('1h 30m');
  });

  test('joins non-zero hour/minute/second parts with a single space', () => {
    expect(formatSecondsToHumanReadable(90)).toBe('1m 30s');
    expect(formatSecondsToHumanReadable(125)).toBe('2m 5s');
    expect(formatSecondsToHumanReadable(3661)).toBe('1h 1m 1s');
  });

  test('returns "0s" for negative or non-numeric input', () => {
    expect(formatSecondsToHumanReadable(-5)).toBe('0s');
    expect(formatSecondsToHumanReadable(NaN)).toBe('0s');
  });
});
