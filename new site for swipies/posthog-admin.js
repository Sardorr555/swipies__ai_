(() => {
  "use strict";
  const $ = (id) => document.getElementById(id),
    escape = (value) =>
      String(value ?? "").replace(
        /[&<>"']/g,
        (char) =>
          ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;",
          })[char],
      );
  const labels = {
    visitors: "Посетители (browser ID)",
    sessions: "Сессии SDK",
    pageviews: "Просмотры лендинга",
    registrations: "Созданные аккаунты",
    payments: "Подтверждённые оплаты",
    registration_conversion: "Регистрация / посетители",
    payment_conversion: "Оплата / посетители",
  };
  const number = (value) =>
    value == null || !Number.isFinite(Number(value))
      ? "—"
      : new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(
          value,
        );
  let report = null,
    controller = null,
    sequence = 0;
  const status = (text, error = false) => {
    $("phStatus").textContent = text;
    $("phStatus").classList.toggle("ph-error", error);
  };
  const token = () => localStorage.getItem("swipies_admin_token") || "";
  function wall(value, zone = $("phZone").value) {
    return new Intl.DateTimeFormat("sv-SE", {
      timeZone: zone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    })
      .format(value)
      .replace(" ", "T");
  }
  function instant(value) {
    if (!/^\d{4}-\d\d-\d\dT\d\d:00$/.test(value))
      throw new Error("Выберите границы по целым часам.");
    const intended = Date.parse(value + "Z");
    let actual = intended;
    for (let i = 0; i < 4; i++)
      actual += intended - Date.parse(wall(new Date(actual)) + "Z");
    if (wall(new Date(actual)) !== value)
      throw new Error("Выбранный час отсутствует при смене времени.");
    return new Date(actual).toISOString();
  }
  function preset() {
    const name = $("phPreset").value;
    if (name === "custom") return;
    const local = wall(new Date());
    const end = new Date(local.slice(0, 14) + "00:00Z"),
      start = new Date(end);
    if (name === "today") start.setUTCHours(0, 0, 0, 0);
    else start.setUTCDate(start.getUTCDate() - Number(name));
    $("phStart").value = start.toISOString().slice(0, 16);
    $("phEnd").value = end.toISOString().slice(0, 16);
  }
  function filters() {
    const start = instant($("phStart").value),
      end = instant($("phEnd").value);
    if (start >= end)
      throw new Error(
        "Конец должен быть позже начала. Если день только начался, выберите предыдущий период.",
      );
    return {
      start,
      end,
      timezone: $("phZone").value.trim(),
      group: new Date(end) - new Date(start) <= 48 * 3600000 ? "hour" : "day",
      comparison: "previous",
    };
  }
  async function api(path, payload, signal) {
    const response = await fetch("/api/admin/posthog/" + path, {
      method: payload ? "POST" : "GET",
      headers: {
        Authorization: "Bearer " + token(),
        ...(payload ? { "Content-Type": "application/json" } : {}),
      },
      body: payload ? JSON.stringify(payload) : undefined,
      cache: "no-store",
      signal,
    });
    if ([401, 403].includes(response.status))
      throw new Error("Сессия завершена. Войдите в существующую админку.");
    const data = await response.json();
    if (!response.ok || data.code !== 0)
      throw new Error(data.message || "Отчёт временно недоступен.");
    return data.data;
  }
  function table(target, headers, rows) {
    $(target).innerHTML =
      "<table><thead><tr>" +
      headers.map((value) => "<th>" + escape(value) + "</th>").join("") +
      "</tr></thead><tbody>" +
      (rows
        .map(
          (row) =>
            "<tr>" +
            row
              .map((value) => "<td>" + escape(value ?? "—") + "</td>")
              .join("") +
            "</tr>",
        )
        .join("") ||
        '<tr><td colspan="' + headers.length + '">Нет данных.</td></tr>') +
      "</tbody></table>";
  }
  function setup(data) {
    $("phSetup").hidden = false;
    $("phReport").hidden = true;
    $("phSetupMessage").textContent =
      data.error ||
      "PostHog отключён или ключи ещё не настроены. Существующая аналитика работает независимо.";
    $("phSetupSteps").innerHTML = (data.setup || [])
      .map((text) => "<li>" + escape(text) + "</li>")
      .join("");
    $("phSetupVars").innerHTML = (data.required_environment || [])
      .map((text) => "<li><code>" + escape(text) + "</code></li>")
      .join("");
  }
  function pairs(rows, columns) {
    const result = new Map();
    for (const row of rows) {
      if (!["current", "previous"].includes(row[0])) continue;
      const keys = row.slice(1, 1 + columns),
        id = JSON.stringify(keys);
      if (!result.has(id)) result.set(id, { keys });
      result.get(id)[row[0]] = row.slice(1 + columns);
    }
    return [...result.values()];
  }
  function render(data) {
    report = data;
    $("phSetup").hidden = true;
    $("phReport").hidden = false;
    $("phEmpty").hidden = !data.empty;
    const dates = data.filters;
    $("phPeriods").textContent =
      `Сейчас: ${wall(new Date(dates.start), dates.timezone)} → ${wall(new Date(dates.end), dates.timezone)}; было: ${wall(new Date(dates.compare_start), dates.timezone)} → ${wall(new Date(dates.compare_end), dates.timezone)}. Часовой пояс: ${dates.timezone}. Последнее обновление: ${wall(new Date(data.updated_at), dates.timezone)}.`;
    $("phMetrics").innerHTML = data.metrics
      .map((item) => {
        const rate = item.key.endsWith("conversion"),
          delta = item.change;
        const change =
          delta.absolute == null
            ? "Нет данных для сравнения"
            : rate
              ? number(delta.absolute) + " п.п."
              : delta.state === "new"
                ? "Ранее 0; изменение " + number(delta.absolute)
                : number(delta.percent) + "% · " + number(delta.absolute);
        return (
          '<article class="ph-metric"><div class="ph-label">' +
          escape(labels[item.key]) +
          '</div><div class="ph-value">' +
          number(item.current) +
          (rate && item.current != null ? "%" : "") +
          '</div><div class="ph-before">Было: ' +
          number(item.previous) +
          (rate && item.previous != null ? "%" : "") +
          '</div><div class="ph-delta">' +
          escape(change) +
          "</div></article>"
        );
      })
      .join("");
    $("phFunnel").innerHTML = data.funnel.current
      .map((row, i) => {
        const before = data.funnel.previous[i];
        const width = data.funnel.current[0].visitors
          ? (row.visitors / data.funnel.current[0].visitors) * 100
          : 0;
        return (
          '<div class="ph-step"><div class="ph-step-heading"><strong>' +
          escape(row.stage) +
          "</strong><span>" +
          number(row.visitors) +
          " browser ID · было " +
          number(before.visitors) +
          '</span></div><div class="ph-step-track"><div class="ph-step-bar" style="width:' +
          Math.max(0, Math.min(100, width)) +
          '%"></div></div><div class="ph-muted">' +
          (i
            ? "Потеря: " +
              number(row.lost) +
              "; переход от предыдущего этапа: " +
              number(row.from_previous_percent) +
              (row.from_previous_percent != null ? "%" : "")
            : "Знаменатель конверсии — " +
              number(row.visitors) +
              " посетителей лендинга") +
          "</div></div>"
        );
      })
      .join("");
    table(
      "phCtas",
      [
        "CTA",
        "Посетители сейчас",
        "Клики сейчас",
        "Посетители было",
        "Клики было",
      ],
      pairs(data.ctas, 1).map((row) => [
        row.keys[0],
        number(row.current?.[0]),
        number(row.current?.[1]),
        number(row.previous?.[0]),
        number(row.previous?.[1]),
      ]),
    );
    table(
      "phSources",
      [
        "Источник",
        "UTM-кампания",
        "Посетители сейчас",
        "Просмотры сейчас",
        "Посетители было",
      ],
      pairs(data.acquisition, 2).map((row) => [
        row.keys[0] || "Не указан",
        row.keys[1] || "Не указана",
        number(row.current?.[0]),
        number(row.current?.[1]),
        number(row.previous?.[0]),
      ]),
    );
    table(
      "phDevices",
      ["Устройство", "Посетители сейчас", "Посетители было"],
      pairs(data.devices, 1).map((row) => [
        row.keys[0] || "Не указано",
        number(row.current?.[0]),
        number(row.previous?.[0]),
      ]),
    );
    const rows = [];
    for (const period of ["current", "previous"]) {
      const comparison = data.comparison[period];
      if (comparison.unavailable) {
        rows.push([
          period === "current" ? "Текущий период" : "Предыдущий период",
          "—",
          "—",
          "—",
          comparison.unavailable,
        ]);
        continue;
      }
      for (const key of ["registrations", "payments"]) {
        const item = comparison[key];
        rows.push([
          (period === "current" ? "Сейчас: " : "Было: ") + labels[key],
          number(item.posthog),
          number(item.system),
          number(item.difference),
          item.unavailable || item.definition,
        ]);
      }
    }
    table(
      "phComparison",
      [
        "Метрика / период",
        "PostHog",
        "Система",
        "Разница",
        "Правило сравнения",
      ],
      rows,
    );
    $("phComparisonNotes").innerHTML = data.comparison_notes
      .map((value) => "<li>" + escape(value) + "</li>")
      .join("");
    $("phDefinitions").innerHTML = Object.entries(data.definitions)
      .map(
        ([key, value]) =>
          "<dt>" +
          escape(
            labels[key] ||
              { funnel: "Воронка", payment_time: "Время оплаты" }[key] ||
              key,
          ) +
          "</dt><dd>" +
          escape(value) +
          "</dd>",
      )
      .join("");
    chart();
    status(
      data.stale
        ? "PostHog недоступен. Показан сохранённый отчёт от " +
            wall(new Date(data.updated_at), dates.timezone) +
            ". " +
            (data.warning || "")
        : data.cached
          ? "Показан кэшированный отчёт. " + data.breakdowns_limit
          : "Отчёт обновлён. " + data.breakdowns_limit,
      !!data.stale,
    );
  }
  function chart() {
    if (!report) return;
    const key = $("phChartMetric").value,
      index = { visitors: 2, pageviews: 3, registrations: 4, payments: 5 }[key];
    const current = report.timeline.filter((row) => row[0] === "current"),
      previous = report.timeline.filter((row) => row[0] === "previous");
    const all = [...current, ...previous]
      .map((row) => Number(row[index]))
      .filter(Number.isFinite);
    if (!all.length) {
      $("phChart").textContent = "Нет временного ряда.";
      table(
        "phTimeline",
        ["Текущая группа", "Сейчас", "Предыдущая группа", "Было"],
        [],
      );
      return;
    }
    const max = Math.max(...all, 1),
      count = Math.max(current.length, previous.length),
      x = (i) => 55 + (i * 900) / Math.max(1, count - 1),
      y = (value) => 225 - (Number(value) / max) * 200;
    const path = (rows, color, dash) =>
      '<path fill="none" stroke="' +
      color +
      '" stroke-width="2" ' +
      (dash ? 'stroke-dasharray="6 5"' : "") +
      ' d="' +
      rows
        .map((row, i) => (i ? "L" : "M") + x(i) + " " + y(row[index]))
        .join(" ") +
      '"/>' +
      (rows.length === 1
        ? '<circle cx="' +
          x(0) +
          '" cy="' +
          y(rows[0][index]) +
          '" r="4" fill="' +
          color +
          '"/>'
        : "");
    $("phChart").innerHTML =
      '<svg viewBox="0 0 1000 260" role="img" aria-label="' +
      escape(labels[key]) +
      ': текущий и предыдущий период; точные значения ниже"><text x="0" y="20">' +
      number(max) +
      '</text><text x="25" y="229">0</text>' +
      path(previous, "#97a0af", true) +
      path(current, "#e8a820", false) +
      "</svg>";
    table(
      "phTimeline",
      ["Текущая группа", "Сейчас", "Предыдущая группа", "Было"],
      Array.from({ length: count }, (_, i) => [
        current[i]?.[1],
        number(current[i]?.[index]),
        previous[i]?.[1],
        number(previous[i]?.[index]),
      ]),
    );
  }
  async function refresh(event) {
    event?.preventDefault();
    const id = ++sequence;
    controller?.abort();
    controller = new AbortController();
    $("phRefresh").disabled = true;
    status("Загрузка PostHog…");
    try {
      if (!token()) throw new Error("Войдите в существующую админку.");
      const settings = await api("status");
      if (!settings.reports_ready) {
        setup(settings);
        status(settings.error || "Настройте подключение PostHog.");
        return;
      }
      const info = settings.collector;
      $("phCollector").textContent = info
        ? info.error ||
          `Сборщик: отправлено ${info.sent}, ожидает ${info.pending}, отменено после отзыва согласия ${info.cancelled}. Начало сбора: ${wall(new Date(info.tracking_started_at * 1000))}.`
        : "Сборщик не запущен: события подтверждённых конверсий пока недоступны.";
      const data = await api(
        "report",
        { filters: filters() },
        controller.signal,
      );
      if (id === sequence) {
        if (data.state === "setup") setup(data);
        else render(data);
      }
    } catch (error) {
      if (error.name !== "AbortError")
        status(
          error.message +
            (report ? " На экране предыдущий успешный отчёт." : ""),
          true,
        );
    } finally {
      if (id === sequence) $("phRefresh").disabled = false;
    }
  }
  $("phFilters").addEventListener("submit", refresh);
  $("phPreset").addEventListener("change", () => {
    preset();
    if ($("phPreset").value !== "custom") refresh();
  });
  for (const id of ["phStart", "phEnd"])
    $(id).addEventListener("change", () => {
      $("phPreset").value = "custom";
      status("Даты изменены. Нажмите «Обновить».");
    });
  $("phChartMetric").addEventListener("change", chart);
  preset();
  refresh();
})();
