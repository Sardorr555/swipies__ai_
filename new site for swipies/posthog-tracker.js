/* Explicit analytics only. No form content, autocapture, replay or URL queries. */
(() => {
  "use strict";
  if (window.SwipiesPostHog) return;
  const hosts = new Set(["swipies.app", "www.swipies.app", "api.swipies.app"]);
  const idPattern = /^(?:v_[a-z0-9]{6,20}_[0-9]{13}|[a-f0-9-]{36})$/;
  const ownScript = document.currentScript;
  const configUrl =
    ownScript?.dataset.swipiesPosthogConfig || "/api/posthog/config";
  const consentUrl = new URL(
    "/api/posthog/consent",
    new URL(configUrl, location.origin),
  ).href;
  const ctas = {
    nav_cta: "nav_start",
    hero_cta1: "hero_start",
    hero_cta2_b2c: "explore_plans",
    hero_cta_enterprise: "hero_enterprise",
    cloud_banner_btn: "cloud_start",
    agent_guide: "agent_guide",
    agent_copy: "agent_instructions",
    basic_cta: "choose_plus",
    starter_cta: "choose_pro",
    license_cta: "choose_license",
    ent_b2c_cta: "contact_enterprise",
    ent_upsell_btn: "enterprise_details",
    form_submit: "contact_submit",
  };
  const plans = {
    basic_cta: "plus",
    starter_cta: "pro",
    license_cta: "license",
    ent_b2c_cta: "enterprise",
  };
  const storage = (key) => {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  };
  const cookie = (key) => {
    try {
      return decodeURIComponent(
        document.cookie
          .split(";")
          .map((x) => x.trim())
          .find((x) => x.startsWith(key + "="))
          ?.slice(key.length + 1) || "",
      );
    } catch {
      return "";
    }
  };
  const setCookie = (key, value, maxAge = 7776000) => {
    document.cookie =
      key +
      "=" +
      encodeURIComponent(value) +
      "; Path=/; Domain=swipies.app; Max-Age=" +
      maxAge +
      "; Secure; SameSite=Lax";
  };
  let instance = null,
    config = null,
    loading = false,
    ready = false,
    identity = "",
    lastConsent = null,
    lastPage = "",
    registrationSent = false,
    pricingSent = false;
  let generation = 0,
    approvedGeneration = 0,
    sdkLoading = false,
    consentTasks = Promise.resolve();
  const queue = [];
  const consent = () => {
    const saved = storage("swipies_cookie_consent");
    return (
      saved === "accepted" ||
      (!saved && cookie("swipies_posthog_allowed") === "1")
    );
  };
  const internal = () => {
    if (
      !hosts.has(location.hostname) ||
      navigator.webdriver ||
      navigator.doNotTrack === "1"
    )
      return true;
    if (
      storage("swipies_admin_token") ||
      storage("swipies_admin_session") === "authenticated"
    )
      return true;
    const params = new URLSearchParams(location.search);
    return ["test", "debug", "preview", "e2e", "ph_test"].some((key) =>
      params.has(key),
    );
  };
  const tag = (value) => {
    value = String(value || "");
    return /^[A-Za-z0-9][A-Za-z0-9_. -]{0,63}$/.test(value) &&
      !/[a-f0-9]{32,}|(?:phc_|phx_|eyJ)/i.test(value)
      ? value
      : "";
  };
  const pagePath = () => {
    const path = location.pathname.replace(/\/$/, "") || "/";
    return [
      "/",
      "/index.html",
      "/login.html",
      "/agents.html",
      "/login",
      "/register",
      "/pricing",
      "/terms.html",
      "/privacy.html",
      "/offer.html",
    ].includes(path)
      ? path
      : "/[other]";
  };
  const referrer = () => {
    try {
      const url = new URL(document.referrer);
      return ["http:", "https:"].includes(url.protocol) ? url.origin : "";
    } catch {
      return "";
    }
  };
  const properties = () => {
    const params = new URLSearchParams(location.search),
      area = location.hostname === "api.swipies.app" ? "platform" : "landing";
    const result = {
      site_area: area,
      page_path: pagePath(),
      referrer_origin: referrer(),
      device_type: /tablet|ipad/i.test(navigator.userAgent)
        ? "tablet"
        : /mobile|android|iphone/i.test(navigator.userAgent)
          ? "mobile"
          : "desktop",
      swipies_environment: "production",
      swipies_internal: false,
      swipies_schema: "1",
      swipies_origin: "browser",
    };
    for (const key of [
      "utm_source",
      "utm_medium",
      "utm_campaign",
      "utm_term",
      "utm_content",
    ])
      result[key] = tag(params.get(key));
    return result;
  };
  function beforeSend(event) {
    if (
      !consent() ||
      internal() ||
      ![
        "$pageview",
        "cta_click",
        "pricing_viewed",
        "plan_selected",
        "registration_started",
      ].includes(event.event)
    )
      return null;
    const safe = { ...properties(), distinct_id: identity };
    const input = event.properties || {};
    // Preserve only SDK identifiers required for delivery/session counting.
    for (const key of [
      "$session_id",
      "$window_id",
      "$device_id",
      "$insert_id",
    ]) {
      const value = String(input[key] || "");
      if (
        /^[A-Za-z0-9_-]{1,100}$/.test(value) ||
        /^[a-f0-9-]{36}$/i.test(value)
      )
        safe[key] = value;
    }
    for (const key of ["$lib", "$lib_version"]) {
      const value = String(input[key] || "");
      if (/^[A-Za-z0-9_.-]{1,32}$/.test(value)) safe[key] = value;
    }
    if (input.token === config.project_token) safe.token = input.token;
    if (input.cta_id && Object.values(ctas).includes(input.cta_id))
      safe.cta_id = input.cta_id;
    if (["plus", "pro", "license", "enterprise"].includes(input.plan))
      safe.plan = input.plan;
    // Raw URL/referrer, $set/$set_once, email, custom person properties and any
    // unrecognized SDK fields are omitted, including initial URL properties.
    return { ...event, properties: safe };
  }
  function capture(name, props = {}) {
    if (!consent() || internal()) return;
    if (!ready) {
      if (loading && queue.length < 20) queue.push([name, props]);
      return;
    }
    try {
      instance.capture(name, { ...properties(), ...props });
    } catch {
      /* optional analytics */
    }
  }
  function pageview() {
    if (!ready) return;
    const path = pagePath();
    if (path === lastPage) return;
    lastPage = path;
    capture("$pageview");
  }
  function receipt(granted) {
    const visitor = identity;
    consentTasks = consentTasks.then(async () => {
      if (!idPattern.test(visitor)) return false;
      try {
        const response = await fetch(consentUrl, {
          method: "POST",
          mode: "cors",
          credentials: "omit",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ visitor_id: visitor, granted }),
          keepalive: true,
        });
        return response.ok;
      } catch {
        return false;
      }
    });
    return consentTasks;
  }
  function initialize() {
    if (approvedGeneration !== generation || !lastConsent) return;
    const sdk = window.posthog;
    if (!sdk?.init) {
      loading = false;
      return;
    }
    const options = {
      api_host: config.api_host,
      bootstrap: { distinctID: identity, isIdentifiedID: false },
      defaults: "2025-11-30",
      persistence: "localStorage+cookie",
      cross_subdomain_cookie: true,
      person_profiles: "never",
      autocapture: false,
      capture_pageview: false,
      capture_pageleave: false,
      disable_session_recording: true,
      enable_recording_console_log: false,
      session_recording: { maskAllInputs: true, maskTextSelector: "*" },
      capture_performance: false,
      capture_heatmaps: false,
      capture_dead_clicks: false,
      disable_surveys: true,
      advanced_disable_flags: true,
      disable_external_dependency_loading: true,
      opt_out_capturing_by_default: true,
      opt_out_persistence_by_default: true,
      respect_dnt: true,
      save_referrer: false,
      store_google: false,
      mask_all_text: true,
      mask_all_element_attributes: true,
      before_send: beforeSend,
      loaded: (loaded) => {
        if (!consent() || internal() || approvedGeneration !== generation) {
          loaded.opt_out_capturing({ clear_persistence: true });
          loading = false;
          return;
        }
        instance = loaded;
        instance.opt_in_capturing();
        ready = true;
        loading = false;
        pageview();
        for (const [name, props] of queue.splice(0)) capture(name, props);
        observePricing();
      },
    };
    sdk.init(config.project_token, options, "swipies_landing");
  }
  function observePricing() {
    const section = document.getElementById("pricing");
    if (!section || !window.IntersectionObserver) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (!pricingSent && entries.some((entry) => entry.isIntersecting)) {
          pricingSent = true;
          capture("pricing_viewed");
          observer.disconnect();
        }
      },
      { threshold: 0.35 },
    );
    observer.observe(section);
  }
  async function syncConsent() {
    const allowed = consent() && !internal();
    if (lastConsent === allowed) return;
    lastConsent = allowed;
    const current = ++generation;
    if (!allowed) {
      ready = false;
      loading = false;
      approvedGeneration = 0;
      lastPage = "";
      queue.length = 0;
      try {
        instance?.opt_out_capturing({ clear_persistence: true });
      } catch {}
      identity = identity || cookie("swipies_posthog_visitor");
      if (hosts.has(location.hostname)) {
        setCookie("swipies_posthog_allowed", "", 0);
        setCookie("swipies_posthog_visitor", "", 0);
        if (config) await receipt(false);
      }
      return;
    }
    loading = true;
    try {
      const response = await fetch(configUrl, {
        credentials: "omit",
        cache: "no-store",
        mode: "cors",
      });
      if (!response.ok) throw new Error("configuration unavailable");
      config = await response.json();
      if (current !== generation) return;
      if (
        !config.enabled ||
        config.internal ||
        !config.allowed_hosts?.includes(location.hostname)
      ) {
        loading = false;
        return;
      }
      identity =
        cookie("swipies_posthog_visitor") ||
        storage("swipies_visitor_id") ||
        "";
      if (!idPattern.test(identity)) identity = crypto.randomUUID();
      if (!consent() || internal() || !(await receipt(true))) {
        if (current === generation) loading = false;
        return;
      }
      if (current !== generation) return;
      approvedGeneration = current;
      setCookie("swipies_posthog_allowed", "1");
      setCookie("swipies_posthog_visitor", identity);
      if (instance) {
        instance.opt_in_capturing();
        ready = true;
        loading = false;
        pageview();
        return;
      }
      if (window.posthog?.init) {
        initialize();
        return;
      }
      if (sdkLoading) return;
      sdkLoading = true;
      const script = document.createElement("script");
      script.src = config.asset_host + "/static/array.js";
      script.async = true;
      script.crossOrigin = "anonymous";
      script.onload = () => {
        sdkLoading = false;
        if (lastConsent) initialize();
      };
      script.onerror = () => {
        sdkLoading = false;
        loading = false;
        queue.length = 0;
      };
      document.head.appendChild(script);
    } catch {
      if (current === generation) {
        loading = false;
        queue.length = 0;
      }
    }
  }
  window.SwipiesPostHog = { syncConsent };
  if (!hosts.has(location.hostname)) return;
  document.addEventListener(
    "click",
    (event) => {
      const control = event.target.closest?.("[data-i18n]");
      const key = control?.getAttribute("data-i18n");
      if (!ctas[key]) return;
      capture("cta_click", { cta_id: ctas[key] });
      if (plans[key]) capture("plan_selected", { plan: plans[key] });
    },
    true,
  );
  window.addEventListener("swipies:registration-started", () => {
    if (!registrationSent && consent() && !internal()) {
      registrationSent = true;
      capture("registration_started");
    }
  });
  window.addEventListener("popstate", pageview);
  window.addEventListener("storage", (event) => {
    if (event.key === "swipies_cookie_consent") syncConsent();
  });
  window.addEventListener("focus", syncConsent);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") syncConsent();
  });
  if (typeof window.handleCookieConsent === "function") {
    const original = window.handleCookieConsent;
    window.handleCookieConsent = function (...args) {
      const result = original.apply(this, args);
      syncConsent();
      return result;
    };
  }
  syncConsent();
})();
