import { AlertTriangle, X } from 'lucide-react';
import React from 'react';
import { useTranslation } from 'react-i18next';

export interface StorageWarningBannerProps {
  visible: boolean;
  onClose: () => void;
}

export const StorageWarningBanner: React.FC<StorageWarningBannerProps> = ({
  visible,
  onClose,
}) => {
  const { t } = useTranslation();
  if (!visible) return null;

  return (
    <div
      role="alert"
      data-testid="storage-warning-banner"
      className="bg-amber-500/15 border-b border-amber-500/20 px-3 py-1.5 flex items-center justify-between text-amber-900 text-[11px] leading-tight z-10 flex-shrink-0"
    >
      <div className="flex items-center space-x-1.5 min-w-0 pr-1">
        <AlertTriangle size={13} className="text-amber-600 flex-shrink-0" />
        <span className="truncate">
          {t('chat.incognitoWarning') ||
            'История диалогов не сохраняется в режиме инкогнито / Safari ITP'}
        </span>
      </div>
      <button
        type="button"
        onClick={onClose}
        aria-label="close"
        className="text-amber-700 hover:text-amber-900 p-0.5 rounded transition-colors flex-shrink-0"
        title={t('common.close') || 'Close'}
      >
        <X size={12} />
      </button>
    </div>
  );
};

export default StorageWarningBanner;
