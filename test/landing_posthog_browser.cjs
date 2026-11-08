/* Run: node --test test/landing_posthog_browser.cjs. Never contacts a server. */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const repo = path.resolve(__dirname, "..");
const { JSDOM, VirtualConsole, CookieJar } = require(
  path.join(repo, "web/node_modules/jsdom"),
);
const site = path.join(repo, "new site for swipies");
const tracker = fs.readFileSync(path.join(site, "posthog-tracker.js"), "utf8");
const config = {
  enabled: true,
  internal: false,
  project_token: "public-test-token",
  api_host: "https://us.i.posthog.com",
  asset_host: "https://us-assets.i.posthog.com",
  allowed_hosts: ["swipies.app", "www.swipies.app", "api.swipies.app"],
};
const visitor = "v_abcdefghijk_1794000000000";
const settle = async () => {
  for (let n = 0; n < 8; n++)
    await new Promise((resolve) => setImmediate(resolve));
};
function environment(options = {}) {
  const dom = new JSDOM(
    '<!doctype html><head></head><body><button data-i18n="starter_cta"><span>Pro</span></button><input value="private@example.com"><section id="pricing"></section></body>',
    {
      url:
        options.url ||
        "https://swipies.app/?utm_source=search&utm_campaign=autumn&token=SECRET&email=private%40example.com",
      referrer: "https://search.example/private?token=SECRET",
      runScripts: "outside-only",
      pretendToBeVisual: true,
      cookieJar: options.jar || new CookieJar(),
      virtualConsole: new VirtualConsole(),
    },
  );
  const w = dom.window,
    events = [],
    calls = [],
    observers = [];
  if (options.accepted !== false)
    w.localStorage.setItem("swipies_cookie_consent", "accepted");
  if (options.admin)
    w.localStorage.setItem("swipies_admin_token", "test-only-admin");
  if (options.dnt)
    Object.defineProperty(w.navigator, "doNotTrack", { value: "1" });
  w.localStorage.setItem("swipies_visitor_id", visitor);
  w.handleCookieConsent = function (decision) {
    w.localStorage.setItem("swipies_cookie_consent", decision);
    return 17;
  };
  w.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    if (options.fetch) return options.fetch(url, init);
    return { ok: true, json: async () => config };
  };
  w.IntersectionObserver = class {
    constructor(callback) {
      observers.push(this);
      this.callback = callback;
    }
    observe() {}
    disconnect() {
      this.disconnected = true;
    }
  };
  let sdkOptions,
    instance,
    initCount = 0;
  function installFake() {
    w.posthog = {
      init(_key, settings) {
        initCount++;
        sdkOptions = settings;
        instance = {
          capture(name, props) {
            const event = settings.before_send({
              event: name,
              properties: {
                $current_url: w.location.href,
                $set: { email: "private@example.com" },
                $session_id: "test-session",
                token: config.project_token,
                ...props,
              },
            });
            if (event) events.push(event);
            return event;
          },
          opt_in_capturing() {},
          opt_out_capturing() {},
        };
        settings.loaded(instance);
        return instance;
      },
    };
  }
  if (!options.deferSDK) installFake();
  return {
    dom,
    w,
    calls,
    events,
    observers,
    installFake,
    get options() {
      return sdkOptions;
    },
    get instance() {
      return instance;
    },
    get initCount() {
      return initCount;
    },
    start() {
      w.eval(tracker);
    },
    stop() {
      dom.window.close();
    },
  };
}
test("local, automated/debug, internal and unconsented pages do not fetch or capture", async () => {
  for (const options of [
    { url: "http://127.0.0.1:8785/" },
    { url: "https://swipies.app/?ph_test=1" },
    { admin: true },
    { dnt: true },
    { accepted: false },
  ]) {
    const e = environment(options);
    try {
      e.start();
      await settle();
      assert.equal(e.calls.length, 0);
      assert.equal(e.events.length, 0);
      assert.equal(e.w.document.querySelectorAll("script").length, 0);
    } finally {
      e.stop();
    }
  }
});
test("one view per path, no duplicate listeners; clicks, plans, pricing and register start are distinct", async () => {
  const e = environment();
  try {
    e.start();
    await settle();
    e.start();
    await settle();
    e.w.dispatchEvent(new e.w.PopStateEvent("popstate"));
    assert.equal(e.events.length, 1);
    assert.equal(e.initCount, 1);
    assert.equal(e.options.disable_session_recording, true);
    assert.equal(e.options.autocapture, false);
    assert.equal(e.options.person_profiles, "never");
    e.w.document.querySelector("button span").click();
    e.observers[0].callback([{ isIntersecting: true }]);
    e.observers[0].callback([{ isIntersecting: true }]);
    e.w.dispatchEvent(new e.w.Event("swipies:registration-started"));
    e.w.dispatchEvent(new e.w.Event("swipies:registration-started"));
    const counts = (name) => e.events.filter((x) => x.event === name).length;
    assert.equal(counts("cta_click"), 1);
    assert.equal(counts("plan_selected"), 1);
    assert.equal(counts("pricing_viewed"), 1);
    assert.equal(counts("registration_started"), 1);
    e.w.history.pushState({}, "", "/agents.html?password=SECRET");
    e.w.dispatchEvent(new e.w.PopStateEvent("popstate"));
    assert.equal(counts("$pageview"), 2);
    assert.equal(e.calls.filter((x) => x.url.endsWith("/consent")).length, 1);
    for (const call of e.calls)
      assert.equal(call.init.referrerPolicy, "no-referrer");
  } finally {
    e.stop();
  }
});
test("privacy allowlist strips URLs, form values, person properties and sensitive UTM; client successes rejected", async () => {
  const e = environment({
    url: "https://swipies.app/private-token-path?utm_source=private%40example.com&utm_campaign=phx_SECRET&token=SECRET",
  });
  try {
    e.start();
    await settle();
    const output = e.options.before_send({
      event: "cta_click",
      properties: {
        token: config.project_token,
        cta_id: "hero_start",
        $session_id: "valid-session",
        $geoip_disable: false,
        $ip: "192.0.2.19",
        $current_url: "SECRET",
        $referrer: "SECRET",
        password: "SECRET",
        email: "private@example.com",
        $set_once: { secret: "SECRET" },
        plan: "private@example.com",
      },
    });
    assert.equal(output.properties.page_path, "/[other]");
    assert.equal(output.properties.referrer_origin, "https://search.example");
    assert.equal(output.properties.utm_source, "");
    assert.equal(output.properties.utm_campaign, "");
    assert.equal(output.properties.cta_id, "hero_start");
    assert.equal(output.properties.$session_id, "valid-session");
    assert.equal(output.properties.$geoip_disable, true);
    assert.equal(output.properties.$ip, null);
    assert.doesNotMatch(
      JSON.stringify(output),
      /SECRET|private@example|\$set|\$current_url|password|email/,
    );
    for (const event of [
      "registration_completed",
      "payment_completed",
      "$autocapture",
      "$snapshot",
      "$identify",
    ])
      assert.equal(e.options.before_send({ event, properties: {} }), null);
  } finally {
    e.stop();
  }
});
test("failed consent prevents SDK loading; ordinary actions keep their behavior", async () => {
  const e = environment({
    deferSDK: true,
    fetch: async (url) =>
      String(url).endsWith("/config")
        ? { ok: true, json: async () => config }
        : { ok: false },
  });
  try {
    let clicks = 0;
    e.w.document
      .querySelector("button")
      .addEventListener("click", () => clicks++);
    e.start();
    await settle();
    e.w.document.querySelector("button").click();
    assert.equal(clicks, 1);
    assert.equal(e.w.document.querySelectorAll("script").length, 0);
    assert.equal(
      e.w.document.querySelector("input").value,
      "private@example.com",
    );
    assert.equal(e.w.handleCookieConsent("declined"), 17);
    await settle();
    assert.equal(e.events.length, 0);
  } finally {
    e.stop();
  }
});
test("withdrawal while official script loads captures nothing; regrant uses one loader and ordered receipts", async () => {
  const e = environment({ deferSDK: true });
  try {
    e.start();
    await settle();
    const script = e.w.document.querySelector("script");
    assert.ok(script);
    assert.equal(script.referrerPolicy, "no-referrer");
    e.w.handleCookieConsent("declined");
    await settle();
    e.installFake();
    script.onload();
    await settle();
    assert.equal(e.events.length, 0);
    e.w.handleCookieConsent("accepted");
    await settle();
    assert.equal(e.events.filter((x) => x.event === "$pageview").length, 1);
    assert.equal(e.initCount, 1);
    assert.deepEqual(
      e.calls
        .filter((x) => x.url.endsWith("/consent"))
        .map((x) => JSON.parse(x.init.body).granted),
      [true, false, true],
    );
  } finally {
    e.stop();
  }
});
test("shared consent and identity work across landing and platform without transmitting credentials", async () => {
  const jar = new CookieJar(),
    landing = environment({ jar });
  let platform;
  try {
    landing.start();
    await settle();
    platform = environment({
      jar,
      url: "https://api.swipies.app/register?access_token=SECRET",
      accepted: false,
    });
    platform.w.localStorage.removeItem("swipies_cookie_consent");
    platform.w.localStorage.removeItem("swipies_visitor_id");
    platform.start();
    await settle();
    assert.equal(platform.events[0].properties.distinct_id, visitor);
    assert.equal(platform.events[0].properties.site_area, "platform");
    assert.doesNotMatch(JSON.stringify(platform.calls), /access_token|SECRET/);
    platform.w.handleCookieConsent("declined");
    await settle();
    platform.w.dispatchEvent(
      new platform.w.Event("swipies:registration-started"),
    );
    assert.equal(platform.events.length, 1);
  } finally {
    landing.stop();
    platform?.stop();
  }
});
test("single nav entry moves between mobile and desktop and leaves existing navigation alone", () => {
  const dom = new JSDOM(
    '<nav class="sidebar-nav"><a id="old">Old</a></nav><nav class="mobile-nav"></nav>',
    { url: "https://swipies.app/admin.html", runScripts: "outside-only" },
  );
  try {
    const media = {
      matches: false,
      addEventListener(_event, cb) {
        this.change = cb;
      },
    };
    dom.window.matchMedia = () => media;
    let oldClicks = 0;
    dom.window.document
      .getElementById("old")
      .addEventListener("click", () => oldClicks++);
    const nav = fs.readFileSync(path.join(site, "posthog-nav.js"), "utf8");
    dom.window.eval(nav);
    dom.window.eval(nav);
    assert.equal(
      dom.window.document.querySelectorAll("#swipiesPosthogLink").length,
      1,
    );
    media.matches = true;
    media.change();
    assert.ok(
      dom.window.document.querySelector(".mobile-nav #swipiesPosthogLink"),
    );
    dom.window.document.getElementById("old").click();
    assert.equal(oldClicks, 1);
  } finally {
    dom.window.close();
  }
});
test("dashboard setup shows configuration without dummy metrics; unauthorized access shows an error", async () => {
  for (const unauthorized of [false, true]) {
    const dom = new JSDOM(
      fs.readFileSync(path.join(site, "posthog.html"), "utf8"),
      { url: "https://swipies.app/admin/posthog", runScripts: "outside-only" },
    );
    try {
      dom.window.localStorage.setItem("swipies_admin_token", "synthetic-owner");
      dom.window.fetch = async () => ({
        ok: !unauthorized,
        status: unauthorized ? 401 : 200,
        json: async () => ({
          code: 0,
          data: {
            reports_ready: false,
            required_environment: ["POSTHOG_READ_API_KEY"],
            setup: ["Use query:read"],
          },
        }),
      });
      dom.window.eval(
        fs.readFileSync(path.join(site, "posthog-admin.js"), "utf8"),
      );
      await settle();
      assert.ok(dom.window.document.getElementById("phReport").hidden);
      if (unauthorized)
        assert.match(
          dom.window.document.getElementById("phStatus").textContent,
          /Сессия завершена/,
        );
      else {
        assert.equal(
          dom.window.document.getElementById("phSetup").hidden,
          false,
        );
        assert.match(
          dom.window.document.getElementById("phSetupVars").textContent,
          /POSTHOG_READ_API_KEY/,
        );
      }
    } finally {
      dom.window.close();
    }
  }
});
test("dashboard renders browser counts separately from clicks, escapes dimensions, and preserves last report on failure", async () => {
  const dom = new JSDOM(
    fs.readFileSync(path.join(site, "posthog.html"), "utf8"),
    { url: "https://swipies.app/admin/posthog", runScripts: "outside-only" },
  );
  try {
    const w = dom.window;
    let failure = false;
    w.localStorage.setItem("swipies_admin_token", "synthetic-owner");
    const funnel = [
      { stage: "Landing", visitors: 10 },
      { stage: "CTA", visitors: 4, lost: 6, from_previous_percent: 40 },
    ];
    const comparison = {
      registrations: {
        posthog: 2,
        system: 3,
        difference: -1,
        definition: "same period",
      },
      payments: {
        posthog: 1,
        system: null,
        difference: null,
        unavailable: "not comparable",
      },
    };
    const fixture = {
      state: "ready",
      filters: {
        start: "2026-11-01T00:00:00Z",
        end: "2026-11-02T00:00:00Z",
        compare_start: "2026-10-31T00:00:00Z",
        compare_end: "2026-11-01T00:00:00Z",
        timezone: "UTC",
      },
      updated_at: "2026-11-08T00:00:00Z",
      empty: false,
      metrics: [
        {
          key: "visitors",
          current: 10,
          previous: 8,
          change: { absolute: 2, percent: 25, state: "changed" },
        },
      ],
      funnel: { current: funnel, previous: funnel },
      ctas: [["current", "hero_start", 4, 17]],
      acquisition: [
        [
          "current",
          "<img src=x onerror=alert(1)>",
          "campaign",
          "https://source.example",
          4,
          8,
        ],
      ],
      devices: [["current", "desktop", 10, 15]],
      comparison: { current: comparison, previous: comparison },
      comparison_notes: ["consent"],
      definitions: { visitors: "anonymous browser IDs" },
      timeline: [
        ["current", "2026-11-01T00:00:00Z", 10, 15, 2, 1],
        ["previous", "2026-10-31T00:00:00Z", 8, 9, 1, 0],
      ],
      breakdowns_limit: "Top list is bounded.",
    };
    w.fetch = async (url) => ({
      ok: !failure,
      status: failure ? 503 : 200,
      json: async () => ({
        code: failure ? 1 : 0,
        message: "Unavailable",
        data: url.endsWith("/status") ? { reports_ready: true } : fixture,
      }),
    });
    w.eval(fs.readFileSync(path.join(site, "posthog-admin.js"), "utf8"));
    await settle();
    const d = w.document;
    assert.equal(d.getElementById("phReport").hidden, false);
    assert.match(
      d.getElementById("phCtas").textContent,
      /Посетители сейчас.*Клики сейчас.*hero_start417/s,
    );
    assert.equal(d.querySelectorAll("#phSources img").length, 0);
    assert.match(
      d.getElementById("phSources").textContent,
      /https:\/\/source.example/,
    );
    assert.ok(d.querySelector("#phChart svg"));
    assert.match(d.getElementById("phPeriods").textContent, /UTC/);
    failure = true;
    d.getElementById("phFilters").dispatchEvent(
      new w.Event("submit", { cancelable: true }),
    );
    await settle();
    assert.match(
      d.getElementById("phStatus").textContent,
      /предыдущий успешный отчёт/,
    );
    assert.equal(d.getElementById("phReport").hidden, false);
  } finally {
    dom.window.close();
  }
});
test(
  "official CDN SDK executes the privacy hook and produces a real pageview payload",
  { skip: !process.env.POSTHOG_SDK_FILE },
  async () => {
    const e = environment({ deferSDK: true });
    try {
      e.w.navigator.sendBeacon = () => true;
      e.w.XMLHttpRequest = class {
        open() {}
        setRequestHeader() {}
        send() {
          this.status = 200;
          this.readyState = 4;
          this.responseText = "{}";
          this.onreadystatechange?.();
          this.onload?.();
        }
        addEventListener() {}
        abort() {}
      };
      e.w.eval(fs.readFileSync(process.env.POSTHOG_SDK_FILE, "utf8"));
      const original = e.w.posthog.init.bind(e.w.posthog),
        captured = [];
      e.w.posthog.init = (key, settings, name) => {
        const before = settings.before_send;
        settings.before_send = (event) => {
          const safe = before(event);
          if (safe) captured.push(safe);
          return safe;
        };
        return original(key, settings, name);
      };
      e.start();
      await settle();
      const view = captured.find((x) => x.event === "$pageview");
      assert.ok(view, "Actual SDK called before_send for pageview");
      assert.equal(view.properties.distinct_id, visitor);
      assert.ok(view.properties.$session_id);
      assert.equal(view.properties.$geoip_disable, true);
      assert.equal(view.properties.$ip, null);
      assert.doesNotMatch(
        JSON.stringify(captured),
        /SECRET|private@example|\$set|\$current_url/,
      );
    } finally {
      e.stop();
    }
  },
);
