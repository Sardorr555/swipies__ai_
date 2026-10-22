/*
 *  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

export interface TelemetryRawEvent {
  session_id: string;
  event_type: 'page_view' | 'click' | 'action' | 'heartbeat';
  module: string;
  page_route: string;
  action_category?: string;
  action_name?: string;
  element_tag?: string;
  element_id?: string;
  element_label?: string;
  duration_seconds?: number;
  metadata?: Record<string, any>;
}

// Generate or retrieve persistent session ID
const getSessionId = (): string => {
  try {
    let sid = sessionStorage.getItem('swipies_telemetry_sid');
    if (!sid) {
      sid = 'sess_' + Math.random().toString(36).substring(2, 12) + Date.now().toString(36);
      sessionStorage.setItem('swipies_telemetry_sid', sid);
    }
    return sid;
  } catch {
    return 'sess_fallback_' + Date.now();
  }
};

// Map route path to high-level platform module
export const resolvePlatformModule = (pathname: string): string => {
  const p = pathname.toLowerCase();
  if (p.startsWith('/chat')) return 'chat';
  if (p.startsWith('/dataset') || p.startsWith('/retrieval') || p.startsWith('/chunk')) return 'datasets';
  if (p.startsWith('/agent')) return 'agent_canvas';
  if (p.startsWith('/crm') || p.startsWith('/data-source')) return 'crm';
  if (p.startsWith('/search')) return 'search';
  if (p.startsWith('/files')) return 'files_skills';
  if (p.startsWith('/admin')) return 'admin';
  if (p.startsWith('/ads')) return 'ads';
  if (p.startsWith('/user-setting') || p.startsWith('/profile') || p.startsWith('/subscription') || p.startsWith('/model') || p.startsWith('/team')) return 'settings';
  return 'other';
};

// Icon class map to human-readable action names
const ICON_ACTION_MAP: Record<string, string> = {
  copy: "Nusxalash (Copy)",
  trash: "O'chirish (Delete)",
  send: "Xabar yuborish (Send)",
  plus: "Yangi yaratish (Add)",
  edit: "Tahrirlash (Edit)",
  settings: "Sozlamalar (Settings)",
  download: "Yuklab olish (Download)",
  upload: "Fayl yuklash (Upload)",
  refresh: "Yangilash (Refresh)",
  search: "Qidiruv (Search)",
  play: "Ishga tushirish (Run)",
  check: "Tasdiqlash (Check)",
  close: "Yopish (Close)",
  thumbsup: "Yoqdi (Like)",
  thumbsdown: "Yoqmadi (Dislike)",
  sparkles: "AI Takomillashtirish (Sparkles)",
  filter: "Filtr (Filter)",
  share: "Ulashish (Share)",
  save: "Saqlash (Save)",
};

class PlatformTelemetryTracker {
  private queue: TelemetryRawEvent[] = [];
  private currentPath: string = '';
  private currentModule: string = '';
  private routeStartTime: number = Date.now();
  private isInitialized: boolean = false;
  private flushTimer: any = null;

  public init() {
    if (this.isInitialized || typeof window === 'undefined') return;
    this.isInitialized = true;

    this.currentPath = window.location.pathname;
    this.currentModule = resolvePlatformModule(this.currentPath);
    this.routeStartTime = Date.now();

    // 1. Initial page view
    this.trackPageView(this.currentPath, 0);

    // 2. Global delegated click listener across ALL interactive elements
    document.addEventListener('click', this.handleDocumentClick, true);

    // 3. Flush on visibility hidden / tab close
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        this.recordRouteDwellTime();
        this.flushQueue(true);
      } else {
        this.routeStartTime = Date.now();
      }
    });

    window.addEventListener('beforeunload', () => {
      this.recordRouteDwellTime();
      this.flushQueue(true);
    });

    // 4. Periodic background flush every 15 seconds
    this.flushTimer = setInterval(() => {
      this.flushQueue(false);
    }, 15000);
  }

  public destroy() {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
  }

  public notifyRouteChange(newPath: string) {
    if (newPath === this.currentPath) return;

    // Record time spent on previous route
    this.recordRouteDwellTime();

    // Start tracking new route
    this.currentPath = newPath;
    this.currentModule = resolvePlatformModule(newPath);
    this.routeStartTime = Date.now();
    this.trackPageView(newPath, 0);
  }

  public trackAction(category: string, name: string, metadata: Record<string, any> = {}) {
    this.pushEvent({
      session_id: getSessionId(),
      event_type: 'action',
      module: this.currentModule || resolvePlatformModule(window.location.pathname),
      page_route: window.location.pathname,
      action_category: category,
      action_name: name,
      duration_seconds: 0,
      metadata,
    });
  }

  /**
   * Automatically track platform features invoked via API calls
   */
  public trackApiFeature(url: string, method: string = 'GET') {
    if (!url || url.includes('/telemetry/events') || url.includes('/system/ping')) {
      return;
    }

    const u = url.toLowerCase();
    const m = method.toUpperCase();

    let featureGroup = 'other';
    let featureName = `${m} ${url}`;

    if (u.includes('/completion') || u.includes('/conversation')) {
      featureGroup = 'chat';
      featureName = m === 'POST' ? 'AI Chat Xabar Generatsiyasi' : 'Chat Tarixini Yuklash';
    } else if (u.includes('/document/upload')) {
      featureGroup = 'datasets';
      featureName = 'Hujjat Yuklash (Upload)';
    } else if (u.includes('/document/run') || u.includes('/chunk/')) {
      featureGroup = 'datasets';
      featureName = 'Hujjatni Bo‘laklash & Parsing (Chunking)';
    } else if (u.includes('/dataset/save') || u.includes('/kb/')) {
      featureGroup = 'datasets';
      featureName = 'Bilimlar Bazasi Saqlash';
    } else if (u.includes('/canvas/')) {
      featureGroup = 'agent_canvas';
      featureName = u.includes('test') ? 'Agent Flow Sinov (Test Run)' : 'Agent Canvas Saqlash (Save Flow)';
    } else if (u.includes('/crm/')) {
      featureGroup = 'crm';
      featureName = u.includes('stock') ? '1C Sklad Qoldiqlarini Tekshirish' : 'CRM Lid Yaratish & Sinxronizatsiya';
    } else if (u.includes('/search') || u.includes('/retrieval')) {
      featureGroup = 'search';
      featureName = 'Gibrid Qidiruv & Semantik Retrieval';
    } else if (u.includes('/model') || u.includes('/provider')) {
      featureGroup = 'settings';
      featureName = 'LLM Model & Provider Sozlamalari';
    } else if (u.includes('/payment') || u.includes('/checkout')) {
      featureGroup = 'settings';
      featureName = 'Tarif & To‘lov Boshlash';
    } else if (u.includes('/skills')) {
      featureGroup = 'files_skills';
      featureName = 'Ko‘nikmalar (Skills) Boshqaruvi';
    } else if (u.includes('/mcp')) {
      featureGroup = 'agent_canvas';
      featureName = 'MCP Tool Integratsiyasi';
    } else if (u.includes('/admin')) {
      featureGroup = 'admin';
      featureName = 'Admin Boshqaruv Operatsiyasi';
    }

    this.pushEvent({
      session_id: getSessionId(),
      event_type: 'action',
      module: featureGroup,
      page_route: window.location.pathname,
      action_category: 'feature_usage',
      action_name: featureName,
      element_tag: 'api',
      element_id: url.split('?')[0],
      element_label: featureName,
      duration_seconds: 0,
      metadata: { method: m, endpoint: url.split('?')[0] },
    });
  }

  private trackPageView(route: string, durationSeconds: number) {
    this.pushEvent({
      session_id: getSessionId(),
      event_type: 'page_view',
      module: resolvePlatformModule(route),
      page_route: route,
      action_category: 'navigation',
      action_name: 'view_page',
      duration_seconds: durationSeconds,
    });
  }

  private recordRouteDwellTime() {
    const elapsedSeconds = Math.max(0, (Date.now() - this.routeStartTime) / 1000);
    if (elapsedSeconds > 1 && this.currentPath) {
      this.pushEvent({
        session_id: getSessionId(),
        event_type: 'page_view',
        module: this.currentModule,
        page_route: this.currentPath,
        action_category: 'navigation',
        action_name: 'dwell_time',
        duration_seconds: Math.round(elapsedSeconds * 10) / 10,
      });
    }
    this.routeStartTime = Date.now();
  }

  private handleDocumentClick = (e: MouseEvent) => {
    try {
      const target = e.target as HTMLElement | null;
      if (!target) return;

      // Selector capturing all interactive elements
      const selector = [
        'button',
        'a',
        '[role="button"]',
        '[role="switch"]',
        '[role="tab"]',
        '[role="menuitem"]',
        '[role="option"]',
        '[role="checkbox"]',
        'input[type="submit"]',
        'input[type="checkbox"]',
        'input[type="radio"]',
        '[data-track-action]',
        '.ant-btn',
        '.ant-switch',
        '.ant-tabs-tab',
      ].join(', ');

      const interactive = target.closest(selector) as HTMLElement | null;
      if (!interactive) return;

      const tag = interactive.tagName.toLowerCase();
      const role = interactive.getAttribute('role');
      const elementTag = role || tag;
      const elementId = interactive.id || interactive.getAttribute('data-testid') || undefined;

      // Extract text or deduce from icon/attributes
      let label = (
        interactive.getAttribute('data-track-action') ||
        interactive.getAttribute('aria-label') ||
        interactive.getAttribute('title') ||
        interactive.getAttribute('data-tooltip') ||
        interactive.innerText ||
        ''
      ).trim();

      // If text is empty (e.g. icon-only button), deduce semantic action from Lucide/SVG class
      if (!label) {
        const svg = interactive.querySelector('svg');
        if (svg) {
          const svgClasses = (svg.getAttribute('class') || '').toLowerCase();
          for (const [key, name] of Object.entries(ICON_ACTION_MAP)) {
            if (svgClasses.includes(key)) {
              label = name;
              break;
            }
          }
        }
      }

      // Check parent container context (e.g. inside a dialog or modal)
      let containerContext = '';
      const modal = interactive.closest('[role="dialog"], .ant-modal, .ant-drawer');
      if (modal) {
        const modalHeader = modal.querySelector('h1, h2, h3, [class*="title"], .ant-modal-title');
        if (modalHeader && modalHeader.textContent) {
          containerContext = modalHeader.textContent.trim().substring(0, 40);
        }
      }

      if (label) {
        label = label.replace(/\s+/g, ' ').substring(0, 100);
        if (containerContext && !label.includes(containerContext)) {
          label = `[${containerContext}] ${label}`;
        }
      }

      if (!label && !elementId) {
        label = `Tugma (${elementTag})`;
      }

      this.pushEvent({
        session_id: getSessionId(),
        event_type: 'click',
        module: this.currentModule || resolvePlatformModule(window.location.pathname),
        page_route: window.location.pathname,
        action_category: 'interaction',
        action_name: `click_${elementTag}`,
        element_tag: elementTag,
        element_id: elementId,
        element_label: label || elementId,
        duration_seconds: 0,
      });
    } catch {
      // Telemetry should never crash host application
    }
  };

  private pushEvent(event: TelemetryRawEvent) {
    this.queue.push(event);
    if (this.queue.length >= 15) {
      this.flushQueue(false);
    }
  }

  public flushQueue(isUrgent: boolean = false) {
    if (this.queue.length === 0) return;

    const batch = [...this.queue];
    this.queue = [];

    const payload = JSON.stringify({ events: batch });

    if (isUrgent && typeof navigator !== 'undefined' && navigator.sendBeacon) {
      try {
        const blob = new Blob([payload], { type: 'application/json' });
        navigator.sendBeacon('/v1/telemetry/events', blob);
        return;
      } catch {
        // Fallback to fetch
      }
    }

    fetch('/v1/telemetry/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: payload,
      keepalive: isUrgent,
    }).catch(() => {
      // Graceful fail without breaking user UX
    });
  }
}

export const telemetryTracker = new PlatformTelemetryTracker();
