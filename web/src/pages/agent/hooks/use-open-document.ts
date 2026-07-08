import { useCallback } from 'react';

export function useOpenDocument() {
  const openDocument = useCallback(() => {
    window.open(
      'https://docs.swipies.app/docs/dev/category/agent-components',
      '_blank',
    );
  }, []);

  return openDocument;
}
