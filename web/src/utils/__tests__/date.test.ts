import dayjs from 'dayjs';
import { formatRelativeTime } from '../date';

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
