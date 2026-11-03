// Chernivtsi Power Outages: today's and tomorrow's schedule of one outage group.
// Reads the Schedule now sensor's `today` / `tomorrow` attributes, and the time of
// the last change from the Schedule changed at sensor of the same group.

const TEXT = {
  en: {
    title: (n) => `Outage group ${n}`,
    today: "Today",
    tomorrow: "Tomorrow",
    notPublished: "Not published yet",
    unknown: "Today's schedule is not published yet",
    noOutages: "No outages scheduled",
    nextOutage: (from, to) => (to ? `Next outage ${from} to ${to}` : `Next outage from ${from}`),
    powerBack: (at, maybe) => (maybe ? `Power possibly back at ${at}` : `Power expected back at ${at}`),
    noNext: "No more outages scheduled",
    degraded: "From the Telegram channel: possible outages are shown as outages",
    on: "Power on",
    off: "Outage",
    maybe: "Possible outage",
    entity: "Schedule now sensor",
    missing: "Entity not found",
    hours: (h) => `${h} h`,
    changed: (when, at) => ({ today: `Changed ${at}`, yesterday: `Changed yesterday ${at}` })[when] || `Changed ${when} ${at}`,
  },
  uk: {
    title: (n) => `Група відключень ${n}`,
    today: "Сьогодні",
    tomorrow: "Завтра",
    notPublished: "Ще не опубліковано",
    unknown: "Графік на сьогодні ще не опубліковано",
    noOutages: "Відключень не заплановано",
    nextOutage: (from, to) => (to ? `Наступне відключення з ${from} до ${to}` : `Наступне відключення з ${from}`),
    powerBack: (at, maybe) => (maybe ? `Світло, можливо, повернеться о ${at}` : `Світло очікується о ${at}`),
    noNext: "Більше відключень не заплановано",
    degraded: "За даними Telegram-каналу: можливі відключення показано як відключення",
    on: "Є світло",
    off: "Відключення",
    maybe: "Можливе відключення",
    entity: "Сенсор «Графік зараз»",
    missing: "Сутність не знайдено",
    hours: (h) => `${h} год`,
    changed: (when, at) => ({ today: `Змінено о ${at}`, yesterday: `Змінено вчора о ${at}` })[when] || `Змінено ${when} о ${at}`,
  },
};

// Material Design Icons, the set Home Assistant uses: flash, flash-off, flash-alert.
const ICONS = {
  on: "M7,2V13H10V22L17,10H13L17,2H7Z",
  off: "M17,10H13L17,2H7V4.18L15.46,12.64M3.27,3L2,4.27L7,9.27V13H10V22L13.58,15.86L17.73,20L19,18.73L3.27,3Z",
  maybe: "M5,2V13H8V22L15,10H11L15,2M17,15H19V17H17V15M17,7H19V13H17V7Z",
};

const KYIV_DAY = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Kyiv", year: "numeric", month: "2-digit", day: "2-digit" });

const KYIV = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/Kyiv",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

const STYLE = `
  :host {
    display: block;
    --co-on: var(--success-color, #43a047);
    --co-off: var(--error-color, #db4437);
    --co-maybe: color-mix(in srgb, var(--secondary-text-color, #727272) 55%, transparent);
    --co-none: var(--divider-color, rgba(0, 0, 0, 0.12));
  }
  ha-card { overflow: hidden; height: 100%; display: flex; flex-direction: column; }
  .card-header {
    color: var(--ha-card-header-color, var(--primary-text-color));
    font-family: var(--ha-card-header-font-family, inherit);
    font-size: var(--ha-card-header-font-size, var(--ha-font-size-2xl, 24px));
    font-weight: var(--ha-font-weight-normal, 400);
    letter-spacing: -0.012em;
    line-height: var(--ha-line-height-expanded, 1.5);
    padding: 12px 16px 4px;
    margin: 0;
  }
  .tile {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 16px; margin: 0; cursor: pointer; outline: none;
    border-radius: var(--ha-card-border-radius, 12px);
  }
  .tile:focus-visible { box-shadow: inset 0 0 0 2px var(--primary-color); }
  .icon {
    flex: none; width: 36px; height: 36px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    --tile-color: var(--co-none);
    color: var(--tile-color);
    background: color-mix(in srgb, var(--tile-color) 20%, transparent);
  }
  .icon.on { --tile-color: var(--co-on); }
  .icon.off { --tile-color: var(--co-off); }
  .icon.maybe { --tile-color: var(--secondary-text-color); }
  .icon svg { width: 24px; height: 24px; fill: currentColor; }
  .info { min-width: 0; display: flex; flex-direction: column; }
  .primary {
    color: var(--primary-text-color);
    font-size: var(--ha-font-size-m, 14px); font-weight: var(--ha-font-weight-medium, 500);
    line-height: 20px; letter-spacing: 0.1px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .secondary {
    color: var(--secondary-text-color);
    font-size: var(--ha-font-size-s, 12px); line-height: 16px; letter-spacing: 0.4px;
  }
  .timeline { padding: 4px 16px 0; display: flex; flex-direction: column; gap: 10px; }
  .day { display: flex; flex-direction: column; gap: 4px; }
  .label { color: var(--secondary-text-color); font-size: var(--ha-font-size-s, 12px); line-height: 16px; }
  .empty {
    height: 20px; box-sizing: border-box; border-radius: 6px;
    border: 1px dashed var(--divider-color, rgba(0, 0, 0, 0.12));
    display: flex; align-items: center; justify-content: center;
    color: var(--secondary-text-color); font-size: var(--ha-font-size-s, 12px);
  }
  .marks {
    position: relative; height: 14px; margin-bottom: -2px;
    font-size: 11px; line-height: 14px; font-variant-numeric: tabular-nums;
    color: var(--primary-text-color); font-weight: var(--ha-font-weight-medium, 500);
  }
  .marks span { position: absolute; white-space: nowrap; transform: translateX(-50%); }
  .marks span.done { color: var(--secondary-text-color); font-weight: var(--ha-font-weight-normal, 400); }
  .bar {
    position: relative; display: flex; height: 20px;
    border-radius: 6px; overflow: visible;
  }
  .segments { display: flex; width: 100%; height: 100%; border-radius: 6px; overflow: hidden; }
  .seg { height: 100%; min-width: 0; }
  .seg.on { background: var(--co-on); }
  .seg.off {
    background-color: var(--co-off);
    background-image: repeating-linear-gradient(135deg, rgba(255, 255, 255, 0.28) 0 3px, transparent 3px 7px);
  }
  .seg.maybe {
    background-color: var(--co-maybe);
    background-image: repeating-linear-gradient(45deg, rgba(255, 255, 255, 0.3) 0 2px, transparent 2px 5px);
  }
  .seg.none { background: var(--co-none); }
  .past {
    position: absolute; left: 0; top: 0; bottom: 0;
    border-radius: 6px 0 0 6px;
    background: var(--ha-card-background, var(--card-background-color, #fff));
    opacity: 0.55; pointer-events: none;
  }
  .now {
    position: absolute; top: -4px; bottom: -4px; width: 2px; margin-left: -1px;
    border-radius: 1px; background: var(--primary-text-color); pointer-events: none;
  }
  .ticks { position: relative; height: 16px; color: var(--secondary-text-color); font-size: 11px; line-height: 16px; }
  .ticks span { position: absolute; transform: translateX(-50%); white-space: nowrap; }
  .ticks span:first-child { transform: none; }
  .ticks span:last-child { transform: translateX(-100%); }
  .legend {
    display: flex; flex-wrap: wrap; gap: 4px 16px; padding: 8px 16px 16px;
    color: var(--secondary-text-color); font-size: var(--ha-font-size-s, 12px); line-height: 16px;
  }
  .legend span { display: inline-flex; align-items: center; gap: 6px; }
  .legend .seg { display: inline-block; width: 12px; height: 12px; border-radius: 3px; flex: none; }
  .legend .changed { margin-left: auto; }
  .note { padding: 0 16px 16px; margin-top: -8px; color: var(--secondary-text-color); font-size: var(--ha-font-size-s, 12px); line-height: 16px; }
  .warning { padding: 16px; color: var(--error-color); }
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

function icon(state) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", ICONS[state] || ICONS.maybe);
  svg.append(path);
  return svg;
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
  const h = hour % 24;
  if (!uses12h(hass)) return `${String(h).padStart(2, "0")}:00`;
  return `${h % 12 || 12} ${h < 12 ? "AM" : "PM"}`;
}

const NUMBER_LOCALES = { comma_decimal: "en-US", decimal_comma: "de-DE", space_comma: "fr-FR", none: "en-US" };

function formatHours(hass, value) {
  const format = hass?.locale?.number_format;
  const locale = format === "system" ? undefined : NUMBER_LOCALES[format] || hass?.locale?.language;
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 1, useGrouping: false }).format(value);
}

// CSS already centres each duration over its outage. When the card is laid out, also
// keep the edge ones inside the bar and drop the ones that would collide; a card
// rendered while hidden has no width yet and keeps the CSS placement.
function fitMarks(row) {
  const width = row.clientWidth;
  if (!width) return;
  let right = -Infinity;
  for (const mark of row.children) {
    mark.style.visibility = "";
    const w = mark.offsetWidth;
    const left = Math.min(Math.max(Number(mark.dataset.mid) * width - w / 2, 0), width - w);
    mark.style.left = `${left}px`;
    mark.style.transform = "none";
    if (left < right + 6) mark.style.visibility = "hidden";
    else right = left + w;
  }
}

// Minutes of outage touching midnight: at the start of `periods` when `first`, else at the end.
function overnight(periods, first) {
  if (!Array.isArray(periods) || !periods.length) return 0;
  const p = first ? periods[0] : periods[periods.length - 1];
  if (p.state !== "off" || (first ? p.start !== "00:00" : p.end !== "24:00")) return 0;
  return minutes(p.end) - minutes(p.start);
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
      throw new Error("Set `entity` to the Schedule now sensor of an outage group");
    }
    if (config.title !== undefined && typeof config.title !== "string") {
      throw new Error("`title` must be text; an empty title hides the header");
    }
    this._config = config;
    this._key = null;
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const state = hass.states[this._config?.entity];
    // Redraw when the sensor or the locale changes, and once a minute for the now marker.
    const changed = hass.states[this._changedId()]?.state;
    const key = [state?.last_updated, changed, Math.floor(Date.now() / 60000), hass.locale?.language, hass.locale?.time_format].join("|");
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

  // The group's Schedule changed at sensor, found by its key on the same device.
  _changedId() {
    const entities = this._hass?.entities || {};
    const device = entities[this._config?.entity]?.device_id;
    if (!device) return undefined;
    return Object.values(entities).find((e) => e.platform === "chernivtsi_outages" && e.translation_key === "changed" && e.device_id === device)?.entity_id;
  }

  _changedText(t) {
    const value = this._hass.states[this._changedId()]?.state;
    const date = value ? new Date(value) : null;
    if (!date || Number.isNaN(date.getTime())) return null;
    const day = KYIV_DAY.format(date);
    const today = KYIV_DAY.format(new Date());
    const yesterday = KYIV_DAY.format(new Date(Date.now() - 86400000));
    const at = formatTime(this._hass, KYIV.format(date));
    const when = day === today ? "today" : day === yesterday ? "yesterday" : `${day.slice(8, 10)}.${day.slice(5, 7)}`;
    return t.changed(when, at);
  }

  _moreInfo() {
    this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId: this._config.entity }, bubbles: true, composed: true }));
  }

  _bar(periods, now, t) {
    const bar = el("div", { class: "bar" });
    const segments = el("div", { class: "segments" });
    for (const p of periods) {
      const start = minutes(p.start);
      const end = minutes(p.end);
      segments.append(
        el("div", {
          class: `seg ${p.state}`,
          style: { flex: `${end - start} 0 0` },
          title: `${formatTime(this._hass, p.start)}-${formatTime(this._hass, p.end)} ${t[p.state] || ""}`,
        })
      );
    }
    bar.append(segments);
    if (now !== null) {
      bar.append(el("div", { class: "past", style: { width: `${(now / 1440) * 100}%` } }));
      bar.append(el("div", { class: "now", style: { left: `${(now / 1440) * 100}%` } }));
    }
    return bar;
  }

  // `carry` is the length of the same outage on the other side of midnight, so both halves show its full length.
  _marks(periods, now, t, carry) {
    const outages = periods.filter((p) => p.state === "off");
    if (!outages.length) return null;
    return el(
      "div",
      { class: "marks" },
      outages.map((p) => {
        const start = minutes(p.start);
        const end = minutes(p.end);
        const extra = (start === 0 ? carry.before : 0) + (end === 1440 ? carry.after : 0);
        return el("span", {
          class: now !== null && end <= now ? "done" : "",
          "data-mid": String((start + end) / 2 / 1440),
          style: { left: `${((start + end) / 2 / 1440) * 100}%` },
          text: t.hours(formatHours(this._hass, (end - start + extra) / 60)),
        });
      })
    );
  }

  _day(label, periods, now, t, missing, carry = { before: 0, after: 0 }) {
    const known = Array.isArray(periods);
    const body = known ? this._bar(periods, now, t) : el("div", { class: "empty", text: missing });
    return el("div", { class: "day", role: "group", "aria-label": label }, [
      el("div", { class: "label", text: label }),
      known ? this._marks(periods, now, t, carry) : null,
      body,
    ]);
  }

  _fit() {
    for (const row of this.shadowRoot.querySelectorAll(".marks")) fitMarks(row);
  }

  connectedCallback() {
    if (this.shadowRoot) requestAnimationFrame(() => this._fit());
    if (!this._resize && "ResizeObserver" in window) {
      this._resize = new ResizeObserver(() => this.shadowRoot && this._fit());
      this._resize.observe(this);
    }
  }

  disconnectedCallback() {
    this._resize?.disconnect();
    this._resize = null;
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
    const card = el("ha-card");
    if (!state) {
      card.append(el("div", { class: "warning", text: `${t.missing}: ${this._config.entity}` }));
      this.shadowRoot.replaceChildren(el("style", { text: STYLE }), card);
      return;
    }
    const a = state.attributes;
    const now = minutes(KYIV.format(new Date()));
    const title = this._config.title ?? (a.group ? t.title(a.group) : a.friendly_name);
    const current = this._hass.formatEntityState ? this._hass.formatEntityState(state) : t[state.state] || state.state;

    const tile = el("div", { class: "tile", role: "button", tabindex: "0" }, [
      el("div", { class: `icon ${state.state}` }, [icon(state.state)]),
      el("div", { class: "info" }, [
        el("div", { class: "primary", text: current }),
        el("div", { class: "secondary", text: this._summary(a, now, t) }),
      ]),
    ]);
    tile.addEventListener("click", () => this._moreInfo());
    tile.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        this._moreInfo();
      }
    });

    const ticks = el(
      "div",
      { class: "ticks", "aria-hidden": "true" },
      [0, 6, 12, 18, 24].map((h) => el("span", { text: formatHour(this._hass, h), style: { left: `${(h / 24) * 100}%` } }))
    );
    const changed = this._changedText(t);
    const legend = el("div", { class: "legend" }, [
      ...["on", "off", "maybe"].map((s) => el("span", {}, [el("i", { class: `seg ${s}` }), document.createTextNode(t[s])])),
      changed ? el("span", { class: "changed", text: changed }) : null,
    ]);

    card.append(
      ...(title ? [el("h1", { class: "card-header", text: title })] : []),
      tile,
      el("div", { class: "timeline" }, [
        this._day(t.today, a.today, now, t, t.unknown, { before: 0, after: overnight(a.tomorrow, true) }),
        this._day(t.tomorrow, a.tomorrow, null, t, t.notPublished, { before: overnight(a.today, false), after: 0 }),
        ticks,
      ]),
      legend,
      ...(a.degraded ? [el("div", { class: "note", text: t.degraded })] : [])
    );
    this.shadowRoot.replaceChildren(el("style", { text: STYLE }), card);
    this._fit();
    requestAnimationFrame(() => this._fit());
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
