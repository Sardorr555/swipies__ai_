import { FileIconMap } from '@/constants/file';
import { cn } from '@/lib/utils';
import { getExtension } from '@/utils/document-util';
import SvgIcon from './svg-icon';
import { IconFont, IconFontType } from './icon-font-base';

export { IconFont, IconFontFill } from './icon-font-base';

export function FileIcon({
  name,
  className,
  type,
}: IconFontType & { type?: string }) {
  const isFolder = type === 'folder';
  const isSkills = type === 'skills';
  if (isSkills) {
    return (
      <span className={cn('size-4', className)}>
        <SvgIcon name="home-icon/skills" width={16} height={16} />
      </span>
    );
  }
  return (
    <span className={cn('size-4', className)}>
      <IconFont
        name={isFolder ? 'file-sub' : FileIconMap[getExtension(name)]}
      ></IconFont>
    </span>
  );
}
