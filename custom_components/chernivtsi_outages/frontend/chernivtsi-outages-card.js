// Chernivtsi Power Outages: today's and tomorrow's schedule of one outage group.
// Reads only the Schedule sensor's `today` / `tomorrow` attributes.

const TEXT = {
  en: {
    group: (n) => `Group ${n}`,
    today: "Today",
    tomorrow: "Tomorrow",
    notPublished: "Not published yet",
    unknown: "Today's schedule is not published yet",
    noOutages: "No outages scheduled",
    nextOutage: (from, to) => (to ? `Next outage ${from} to ${to}` : `Next outage from ${from}`),
    powerBack: (at, maybe) => (maybe ? `Power possibly back at ${at}` : `Power back at ${at}`),
    noNext: "No more outages scheduled",
    degraded: "From the Telegram channel: possible outages are shown as outages",
    on: "Power on",
    off: "Outage",
    maybe: "Possible outage",
    entity: "Schedule sensor",
    missing: "Entity not found",
  },
  uk: {
    group: (n) => `Група ${n}`,
    today: "Сьогодні",
    tomorrow: "Завтра",
    notPublished: "Ще не опубліковано",
    unknown: "Графік на сьогодні ще не опубліковано",
    noOutages: "Відключень не заплановано",
    nextOutage: (from, to) => (to ? `Наступне відключення з ${from} до ${to}` : `Наступне відключення з ${from}`),
    powerBack: (at, maybe) => (maybe ? `Світло, можливо, повернеться о ${at}` : `Світло повернеться о ${at}`),
    noNext: "Більше відключень не заплановано",
    degraded: "За даними Telegram-каналу: можливі відключення показано як відключення",
    on: "Є світло",
    off: "Відключення",
    maybe: "Можливе відключення",
    entity: "Сенсор графіка",
    missing: "Сутність не знайдено",
  },
};

const KYIV = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/Kyiv",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

const STYLE = `
  :host { --co-on: var(--success-color, #43a047); --co-off: var(--error-color, #db4437); --co-maybe: var(--disabled-color, #9e9e9e); }
  .body { padding: 16px; display: flex; flex-direction: column; gap: 10px; }
  .head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .name { font-size: 1.1em; font-weight: 500; color: var(--primary-text-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .state { flex: none; padding: 2px 10px; border-radius: 12px; font-size: 0.9em; font-weight: 500; color: var(--primary-text-color); background: var(--secondary-background-color); border: 1px solid var(--divider-color); }
  .state.on { border-color: var(--co-on); }
  .state.off { border-color: var(--co-off); }
  .state.maybe { border-style: dashed; border-color: var(--co-maybe); }
  .summary { color: var(--secondary-text-color); }
  .day { display: flex; flex-direction: column; gap: 4px; }
  .label { font-size: 0.85em; color: var(--secondary-text-color); }
  .bar { position: relative; display: flex; gap: 1px; height: 22px; }
  .cell { flex: 1 1 0; min-width: 0; border-radius: 2px; box-sizing: border-box; }
  .cell.on { background: var(--co-on); }
  .cell.off { background: repeating-linear-gradient(135deg, var(--co-off) 0 3px, color-mix(in srgb, var(--co-off) 55%, transparent) 3px 5px); }
  .cell.maybe { background: color-mix(in srgb, var(--co-maybe) 70%, transparent); border: 1px dashed var(--secondary-text-color); }
  .cell.none { background: var(--divider-color); }
  .cell.past { opacity: 0.4; }
  .now { position: absolute; top: -3px; bottom: -3px; width: 2px; margin-left: -1px; background: var(--primary-text-color); border-radius: 1px; }
  .ticks { position: relative; height: 1.2em; font-size: 0.75em; color: var(--secondary-text-color); }
  .ticks span { position: absolute; transform: translateX(-50%); white-space: nowrap; }
  .ticks span:first-child { transform: none; }
  .ticks span:last-child { transform: translateX(-100%); }
  .legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 0.85em; color: var(--secondary-text-color); }
  .legend span { display: inline-flex; align-items: center; gap: 6px; }
  .legend .cell { display: inline-block; width: 14px; height: 14px; flex: none; }
  .muted { color: var(--secondary-text-color); font-size: 0.9em; }
  .note { font-style: italic; }
  .warning { color: var(--error-color); }
`;

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key === "style") Object.assign(node.style, value);
    else node.setAttribute(key, value);
  }
  for (const child of children) if (child) node.append(child);
  return node;
}

function text(hass) {
  const lang = (hass?.locale?.language || hass?.language || "en").slice(0, 2);
  return TEXT[lang] || TEXT.en;
}

function minutes(hhmm) {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

function hhmm(total) {
  const m = ((total % 1440) + 1440) % 1440;
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
}

function uses12h(hass) {
  const format = hass?.locale?.time_format;
  if (format === "12") return true;
  if (format === "24") return false;
  const lang = format === "system" ? undefined : hass?.locale?.language;
  return new Intl.DateTimeFormat(lang, { hour: "numeric" }).resolvedOptions().hour12 === true;
}

function formatTime(hass, value) {
  const [h, m] = (value === "24:00" ? "00:00" : value).split(":").map(Number);
  if (!uses12h(hass)) return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
  return `${h % 12 || 12}:${String(m).padStart(2, "0")} ${h < 12 ? "AM" : "PM"}`;
}

function formatHour(hass, hour) {
  if (!uses12h(hass)) return `${String(hour % 24).padStart(2, "0")}:00`;
  const h = hour % 24;
  return `${h % 12 || 12} ${h < 12 ? "AM" : "PM"}`;
}

function slots(periods) {
  const cells = new Array(48).fill(null);
  for (const p of periods || []) {
    for (let i = minutes(p.start) / 30; i < minutes(p.end) / 30; i++) cells[i] = p.state;
  }
  return cells;
}

function isSchedule(state) {
  return state && Array.isArray(state.attributes.today) && "schedule_active" in state.attributes;
}

class ChernivtsiOutagesCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("chernivtsi-outages-card-editor");
  }

  static getStubConfig(hass) {
    const entity = Object.keys(hass.states).find((id) => id.startsWith("sensor.") && isSchedule(hass.states[id]));
    return { entity: entity || "" };
  }

  setConfig(config) {
    if (!config || typeof config.entity !== "string" || !config.entity.startsWith("sensor.")) {
      throw new Error("Set `entity` to the Schedule sensor of an outage group");
    }
    this._config = config;
    this._key = null;
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const state = hass.states[this._config?.entity];
    // Redraw when the sensor or the locale changes, and once a minute for the now marker.
    const key = [state?.last_updated, Math.floor(Date.now() / 60000), hass.locale?.language, hass.locale?.time_format].join("|");
    if (key === this._key) return;
    this._key = key;
    this._render();
  }

  getCardSize() {
    return 4;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: 4, min_rows: 3 };
  }

  _row(label, periods, now, t) {
    if (!Array.isArray(periods)) return null;
    const current = now === null ? -1 : Math.floor(now / 30);
    const bar = el("div", { class: "bar", role: "img", "aria-label": label });
    slots(periods).forEach((state, i) => {
      bar.append(
        el("span", {
          class: `cell ${state || "none"}${i < current ? " past" : ""}`,
          title: `${formatTime(this._hass, hhmm(i * 30))} ${state ? t[state] : ""}`,
        })
      );
    });
    if (now !== null) bar.append(el("span", { class: "now", style: { left: `${(now / 1440) * 100}%` } }));
    return el("div", { class: "day" }, [el("div", { class: "label", text: label }), bar]);
  }

  _missingRow(label, message) {
    return el("div", { class: "day" }, [el("div", { class: "label", text: label }), el("div", { class: "muted", text: message })]);
  }

  _summary(a, now, t) {
    if (!Array.isArray(a.today)) return t.unknown;
    if (a.schedule_active === false && !(a.tomorrow || []).some((p) => p.state === "off")) return t.noOutages;
    const merged = [];
    [a.today, a.tomorrow || []].forEach((periods, d) =>
      periods.forEach((p) => {
        const s = d * 1440 + minutes(p.start);
        const e = d * 1440 + minutes(p.end);
        const last = merged[merged.length - 1];
        if (last && last.state === p.state && last.e === s) last.e = e;
        else merged.push({ state: p.state, s, e });
      })
    );
    const at = (m) => formatTime(this._hass, hhmm(m));
    const inside = merged.find((p) => p.s <= now && now < p.e);
    if (inside?.state === "off") {
      const after = merged.find((p) => p.s === inside.e);
      return after ? t.powerBack(at(inside.e), after.state === "maybe") : t.off;
    }
    const next = merged.find((p) => p.state === "off" && p.s > now);
    if (!next) return t.noNext;
    const ends = merged.some((p) => p.s === next.e);
    return t.nextOutage(at(next.s), ends ? at(next.e) : null);
  }

  _render() {
    if (!this._config || !this._hass) return;
    const t = text(this._hass);
    const state = this._hass.states[this._config.entity];
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const body = el("div", { class: "body" });
    if (!state) {
      body.append(el("div", { class: "warning", text: `${t.missing}: ${this._config.entity}` }));
    } else {
      const a = state.attributes;
      const now = minutes(KYIV.format(new Date()));
      const current = this._hass.formatEntityState ? this._hass.formatEntityState(state) : state.state;
      const ticks = el(
        "div",
        { class: "ticks" },
        [0, 6, 12, 18, 24].map((h) => el("span", { text: formatHour(this._hass, h), style: { left: `${(h / 24) * 100}%` } }))
      );
      const legend = el(
        "div",
        { class: "legend" },
        ["on", "off", "maybe"].map((s) => el("span", {}, [el("i", { class: `cell ${s}` }), document.createTextNode(t[s])]))
      );
      body.append(
        el("div", { class: "head" }, [
          el("div", { class: "name", text: this._config.title || (a.group ? t.group(a.group) : a.friendly_name) }),
          el("div", { class: `state ${state.state}`, text: current }),
        ]),
        el("div", { class: "summary", text: this._summary(a, now, t) }),
        this._row(t.today, a.today, now, t) || this._missingRow(t.today, t.unknown),
        this._row(t.tomorrow, a.tomorrow, null, t) || this._missingRow(t.tomorrow, t.notPublished),
        ticks,
        legend,
        ...(a.degraded ? [el("div", { class: "muted note", text: t.degraded })] : [])
      );
    }
    this.shadowRoot.replaceChildren(el("style", { text: STYLE }), el("ha-card", {}, [body]));
  }
}

class ChernivtsiOutagesCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    const t = text(this._hass);
    const select = el("select", {
      style: {
        padding: "8px",
        font: "inherit",
        color: "var(--primary-text-color)",
        background: "var(--card-background-color)",
        border: "1px solid var(--divider-color)",
        borderRadius: "4px",
      },
    });
    for (const id of Object.keys(this._hass.states).filter((e) => e.startsWith("sensor.") && isSchedule(this._hass.states[e]))) {
      const option = el("option", { value: id, text: this._hass.states[id].attributes.friendly_name || id });
      option.selected = id === this._config.entity;
      select.append(option);
    }
    select.addEventListener("change", (ev) => {
      this._config = { ...this._config, entity: ev.target.value };
      this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
    });
    const label = el("label", { style: { display: "flex", flexDirection: "column", gap: "4px", color: "var(--primary-text-color)" } }, [
      document.createTextNode(t.entity),
      select,
    ]);
    this.replaceChildren(label);
  }
}

if (!customElements.get("chernivtsi-outages-card")) {
  customElements.define("chernivtsi-outages-card", ChernivtsiOutagesCard);
  customElements.define("chernivtsi-outages-card-editor", ChernivtsiOutagesCardEditor);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "chernivtsi-outages-card",
    name: "Chernivtsi Power Outages",
    description: "Today's and tomorrow's outage schedule of one group",
    preview: true,
  });
}
