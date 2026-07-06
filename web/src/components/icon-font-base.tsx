import { cn } from '@/lib/utils';
import { CSSProperties } from 'react';

export type IconFontType = {
  name: string;
  className?: string;
  style?: CSSProperties;
};

export const IconFont = ({ name, className, style }: IconFontType) => (
  <svg className={cn('size-4', className)} style={style}>
    <use xlinkHref={`#icon-${name}`} />
  </svg>
);

export function IconFontFill({
  name,
  className,
  isFill = true,
}: IconFontType & { isFill?: boolean }) {
  return (
    <svg
      className={cn('size-4', className)}
      style={{ fill: isFill ? 'currentColor' : '' }}
    >
      <use xlinkHref={`#icon-${name}`} />
    </svg>
  );
}
