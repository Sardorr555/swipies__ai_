/* Factual period comparison. Existing admin navigation/settings remain in place. */
(() => {
  "use strict";
  const byId = (id) => document.getElementById(id);
  const escape = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const state = {
    report: null,
    request: 0,
    controller: null,
    pages: { visitors: 1, leads: 1, users: 1, campaigns: 1 },
    searches: { visitors: "", leads: "", users: "", campaigns: "" },
    recordRequests: {},
    source: "landing",
    tablePage: 1,
    busy: false,
    signature: "",
    appliedFilters: null,
    loginEmail: null,
  };
  function authorization() {
    const saved =
      (window.SWIPIES_LANDING_NATIVE_AUTH
        ? localStorage.getItem("swipies_admin_token")
        : localStorage.getItem("Authorization")) || "";
    const cookie = document.cookie
      .split(";")
      .map((x) => x.trim())
      .find((x) => x.startsWith("swipies_auth_token="));
    let value = saved;
    if (!value && cookie) {
      try {
        value = decodeURIComponent(cookie.slice(cookie.indexOf("=") + 1));
      } catch {}
    }
    return value ? (/^Bearer /i.test(value) ? value : "Bearer " + value) : "";
  }
  const headers = () => ({
    "Content-Type": "application/json",
    Authorization: authorization(),
  });
  const credentials = () =>
    state.source === "ga"
      ? {
          property_id: localStorage.getItem("swipies_ga_property_id") || "",
          service_account_key:
            localStorage.getItem("swipies_ga_service_key") || "",
        }
      : state.source === "ym"
        ? {
            counter_id: localStorage.getItem("swipies_ym_counter_id") || "",
            oauth_token: localStorage.getItem("swipies_ym_oauth_token") || "",
          }
        : {};
  const format = (value, unit = "number") =>
    value == null || !Number.isFinite(Number(value))
      ? "—"
      : new Intl.NumberFormat("ru-RU", {
          maximumFractionDigits: ["percent", "seconds"].includes(unit) ? 1 : 2,
        }).format(value) +
        (unit === "percent" ? "%" : unit === "seconds" ? " с" : "");
  const zone = () => byId("analyticsTimezone").value.trim() || "Asia/Tashkent";
  function parts(instant, tz = zone()) {
    return Object.fromEntries(
      new Intl.DateTimeFormat("sv-SE", {
        timeZone: tz,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hourCycle: "h23",
      })
        .formatToParts(instant)
        .filter((x) => x.type !== "literal")
        .map((x) => [x.type, x.value]),
    );
  }
  function wall(instant, tz = zone()) {
    const p = parts(instant, tz);
    return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
  }
  function instant(value, tz = zone()) {
    if (!/^\d{4}-\d\d-\d\dT\d\d:00$/.test(value))
      throw new Error("Укажите даты с точностью до целого часа.");
    const intended = Date.parse(value + "Z");
    let result = intended;
    for (let i = 0; i < 4; i++) {
      const actual = Date.parse(wall(new Date(result), tz) + "Z");
      result += intended - actual;
    }
    if (wall(new Date(result), tz) !== value)
      throw new Error(
        "Этот час отсутствует при переходе времени. Выберите соседний час.",
      );
    return new Date(result).toISOString();
  }
  function filters() {
    return {
      start: instant(byId("analyticsStart").value),
      end: instant(byId("analyticsEnd").value),
      timezone: zone(),
      group: byId("analyticsGroup").value,
      comparison: byId("analyticsCompareMode").value,
      compare_start: byId("analyticsCompareStart").value
        ? instant(byId("analyticsCompareStart").value)
        : undefined,
      compare_end: byId("analyticsCompareEnd").value
        ? instant(byId("analyticsCompareEnd").value)
        : undefined,
      utm_source: byId("analyticsUtmSource").value.trim(),
      utm_campaign: byId("analyticsUtmCampaign").value.trim(),
    };
  }
  const body = () => ({
    filters: filters(),
    source: state.source,
    credentials: credentials(),
  });
  function status(message = "", error = false) {
    const node = byId("analyticsStatus");
    if (!node) return;
    node.textContent = message;
    node.classList.toggle("error", error);
  }
  async function jsonPost(path, data, signal) {
    const response = await fetch("/api/admin/analytics/" + path, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify(data),
      signal,
      cache: "no-store",
    });
    if (
      !(response.headers.get("content-type") || "").includes("application/json")
    )
      throw new Error("Обновите сервис API лендинга: он не вернул JSON.");
    const payload = await response.json();
    if (!response.ok || payload.code !== 0)
      throw new Error(payload.message || "Не удалось загрузить данные.");
    return payload;
  }
  function preset(name) {
    const now = wall(new Date());
    const local = new Date(now.slice(0, 14) + "00:00Z");
    let start = new Date(local);
    if (name === "today") start.setUTCHours(0, 0, 0, 0);
    else if (name === "yesterday") {
      start.setUTCDate(start.getUTCDate() - 1);
      start.setUTCHours(0, 0, 0, 0);
      local.setUTCHours(0, 0, 0, 0);
    } else if (name === "week") {
      start.setUTCDate(start.getUTCDate() - ((start.getUTCDay() + 6) % 7));
      start.setUTCHours(0, 0, 0, 0);
    } else if (name === "month") {
      start.setUTCDate(1);
      start.setUTCHours(0, 0, 0, 0);
    } else start.setUTCDate(start.getUTCDate() - Number(name || 30));
    byId("analyticsStart").value = start.toISOString().slice(0, 16);
    byId("analyticsEnd").value = local.toISOString().slice(0, 16);
    if (["today", "yesterday"].includes(name))
      byId("analyticsGroup").value = "hour";
  }
  function dateLabel(value) {
    let input = String(value).replace(" ", "T");
    if (/^\d{4}-\d\d-\d\dT/.test(input) && !/(?:Z|[+-]\d\d:\d\d)$/.test(input))
      input += "Z";
    return new Intl.DateTimeFormat("ru-RU", {
      timeZone: state.report?.filters.timezone || zone(),
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).format(new Date(input));
  }
  function change(metric) {
    const data = metric.change;
    if (data.absolute == null) return "Нет данных для сравнения";
    if (metric.unit === "percent")
      return `${data.absolute > 0 ? "+" : ""}${format(data.absolute, "seconds").replace(" с", "")} п.п.`;
    const absolute = `${data.absolute > 0 ? "+" : ""}${format(data.absolute, metric.unit)}`;
    return data.state === "new"
      ? `${absolute} · ранее 0`
      : `${data.percent > 0 ? "+" : ""}${format(data.percent)}% · ${absolute}`;
  }
  function renderCards(report) {
    const sourceNames = {
      traffic:
        state.source === "landing"
          ? "Журнал"
          : state.source === "ga"
            ? "GA4"
            : "Метрика",
      platform: "Платформа",
      landing: "Лендинг",
    };
    const renderMetric = (metric) => {
      const reverse = metric.key === "bounce_rate";
      const up = metric.change.absolute > 0;
      const color =
        metric.change.absolute === 0 || metric.change.absolute == null
          ? ""
          : up !== reverse
            ? "up"
            : "down";
      return `<article class="analytics-metric"><div class="analytics-metric-label"><span>${escape(metric.label)}</span><span class="analytics-metric-source">${sourceNames[metric.source]}</span></div><div class="analytics-metric-value">${format(metric.current, metric.unit)}</div><div class="analytics-metric-prev">Было: ${format(metric.previous, metric.unit)}</div><div class="analytics-metric-change ${color}">${escape(change(metric))}</div>${metric.reason ? `<p class="analytics-metric-reason">${escape(metric.reason)}</p>` : ""}</article>`;
    };
    const primary = [
      "visitors",
      "new_users",
      "revenue_uzs",
      "leads",
      "visits",
      "paid_payments",
      "payment_rate",
      "lead_rate",
    ];
    byId("analyticsMetrics").innerHTML = primary
      .map((key) => report.metrics.find((metric) => metric.key === key))
      .filter(Boolean)
      .map(renderMetric)
      .join("");
    byId("analyticsExtraMetrics").innerHTML = report.metrics
      .filter((metric) => !primary.includes(metric.key))
      .map(renderMetric)
      .join("");
    if (byId("analyticsCurrentRange"))
      byId("analyticsCurrentRange").textContent =
        dateLabel(report.filters.start) + " — " + dateLabel(report.filters.end);
    if (byId("analyticsPreviousRange"))
      byId("analyticsPreviousRange").textContent =
        dateLabel(report.filters.compare_start) +
        " — " +
        dateLabel(report.filters.compare_end);
    if (byId("analyticsZoneLabel"))
      byId("analyticsZoneLabel").textContent = report.filters.timezone;
    byId("analyticsNotes").innerHTML =
      report.notes.map((note) => `<p>${escape(note)}</p>`).join("") +
      (report.filters.equal_duration
        ? ""
        : "<p>У периодов разная длительность. Изменение сравнивает фактические итоги без нормализации на число дней.</p>");
    byId("analyticsMetricSelect").innerHTML = report.metrics
      .map(
        (metric) =>
          `<option value="${metric.key}">${escape(metric.label)}</option>`,
      )
      .join("");
  }
  function renderChart() {
    if (!state.report) return;
    const report = state.report,
      key = byId("analyticsMetricSelect").value;
    const metric = report.metrics.find((item) => item.key === key);
    const current = report.current.buckets.map(
        (bucket) => bucket.values[key] ?? null,
      ),
      previous = report.previous.buckets.map(
        (bucket) => bucket.values[key] ?? null,
      );
    const values = [...current, ...previous]
      .filter((value) => value != null && Number.isFinite(Number(value)))
      .map(Number);
    if (!values.length) {
      byId("analyticsChart").innerHTML =
        '<div class="analytics-chart-empty">Для этой метрики нет временного ряда. Выберите другой показатель или источник.</div>';
      renderDetail();
      return;
    }
    const width = 1000,
      height = 300,
      left = 65,
      right = 20,
      top = 20,
      bottom = 45;
    const count = Math.max(current.length, previous.length),
      max = Math.max(...values, 1),
      min = Math.min(...values, 0),
      span = max - min || 1;
    const x = (i) =>
        left + (i * (width - left - right)) / Math.max(count - 1, 1),
      y = (v) => height - bottom - ((v - min) * (height - top - bottom)) / span;
    const paths = (items, color, dashed) => {
      let d = "";
      let open = false;
      items.forEach((value, i) => {
        if (value == null) {
          open = false;
          return;
        }
        d += `${open ? "L" : "M"}${x(i).toFixed(2)} ${y(value).toFixed(2)} `;
        open = true;
      });
      return (
        `<path d="${d}" fill="none" stroke="${color}" stroke-width="2" ${dashed ? 'stroke-dasharray="6 5"' : ""}/>` +
        (items.length === 1 && items[0] != null
          ? `<circle cx="${x(0)}" cy="${y(items[0])}" r="4" fill="${color}"/>`
          : "")
      );
    };
    let grid = "";
    for (let i = 0; i < 5; i++) {
      const value = min + (span * i) / 4;
      grid += `<line x1="${left}" y1="${y(value)}" x2="${width - right}" y2="${y(value)}" stroke="var(--border)"/><text x="${left - 10}" y="${y(value) + 4}" text-anchor="end">${escape(format(value))}</text>`;
    }
    const points = report.current.buckets;
    for (let i = 0; i < Math.min(6, points.length); i++) {
      const index = Math.round(
        (i * (points.length - 1)) / Math.max(Math.min(6, points.length) - 1, 1),
      );
      const date = new Date(points[index].start);
      const label = new Intl.DateTimeFormat("ru-RU", {
        timeZone: report.filters.timezone,
        month: "short",
        day: "numeric",
        ...(report.filters.group === "hour"
          ? { hour: "2-digit", hourCycle: "h23" }
          : {}),
      }).format(date);
      grid += `<text x="${x(index)}" y="${height - 15}" text-anchor="middle">${escape(label)}</text>`;
    }
    byId("analyticsChart").innerHTML =
      `<svg class="analytics-chart" role="img" aria-label="${escape(metric.label)}: текущий период и период сравнения. Точные значения приведены в таблице ниже." viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">${grid}${paths(previous, "#8792a2", true)}${paths(current, "#e8a820", false)}</svg>`;
    if (byId("analyticsChartSubtitle")) byId("analyticsChartSubtitle").textContent =
      metric.label + " · сравнение по порядку временных групп";
    renderDetail();
  }
  function renderDetail() {
    const report = state.report;
    if (!report) return;
    const key = byId("analyticsMetricSelect").value,
      metric = report.metrics.find((item) => item.key === key);
    const count = Math.max(
        report.current.buckets.length,
        report.previous.buckets.length,
      ),
      start = (state.tablePage - 1) * 50;
    const rows = [];
    for (let index = start; index < Math.min(start + 50, count); index++) {
      const a = report.current.buckets[index],
        b = report.previous.buckets[index],
        current = a?.values[key],
        previous = b?.values[key];
      const diff =
        current != null && previous != null ? current - previous : null;
      rows.push(
        `<tr><td>${a ? escape(dateLabel(a.start)) : "—"}</td><td>${b ? escape(dateLabel(b.start)) : "—"}</td><td>${format(current, metric.unit)}</td><td>${format(previous, metric.unit)}</td><td>${diff == null ? "—" : (diff > 0 ? "+" : "") + format(diff, metric.unit === "percent" ? "number" : metric.unit) + (metric.unit === "percent" ? " п.п." : "")}</td></tr>`,
      );
    }
    if (!byId("analyticsDetailBody")) return;
    byId("analyticsDetailBody").innerHTML =
      rows.join("") ||
      '<tr><td colspan="5">Нет данных за выбранный период.</td></tr>';
    if (byId("analyticsDetailPage"))
      byId("analyticsDetailPage").textContent =
        `${count ? start + 1 : 0}–${Math.min(start + 50, count)} из ${count}`;
    if (byId("analyticsDetailPrev"))
      byId("analyticsDetailPrev").disabled = state.tablePage <= 1;
    if (byId("analyticsDetailNext"))
      byId("analyticsDetailNext").disabled = start + 50 >= count;
  }
  function breakdown(container, key, title) {
    const a = state.report.current.breakdowns[key] || [],
      b = state.report.previous.breakdowns[key] || [];
    const previous = new Map(b.map((item) => [item.name, item.value]));
    const names = [
      ...new Set([
        ...a.map((item) => item.name),
        ...b.map((item) => item.name),
      ]),
    ].slice(0, 15);
    const current = new Map(a.map((item) => [item.name, item.value]));
    container.innerHTML =
      `<div class="analytics-card-header"><h3>${escape(title)}</h3><span class="analytics-note">Сейчас / было · топ 15</span></div>` +
      (names
        .map(
          (name) =>
            `<div class="analytics-breakdown-item"><span title="${escape(name)}">${escape(name)}</span><span>${format(current.get(name))}</span><span style="color:var(--text-muted)">${format(previous.get(name))}</span></div>`,
        )
        .join("") ||
        '<p class="analytics-note">Нет данных за выбранные периоды.</p>');
  }
  function renderOtherTabs() {
    const a = state.report.current.totals;
    const text = (id, value) => {
      if (byId(id)) byId(id).textContent = value;
    };
    text("convDemoClicks", format(a.demo_clicks));
    text("convSalesClicks", format(a.sales_clicks));
    text("convFormSubmits", format(a.leads));
    text(
      "convDemoRate",
      a.demo_clicks != null && a.visits
        ? format((a.demo_clicks / a.visits) * 100, "percent") + " от сессий"
        : "Нет данных для расчёта",
    );
    text(
      "convSalesRate",
      a.sales_clicks != null && a.visits
        ? format((a.sales_clicks / a.visits) * 100, "percent") + " от сессий"
        : "Нет данных для расчёта",
    );
    text(
      "convFormRate",
      a.lead_rate != null
        ? format(a.lead_rate, "percent") + " от сессий"
        : "Нет данных для расчёта",
    );
    document
      .querySelectorAll("#conversionsTab .stat-trend, #utmTab .stat-trend")
      .forEach((node) => (node.style.display = "none"));
    for (const [id, key, title] of [
      ["languageDistributionChart", "languages", "Языки"],
    ]) {
      const canvas = byId(id);
      if (!canvas) continue;
      let holder = canvas.tagName === "CANVAS" ? canvas.parentElement : canvas;
      if (canvas.tagName === "CANVAS") {
        holder.innerHTML = `<div id="${id}" class="analytics-legacy-breakdown"></div>`;
        holder.style.height = "auto";
        holder = byId(id);
      }
      breakdown(holder, key, title);
    }
    const funnel = byId("funnelContainer");
    if (funnel) {
      funnel.innerHTML =
        '<p class="analytics-note">Фактические события за два периода показаны в общем отчёте. Это не когортная воронка: пользователи между этапами не сопоставляются.</p>';
    }
    const language = byId("languageTimelineChart");
    if (language) {
      const holder =
        language.tagName === "CANVAS" ? language.parentElement : language;
      holder.innerHTML =
        '<p class="analytics-note">Динамика языков по времени не измеряется этим отчётом. Сравнение итогов доступно в таблице языков.</p>';
      holder.style.height = "auto";
    }
    renderCampaigns();
  }
  function renderCampaigns() {
    if (!state.report) return;
    const groups = state.report.current.campaigns || [],
      previous = new Map(
        (state.report.previous.campaigns || []).map((row) => [
          JSON.stringify([row.source, row.medium, row.campaign]),
          row,
        ]),
      );
    const visits = groups.reduce((total, row) => total + row.visits, 0),
      duration = groups.reduce(
        (total, row) => total + row.avg_duration * row.visits,
        0,
      );
    const sources = new Map(),
      campaigns = new Map();
    for (const row of groups) {
      sources.set(row.source, (sources.get(row.source) || 0) + row.visits);
      campaigns.set(
        row.campaign,
        (campaigns.get(row.campaign) || 0) + row.visits,
      );
    }
    const top = (map) => [...map].sort((a, b) => b[1] - a[1])[0]?.[0] || "—";
    const setText = (id, val) => {
      const el = byId(id);
      if (el) el.textContent = val;
    };
    setText("utmStatTotal", format(visits));
    setText("utmStatTopSource", top(sources));
    setText("utmStatTopCampaign", top(campaigns));
    setText(
      "utmStatAvgDuration",
      visits ? format(duration / visits, "seconds") : "—",
    );
    const body = byId("utmAggTableBody");
    if (!body) return;
    const thead = body.closest("table")?.querySelector("thead");
    if (thead) {
      thead.innerHTML =
        "<tr><th>Источник / medium</th><th>Кампания</th><th>Сессии: сейчас / было</th><th>Уникальные IP</th><th>Согласие cookies</th><th>Средняя сессия</th></tr>";
    }
    body.innerHTML =
      groups
        .slice(0, 100)
        .map((row) => {
          const before = previous.get(
            JSON.stringify([row.source, row.medium, row.campaign]),
          );
          return `<tr><td>${escape(row.source)} / ${escape(row.medium)}</td><td>${escape(row.campaign)}</td><td>${format(row.visits)} / ${format(before?.visits)}</td><td>${format(row.unique_ips)}</td><td>${format(row.consent_rate, "percent")}</td><td>${format(row.avg_duration, "seconds")}</td></tr>`;
        })
        .join("") ||
      '<tr><td colspan="6">Нет UTM-сессий с выбранными датами и фильтрами.</td></tr>';
    let note = byId("analyticsCampaignNote");
    if (!note) {
      note = document.createElement("p");
      note.id = "analyticsCampaignNote";
      note.className = "analytics-note";
      body.closest(".table-wrapper")?.before(note);
    }
    note.textContent = `Журнал лендинга · ${groups.length} комбинаций UTM. Показаны первые 100 по сессиям; журнал ниже и Excel включают все подходящие записи. Прочерк означает отсутствие строки в предыдущем периоде.`;
  }
  async function refresh() {
    if (!byId("analyticsStart")) return;
    const id = ++state.request;
    state.controller?.abort();
    state.controller = new AbortController();
    try {
      const payload = body();
      state.busy = true;
      byId("analyticsApply").disabled = true;
      status("Загружаем оба периода…");
      byId("analyticsMetrics").setAttribute("aria-busy", "true");
      const result = await jsonPost("report", payload, state.controller.signal);
      if (id !== state.request) return;
      state.report = result.data;
      state.tablePage = 1;
      state.appliedFilters = payload.filters;
      state.signature = JSON.stringify({
        filters: payload.filters,
        source: payload.source,
      });
      const selected = byId("analyticsMetricSelect").value || "visitors";
      renderCards(state.report);
      if (state.report.metrics.some((item) => item.key === selected))
        byId("analyticsMetricSelect").value = selected;
      renderChart();
      breakdown(byId("analyticsChannels"), "channels", "Источники трафика");
      breakdown(byId("analyticsDevices"), "devices", "Устройства");
      renderOtherTabs();
      status(
        "Обновлено " +
          dateLabel(state.report.generated_at) +
          ". Незавершённый текущий час не включён.",
      );
      for (const table of ["leads", "users", "campaigns"])
        state.pages[table] = 1;
      const tab = typeof activeTab === "string" ? activeTab : "overview";
      if (tab === "submissions") loadRecords("leads");
      if (tab === "users") loadRecords("users");
      if (tab === "utm") loadRecords("campaigns");
      return true;
    } catch (error) {
      if (error.name === "AbortError") return;
      status(error.message, true);
      if (state.report) {
        status(
          error.message +
            " Показан предыдущий успешный отчёт; новые фильтры ещё не применены.",
          true,
        );
      } else
        byId("analyticsMetrics").innerHTML =
          '<div class="analytics-card analytics-note">Отчёт не загружен. Проверьте сообщение над фильтрами. <button type="button" id="analyticsRetry">Повторить</button></div>';
      byId("analyticsRetry")?.addEventListener("click", refresh);
      return false;
    } finally {
      if (id === state.request) {
        state.busy = false;
        byId("analyticsApply").disabled = false;
        byId("analyticsMetrics").setAttribute("aria-busy", "false");
      }
    }
  }
  async function download(kind = "report", format_ = "xlsx") {
    try {
      if (state.busy) throw new Error("Дождитесь загрузки отчёта.");
      if (
        state.signature !==
        JSON.stringify({ filters: filters(), source: state.source })
      ) {
        if (!(await refresh())) return;
        if (
          state.signature !==
          JSON.stringify({ filters: filters(), source: state.source })
        )
          throw new Error(
            "Фильтры изменились во время загрузки. Повторите применение.",
          );
      }
      const payload = {
        ...body(),
        kind,
        format: format_,
        search: state.searches[kind] || "",
      };
      status("Готовим файл с выбранными датами и фильтрами…");
      const response = await fetch("/api/admin/analytics/export", {
        method: "POST",
        headers: headers(),
        body: JSON.stringify(payload),
        cache: "no-store",
      });
      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.message || "Не удалось сформировать файл.");
      }
      const blob = await response.blob(),
        url = URL.createObjectURL(blob),
        link = document.createElement("a");
      const match = (response.headers.get("content-disposition") || "").match(
        /filename="([^"]+)"/,
      );
      link.href = url;
      link.download = match?.[1] || `swipies_${kind}.${format_}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      status("Файл сформирован по выбранным датам и фильтрам.");
    } catch (error) {
      status(error.message, true);
    }
  }
  function recordControls(table, section) {
    const target = byId(section);
    if (!target || byId("analyticsSearch-" + table)) return;
    const controls = document.createElement("form");
    controls.className = "analytics-record-search";
    controls.innerHTML = `<label class="analytics-field">Поиск в выбранном периоде<input type="search" id="analyticsSearch-${table}" maxlength="200" placeholder="Поиск по таблице"></label><button class="btn-secondary-dashboard" type="submit">Найти</button><button class="btn-secondary-dashboard" type="button" data-record-export="${table}">Excel</button>`;
    const card =
      table === "campaigns"
        ? byId("utmLogTableBody").closest(".card")
        : target.querySelector(".card");
    card.insertBefore(controls, card.querySelector(".table-wrapper"));
    controls.addEventListener("submit", (event) => {
      event.preventDefault();
      state.searches[table] = byId("analyticsSearch-" + table).value.trim();
      state.pages[table] = 1;
      loadRecords(table);
    });
    controls
      .querySelector("[data-record-export]")
      .addEventListener("click", () => download(table));
    const pager = document.createElement("div");
    pager.className = "analytics-pager";
    pager.id = "analyticsPager-" + table;
    card.appendChild(pager);
  }
  async function loadRecords(table) {
    const target = byId(
      {
        visitors: "visitorsTableBody",
        leads: "submissionsTableBody",
        users: "usersTableBody",
        campaigns: "utmLogTableBody",
      }[table],
    );
    if (!target) return;
    const requestId = (state.recordRequests[table] =
      (state.recordRequests[table] || 0) + 1);
    try {
      const result = await jsonPost("records", {
        filters: state.appliedFilters || filters(),
        table,
        search: state.searches[table],
        page: state.pages[table],
      });
      if (requestId !== state.recordRequests[table]) return;
      const records = result.data;
      if (table === "leads") {
        if (typeof databaseSubmissions !== "undefined")
          databaseSubmissions =
            typeof mapDatabaseLeads === "function"
              ? mapDatabaseLeads(records)
              : records;
        if (typeof databaseSubmissions !== "undefined")
          databaseSubmissions = databaseSubmissions.map((row, index) => ({
            ...row,
            channel: records[index]?.channel || records[index]?.source || "web",
          }));
        renderLeadRows();
      } else if (table === "visitors") {
        if (typeof currentVisitorsData !== "undefined")
          currentVisitorsData = records;
        target.innerHTML = records
          .map(
            (row) =>
              `<tr><td>${escape(row.ip || "—")}<br><span class="analytics-note">${escape([row.country, row.city].filter(Boolean).join(", "))}</span></td><td>${escape(row.isp || "—")}</td><td>${escape(row.device_type || "—")}</td><td>${escape(row.browser || "—")}</td><td>${format(row.session_duration, "seconds")} / ${format(row.scroll_depth, "percent")}</td><td>${escape(row.cookie_consent || "—")}</td><td>${escape(row.utm_source || "direct")}<br><span class="analytics-note">${escape(row.page_url || "—")}</span></td><td>${escape(dateLabel(row.create_date))}</td><td>—</td></tr>`,
          )
          .join("");
      } else if (table === "campaigns")
        target.innerHTML = records
          .map(
            (row) =>
              `<tr><td>${escape(row.ip)}<br>${escape([row.country, row.city].filter(Boolean).join(", "))}</td><td>${escape(row.utm_source)} / ${escape(row.utm_medium)}<br>${escape(row.utm_campaign)}</td><td>${escape(row.isp)}</td><td>${escape(row.device_type)} / ${escape(row.browser)}</td><td>${format(row.session_duration, "seconds")} / ${format(row.scroll_depth, "percent")}</td><td>${escape(row.cookie_consent)}</td><td>${escape(dateLabel(row.create_date))}</td></tr>`,
          )
          .join("");
      else if (window.SWIPIES_LANDING_NATIVE_AUTH) {
        target.innerHTML = records
          .map((row) => {
            const active = String(row.is_active ?? row.status) === "1";
            return `<tr><td>${escape(row.email)}<br>${escape(row.nickname)}</td><td>${escape(row.utm_source || "—")}<br>${escape(row.utm_campaign || "—")}</td><td>${escape(dateLabel(row.create_date))}</td><td>${format(row.kb_count)}</td><td>${format(row.dialog_count)}</td><td>${row.last_login_time ? escape(dateLabel(row.last_login_time)) : "—"}</td><td>${active ? "Active" : "Inactive"}</td><td><button type="button" class="btn-action" data-user-action="status" data-email="${escape(row.email)}" data-active="${active}">${active ? "Deactivate" : "Activate"}</button><button type="button" class="btn-action delete" data-user-action="delete" data-email="${escape(row.email)}">Delete</button></td></tr>`;
          })
          .join("");
      } else
        target.innerHTML = records
          .map(
            (row) =>
              `<tr><td>${escape(row.email)}</td><td>${escape(row.nickname)}</td><td>${escape(dateLabel(row.create_date))}</td><td>${escape(row.referred_by_id || "—")}</td><td>—</td><td>${row.status === "1" ? "Active" : "Inactive"}</td></tr>`,
          )
          .join("");
      if (!records.length)
        target.innerHTML = `<tr><td colspan="${table === "visitors" ? 9 : 6}" style="text-align:center;padding:24px;color:var(--text-muted)">Нет записей с выбранными датами и фильтрами.</td></tr>`;
      const empty = byId(
        table === "users"
          ? "usersEmptyState"
          : table === "leads"
            ? "submissionsEmptyState"
            : "",
      );
      if (empty) empty.style.display = "none";
      const pager = byId("analyticsPager-" + table);
      if (pager) {
        pager.innerHTML = `<span>${result.total} записей · страница ${result.page} из ${Math.max(1, Math.ceil(result.total / result.page_size))}</span><div class="analytics-pager-controls"><button type="button" data-step="-1" ${result.page <= 1 ? "disabled" : ""}>Назад</button><button type="button" data-step="1" ${result.page * result.page_size >= result.total ? "disabled" : ""}>Далее</button></div>`;
        pager.querySelectorAll("[data-step]").forEach((button) =>
          button.addEventListener("click", () => {
            state.pages[table] += Number(button.dataset.step);
            loadRecords(table);
          }),
        );
      }
    } catch (error) {
      if (requestId === state.recordRequests[table])
        target.innerHTML = `<tr><td colspan="9" style="padding:24px;color:var(--text-muted)">${escape(error.message)}</td></tr>`;
    }
  }
  function renderLeadRows() {
    const records =
      typeof databaseSubmissions !== "undefined" ? databaseSubmissions : [];
    byId("submissionsTableBody").innerHTML = records
      .map(
        (row) =>
          `<tr id="row_${escape(row.id)}"><td>${row.read ? "Read" : "New"}</td>${window.SWIPIES_LANDING_NATIVE_AUTH ? `<td>${escape(row.channel || "web")}</td>` : ""}<td>${escape(row.name)}<br><span class="analytics-note">${escape(row.company)}</span></td><td>${escape(row.email)}<br>${escape(row.phone || "—")}</td><td title="${escape(row.message)}" style="max-width:300px;white-space:normal">${escape(row.message)}</td><td>${escape(dateLabel(row.date))}</td><td><button class="btn-action" data-rowid="${escape(row.id)}" data-lead-action="read">${row.read ? "Mark unread" : "Mark read"}</button><button class="btn-action delete" data-rowid="${escape(row.id)}" data-lead-action="delete">Delete</button></td></tr>`,
      )
      .join("");
  }
  function buildUI() {
    const header = document.querySelector(".dashboard-header");
    if (!header) return;
    const oldDate = byId("dateRangeSelect");
    if (oldDate) oldDate.parentElement.style.display = "none";
    const oldSources = byId("sourceSelectorContainer");
    if (oldSources) oldSources.style.display = "none";
    const toolbar = document.createElement("section");
    toolbar.className = "analytics-toolbar";
    toolbar.lang = "ru";
    toolbar.setAttribute("aria-label", "Фильтры аналитики");
    toolbar.innerHTML = `<div class="analytics-controls"><label class="analytics-field">Источник посещений<select id="analyticsSource"><option value="landing">Журнал лендинга</option><option value="ga">Google Analytics 4</option><option value="ym">Яндекс.Метрика</option></select></label><label class="analytics-field">Период<select id="analyticsPreset"><option value="today">Сегодня</option><option value="yesterday">Вчера</option><option value="7">Последние 7 дней</option><option value="30" selected>Последние 30 дней</option><option value="90">Последние 90 дней</option><option value="week">Эта неделя</option><option value="month">Этот месяц</option><option value="custom">Свой период</option></select></label><label class="analytics-field">Начало<input type="datetime-local" step="3600" id="analyticsStart" required></label><label class="analytics-field">Конец, не включительно<input type="datetime-local" step="3600" id="analyticsEnd" required></label><label class="analytics-field">Шаг<select id="analyticsGroup"><option value="hour">Час</option><option value="day" selected>День</option><option value="week">Неделя</option><option value="month">Месяц</option></select></label><label class="analytics-field">Часовой пояс<input id="analyticsTimezone" list="analyticsZones" value="Asia/Tashkent" spellcheck="false"></label><datalist id="analyticsZones"><option value="Asia/Tashkent"><option value="UTC"><option value="Europe/Moscow"><option value="Europe/Berlin"><option value="America/New_York"></datalist></div>
    <div class="analytics-controls"><label class="analytics-field">Сравнение<select id="analyticsCompareMode"><option value="previous">Предыдущий период такой же длительности</option><option value="custom">Выбрать период сравнения</option></select></label><label class="analytics-field" id="analyticsCompareStartField" hidden>Сравнить с<input type="datetime-local" step="3600" id="analyticsCompareStart"></label><label class="analytics-field" id="analyticsCompareEndField" hidden>По, не включительно<input type="datetime-local" step="3600" id="analyticsCompareEnd"></label><label class="analytics-field">UTM source<input id="analyticsUtmSource" maxlength="128" placeholder="Все источники"></label><label class="analytics-field">UTM campaign<input id="analyticsUtmCampaign" maxlength="128" placeholder="Все кампании"></label><div class="analytics-actions"><button class="primary" id="analyticsApply" type="button">Применить</button><button id="analyticsExport" type="button">Скачать Excel</button><button id="analyticsExportCsv" type="button">CSV</button></div></div><p class="analytics-status" id="analyticsStatus" role="status" aria-live="polite"></p><div class="analytics-periods"><span><i class="analytics-current-dot"></i>Сейчас: <strong id="analyticsCurrentRange">—</strong></span><span><i class="analytics-previous-dot"></i>Было: <strong id="analyticsPreviousRange">—</strong></span><span id="analyticsZoneLabel">Asia/Tashkent</span></div>`;
    header.after(toolbar);
    // Hide toolbar initially if visitors tab is the active/default tab
    const _initialTab = (function() {
      const active = document.querySelector('[data-tab].active, [data-tab][aria-selected="true"]');
      if (active) return active.dataset.tab;
      const visible = document.querySelector('.dashboard-section:not([style*="display: none"]):not([style*="display:none"])');
      return visible ? visible.id.replace('Tab', '') : 'overview';
    })();
    toolbar.hidden = _initialTab === 'visitors' || _initialTab === 'settings' || _initialTab === 'plans';
    byId("overviewTab").innerHTML =
      `<div class="analytics-panel" lang="ru"><div class="analytics-intro"><div><h2>Как изменились показатели</h2><p class="analytics-note">Сравнение фактических периодов. У каждой метрики — текущее значение, предыдущее и изменение. Пустые данные отмечаются прочерком.</p></div></div><div class="analytics-metrics" id="analyticsMetrics" aria-live="polite"><div class="analytics-metric"><div class="analytics-metric-label">Загружаем метрики</div><div class="analytics-skeleton"></div><p class="analytics-note">Сравниваем два периода</p></div></div><section class="analytics-card"><div class="analytics-card-header"><h3 id="analyticsChartSubtitle">Динамика за два периода</h3><label class="analytics-field">Показатель<select id="analyticsMetricSelect"><option value="visitors">Посетители</option></select></label></div><div class="analytics-legend"><span><i class="analytics-current-dot"></i>Текущий период</span><span><i class="analytics-previous-dot"></i>Период сравнения</span></div><div id="analyticsChart"><div class="analytics-chart-empty">Загрузите отчёт для выбранного периода.</div></div><p class="analytics-caption">Ось X сопоставляет группы по порядку. При разной длительности периодов некоторые группы не имеют пары; пропуски не подменяются нулями.</p></section><section class="analytics-card"><div class="analytics-card-header"><h3>Значения по временным группам</h3></div><div class="analytics-table-wrap"><table class="analytics-table"><thead><tr><th>Текущий период</th><th>Период сравнения</th><th>Сейчас</th><th>Было</th><th>Разница</th></tr></thead><tbody id="analyticsDetailBody"></tbody></table></div><div class="analytics-pager"><span id="analyticsDetailPage">—</span><div class="analytics-pager-controls"><button id="analyticsDetailPrev" type="button">Назад</button><button id="analyticsDetailNext" type="button">Далее</button></div></div></section><div class="analytics-breakdowns"><section class="analytics-card" id="analyticsChannels"></section><section class="analytics-card" id="analyticsDevices"></section></div><details class="analytics-details"><summary>Источники и правила расчёта</summary><div class="analytics-note" id="analyticsNotes"></div></details></div>`;
    preset("30");
    const extra = document.createElement("details");
    extra.className = "analytics-details";
    extra.innerHTML =
      '<summary>Все метрики: платежи, просмотры, цели и вовлечённость</summary><div class="analytics-metrics" id="analyticsExtraMetrics" style="margin-top:12px"></div>';
    byId("analyticsMetrics").after(extra);
    byId("analyticsApply").addEventListener("click", refresh);
    byId("analyticsExport").addEventListener("click", () => download());
    byId("analyticsExportCsv").addEventListener("click", () =>
      download("report", "csv"),
    );
    byId("analyticsPreset").addEventListener("change", (event) => {
      if (event.target.value !== "custom") {
        preset(event.target.value);
        refresh();
      }
    });
    for (const id of ["analyticsStart", "analyticsEnd"])
      byId(id).addEventListener(
        "change",
        () => (byId("analyticsPreset").value = "custom"),
      );
    byId("analyticsCompareMode").addEventListener("change", (event) => {
      const custom = event.target.value === "custom";
      byId("analyticsCompareStartField").hidden = !custom;
      byId("analyticsCompareEndField").hidden = !custom;
      if (custom && !byId("analyticsCompareStart").value) {
        const end = new Date(instant(byId("analyticsStart").value));
        const start = new Date(
          end - (new Date(instant(byId("analyticsEnd").value)) - end),
        );
        byId("analyticsCompareStart").value = wall(start);
        byId("analyticsCompareEnd").value = wall(end);
      }
    });
    byId("analyticsSource").addEventListener("change", (event) => {
      state.source = event.target.value;
      refresh();
    });
    byId("analyticsMetricSelect").addEventListener("change", () => {
      state.tablePage = 1;
      renderChart();
    });
    byId("analyticsDetailPrev").addEventListener("click", () => {
      state.tablePage--;
      renderDetail();
    });
    byId("analyticsDetailNext").addEventListener("click", () => {
      state.tablePage++;
      renderDetail();
    });
    // recordControls("visitors", "visitorsTab"); // Visitors tab uses its own original UI
    recordControls("leads", "submissionsTab");
    recordControls("users", "usersTab");
    byId("usersTableBody").addEventListener("click", (event) => {
      const button = event.target.closest("[data-user-action]");
      if (!button) return;
      if (button.dataset.userAction === "status")
        window.toggleUserStatus(
          button.dataset.email,
          button.dataset.active === "true",
        );
      else window.deleteUser(button.dataset.email);
    });
    recordControls("campaigns", "utmTab");
    toolbar.addEventListener("input", () => {
      if (state.report && !state.busy)
        status(
          "Фильтры изменены. Нажмите «Применить», чтобы обновить отчёт и таблицы.",
        );
    });
    const switchOriginal = window.switchTab;
    const refreshOriginal = window.refreshDashboardData;
    const setDataSourceOriginal = window.setDataSource;
    window.switchTab = function (tab) {
      switchOriginal(tab);
      const isVisitors = tab === "visitors";
      if (oldDate && oldDate.parentElement) {
        oldDate.parentElement.style.display = isVisitors ? "" : "none";
      }
      if (oldSources) {
        oldSources.style.display = isVisitors ? "flex" : "none";
      }
      toolbar.hidden =
        tab === "settings" || tab === "plans" || tab === "visitors";
      if (tab === "submissions") loadRecords("leads");
    };
    window.refreshDashboardData = function () {
      if (typeof refreshOriginal === "function") {
        Promise.resolve(refreshOriginal()).catch(() => {});
      }
      if (typeof activeTab === "string" && activeTab === "visitors") {
        return;
      }
      return refresh();
    };
    // window.loadVisitorsFromDB preserved (original admin.html implementation handles visitors tab)
    window.loadLeadsFromDB = () => loadRecords("leads");
    window.loadUsersFromDB = () => loadRecords("users");
    // window.updateActiveUsers preserved (original admin.html handles active users)
    window.loadUtmPageData = () => {
      renderCampaigns();
      return loadRecords("campaigns");
    };
    // window.exportVisitorsToCSV preserved (original admin.html implementation)
    window.exportSubmissionsToCSV = () => download("leads", "csv");
    window.renderSubmissionsTable = renderLeadRows;
    byId("submissionsTableBody").addEventListener("click", (event) => {
      const button = event.target.closest("[data-lead-action]");
      if (!button) return;
      const row = databaseSubmissions.find(
        (item) => String(item.id) === button.dataset.rowid,
      );
      if (!row) return;
      if (button.dataset.leadAction === "read") window.toggleReadStatus(row.id);
      else window.deleteSubmission(row.id);
    });
    window.setDataSource = (source) => {
      if (
        typeof activeTab === "string" &&
        activeTab === "visitors" &&
        typeof setDataSourceOriginal === "function"
      ) {
        return setDataSourceOriginal(source);
      }
      state.source = source;
      if (byId("analyticsSource")) byId("analyticsSource").value = source;
      refresh();
    };
    if (!window.SWIPIES_LANDING_NATIVE_AUTH) {
      const otp = document.createElement("div");
      otp.className = "form-group";
      otp.hidden = true;
      otp.innerHTML =
        '<label for="analyticsLoginCode">Код из письма</label><div class="input-container"><input id="analyticsLoginCode" type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" pattern="[0-9]{6}"></div>';
      byId("password").closest(".form-group").after(otp);
      const restart = document.createElement("button");
      restart.type = "button";
      restart.className = "btn-secondary-dashboard";
      restart.textContent = "Войти с другим email / начать заново";
      otp.appendChild(restart);
      restart.addEventListener("click", () => {
        state.loginEmail = null;
        otp.hidden = true;
        byId("analyticsLoginCode").required = false;
        byId("analyticsLoginCode").value = "";
        byId("username").readOnly = false;
        byId("password").required = true;
        byId("password").closest(".form-group").hidden = false;
        byId("username").focus();
      });
      window.handleLogin = async (event) => {
        event.preventDefault();
        const error = byId("loginError");
        try {
          error.style.display = "none";
          let result;
          if (state.loginEmail) {
            result = await jsonPost("verify", {
              email: state.loginEmail,
              code: byId("analyticsLoginCode").value.trim(),
            });
          } else {
            const encrypted = window.rsaPsw(byId("password").value);
            if (!encrypted)
              throw new Error(
                "Не удалось подготовить пароль для входа. Проверьте загрузку модуля шифрования.",
              );
            result = await jsonPost("login", {
              email: byId("username").value.trim(),
              password: encrypted,
            });
          }
          if (result.data.requires_2fa) {
            state.loginEmail = result.data.email;
            otp.hidden = false;
            byId("password").closest(".form-group").hidden = true;
            byId("analyticsLoginCode").required = true;
            byId("password").value = "";
            byId("password").required = false;
            byId("username").readOnly = true;
            byId("analyticsLoginCode").focus();
            return;
          }
          localStorage.setItem("Authorization", result.data.authorization);
          localStorage.setItem("swipies_admin_session", "authenticated");
          byId("password").value = "";
          byId("analyticsLoginCode").value = "";
          state.loginEmail = null;
          otp.hidden = true;
          byId("analyticsLoginCode").required = false;
          byId("password").required = true;
          byId("password").closest(".form-group").hidden = false;
          byId("username").readOnly = false;
          window.checkAuth();
        } catch (problem) {
          error.textContent = problem.message;
          error.style.display = "block";
        }
      };
    }
    const logoutOriginal = window.handleLogout;
    window.handleLogout = () => {
      state.controller?.abort();
      state.report = null;
      state.signature = "";
      localStorage.removeItem("Authorization");
      logoutOriginal();
    };
    window.SwipiesAdminReporting = {
      refresh,
      download,
      filters,
      state,
      wall,
      instant,
      format,
    };
  }
  // The legacy DOMContentLoaded listener calls initializeDashboard; install
  // overrides before it runs, then let existing auth decide whether to load.
  buildUI();
})();
