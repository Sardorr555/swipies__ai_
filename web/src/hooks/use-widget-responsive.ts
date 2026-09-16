import { useEffect, useState } from 'react';

export interface WidgetResponsiveState {
  isMobile: boolean;
  viewportWidth: number;
  visualViewportHeight?: number;
  visualViewportOffsetTop?: number;
}

export const DEFAULT_MOBILE_BREAKPOINT = 640;

/**
 * Safely calculates whether the widget is running on a mobile device or small viewport.
 *
 * CRITICAL ARCHITECTURAL GUARANTEE:
 * Inside an embedded iframe (window.self !== window.top), the child iframe's own
 * window.innerWidth (100px or 380px) and window.matchMedia MUST NOT be used for
 * cross-origin mobile detection, as they would cause false-positive mobile detection
 * on ALL desktop users!
 *
 * Evaluation hierarchy:
 * 1. If in iframe:
 *    a) Same-origin: inspect window.parent.innerWidth.
 *    b) Cross-origin (SecurityError): fallback to window.screen.width (physical device resolution).
 * 2. If top-level standalone window (not in iframe):
 *    Use window.innerWidth, matchMedia, and screen.width.
 */
export const checkIsMobileViewport = (
  breakpoint: number = DEFAULT_MOBILE_BREAKPOINT,
): boolean => {
  if (typeof window === 'undefined') return false;

  let isInIframe = false;
  try {
    isInIframe = window.self !== window.top;
  } catch {
    // If accessing window.top throws a SecurityError, we are definitely in a cross-origin iframe
    isInIframe = true;
  }

  if (isInIframe) {
    // 1. Try checking parent window if accessible (same-origin iframe)
    try {
      if (
        window.parent &&
        window.parent !== window &&
        typeof window.parent.innerWidth === 'number' &&
        window.parent.innerWidth > 0
      ) {
        return window.parent.innerWidth <= breakpoint;
      }
    } catch {
      // Cross-origin access blocked by browser security (standard production scenario)
    }

    // 2. Cross-origin iframe:
    // We intentionally bypass window.innerWidth and matchMedia inside the iframe.
    // window.screen dimensions provide the true physical device screen width/height across origins.
    if (typeof window.screen !== 'undefined') {
      const screenWidth = window.screen.width;
      const screenHeight = window.screen.height;
      if (typeof screenWidth === 'number' && screenWidth > 0) {
        // Mobile portrait (width <= 640px) OR mobile landscape:
        // - 480px height ceiling: Maximum logical short dimension of smartphones (iPhone SE: 375px,
        //   iPhone 16 Pro Max: 430px, S24 Ultra: 412px, Pixel 9: 412px). Tablets (iPad mini: 768px,
        //   iPad 10: 810px) exceed 480px and are treated as desktop/tablet.
        // - 960px width ceiling: Maximum logical long dimension of modern smartphones in landscape
        //   (iPhone 16 Pro Max: 932px, S24 Ultra: 915px, Xperia 1: 960px). Excludes desktop monitors.
        const isMobileDevice =
          screenWidth <= breakpoint ||
          (typeof screenHeight === 'number' &&
            screenHeight > 0 &&
            screenHeight <= 480 &&
            screenWidth <= 960);
        if (isMobileDevice) {
          return true;
        }
      }
    }

    return false;
  }

  // Not in iframe (top-level standalone window, debug, or preview tab):
  if (typeof window.innerWidth === 'number' && window.innerWidth > 0) {
    if (window.innerWidth <= breakpoint) {
      return true;
    }
  }

  if (typeof window.matchMedia === 'function') {
    try {
      if (window.matchMedia(`(max-width: ${breakpoint}px)`).matches) {
        return true;
      }
    } catch {
      // matchMedia unsupported or errored
    }
  }

  if (typeof window.screen !== 'undefined' && typeof window.screen.width === 'number') {
    if (window.screen.width > 0 && window.screen.width <= breakpoint) {
      return true;
    }
  }

  return false;
};

const getEffectiveViewportWidth = (isInIframe: boolean): number => {
  if (typeof window === 'undefined') return 1024;

  if (isInIframe) {
    try {
      if (
        window.parent &&
        window.parent !== window &&
        typeof window.parent.innerWidth === 'number' &&
        window.parent.innerWidth > 0
      ) {
        return window.parent.innerWidth;
      }
    } catch {
      // Cross-origin access blocked by security policy
    }
    return window.screen?.width || 1024;
  }

  return window.innerWidth || window.screen?.width || 1024;
};

export const getVisualViewportMetrics = (): {
  visualViewportHeight?: number;
  visualViewportOffsetTop?: number;
} => {
  if (typeof window === 'undefined' || !window.visualViewport) {
    return {
      visualViewportHeight: undefined,
      visualViewportOffsetTop: undefined,
    };
  }
  return {
    visualViewportHeight: Math.round(window.visualViewport.height),
    visualViewportOffsetTop: Math.round(window.visualViewport.offsetTop),
  };
};

/**
 * Hook to reactively monitor mobile viewport changes (orientation, window resize, visualViewport).
 */
export const useWidgetResponsive = (
  breakpoint: number = DEFAULT_MOBILE_BREAKPOINT,
): WidgetResponsiveState => {
  const [state, setState] = useState<WidgetResponsiveState>(() => {
    let isInIframe = false;
    try {
      isInIframe = typeof window !== 'undefined' && window.self !== window.top;
    } catch {
      isInIframe = true;
    }

    const vv = getVisualViewportMetrics();

    return {
      isMobile: checkIsMobileViewport(breakpoint),
      viewportWidth: getEffectiveViewportWidth(isInIframe),
      visualViewportHeight: vv.visualViewportHeight,
      visualViewportOffsetTop: vv.visualViewportOffsetTop,
    };
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    let isInIframe = false;
    try {
      isInIframe = window.self !== window.top;
    } catch {
      isInIframe = true;
    }

    const handleResize = () => {
      const mobile = checkIsMobileViewport(breakpoint);
      const width = getEffectiveViewportWidth(isInIframe);
      const vv = getVisualViewportMetrics();

      setState(prev => {
        if (
          prev.isMobile === mobile &&
          prev.viewportWidth === width &&
          prev.visualViewportHeight === vv.visualViewportHeight &&
          prev.visualViewportOffsetTop === vv.visualViewportOffsetTop
        ) {
          return prev;
        }
        return {
          isMobile: mobile,
          viewportWidth: width,
          visualViewportHeight: vv.visualViewportHeight,
          visualViewportOffsetTop: vv.visualViewportOffsetTop,
        };
      });
    };

    window.addEventListener('resize', handleResize);
    window.addEventListener('orientationchange', handleResize);

    // Explicitly attach to window.visualViewport to handle iOS Safari virtual keyboard
    let cleanupVV: (() => void) | undefined;
    if (typeof window.visualViewport !== 'undefined' && window.visualViewport !== null) {
      const vv = window.visualViewport;
      const handleVVChange = () => {
        handleResize();
      };
      vv.addEventListener('resize', handleVVChange);
      vv.addEventListener('scroll', handleVVChange);

      cleanupVV = () => {
        vv.removeEventListener('resize', handleVVChange);
        vv.removeEventListener('scroll', handleVVChange);
      };
    }

    let mql: MediaQueryList | null = null;
    if (typeof window.matchMedia === 'function') {
      try {
        mql = window.matchMedia(`(max-width: ${breakpoint}px)`);
        if (mql.addEventListener) {
          mql.addEventListener('change', handleResize);
        } else if ((mql as any).addListener) {
          (mql as any).addListener(handleResize);
        }
      } catch {
        // matchMedia unsupported or errored
      }
    }

    // Trigger immediate update
    handleResize();

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('orientationchange', handleResize);
      if (cleanupVV) {
        cleanupVV();
      }
      if (mql) {
        if (mql.removeEventListener) {
          mql.removeEventListener('change', handleResize);
        } else if ((mql as any).removeListener) {
          (mql as any).removeListener(handleResize);
        }
      }
    };
  }, [breakpoint]);

  return state;
};
