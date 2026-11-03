// What the outage card shows, worked out from the schedule sensor's periods: no DOM
// and no Home Assistant objects, so every rule can be tested on its own. Times are
// minutes from today's midnight in Kyiv; tomorrow's run from 1440 on.

const DAY = 1440;

const KYIV_CLOCK = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/Kyiv",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});
const KYIV_DATE = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Kyiv", year: "numeric", month: "2-digit", day: "2-digit" });

export function minutes(hhmm) {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

export function hhmm(total) {
  const m = ((total % DAY) + DAY) % DAY;
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
}

// Minutes since midnight in Kyiv, the schedule's clock, whatever the browser's zone.
export function kyivMinutes(date) {
  return minutes(KYIV_CLOCK.format(date));
}

export function formatClock(value, twelveHour) {
  const [h, m] = (value === "24:00" ? "00:00" : value).split(":").map(Number);
  if (!twelveHour) return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
  return `${h % 12 || 12}:${String(m).padStart(2, "0")} ${h < 12 ? "AM" : "PM"}`;
}

// Today and tomorrow as one line, with neighbouring periods of the same state joined
// so an outage across midnight is one outage.
export function mergeDays(today, tomorrow) {
  const merged = [];
  [today || [], tomorrow || []].forEach((periods, d) =>
    periods.forEach((p) => {
      const s = d * DAY + minutes(p.start);
      const e = d * DAY + minutes(p.end);
      const last = merged[merged.length - 1];
      if (last && last.state === p.state && last.e === s) last.e = e;
      else merged.push({ state: p.state, s, e });
    }),
  );
  return merged;
}

// The line under the current state. `kind` is one of:
//   unknown   today's schedule is not published
//   quiet     no outages today, and none published for tomorrow
//   back      in an outage that ends at `at` (`maybe` when a possible outage follows)
//   off       in an outage whose end is not published yet
//   next      the next outage starts at `at`, ending at `to` when that is known
//   none      no more outages in what is published
// `tomorrow` says the time falls after midnight, and `in` how many minutes are left until it.
export function nextEvent(attrs, now) {
  if (!Array.isArray(attrs.today)) return { kind: "unknown" };
  if (attrs.schedule_active === false && !(attrs.tomorrow || []).some((p) => p.state === "off")) {
    return { kind: "quiet" };
  }
  const merged = mergeDays(attrs.today, attrs.tomorrow);
  const inside = merged.find((p) => p.s <= now && now < p.e);
  if (inside?.state === "off") {
    const after = merged.find((p) => p.s === inside.e);
    if (!after) return { kind: "off" };
    return { kind: "back", at: hhmm(inside.e), maybe: after.state === "maybe", tomorrow: inside.e >= DAY, in: inside.e - now };
  }
  const next = merged.find((p) => p.state === "off" && p.s > now);
  if (!next) return { kind: "none" };
  const ends = merged.some((p) => p.s === next.e);
  return { kind: "next", at: hhmm(next.s), to: ends ? hhmm(next.e) : null, tomorrow: next.s >= DAY, in: next.s - now };
}

// A countdown in whole hours and minutes: [[2, "h"], [10, "min"]]. Under a minute
// still reads as one, so it never says "in 0 min".
export function countdown(minutesLeft) {
  const total = Math.max(1, Math.round(minutesLeft));
  const h = Math.floor(total / 60);
  const m = total % 60;
  if (!h) return [[m, "min"]];
  return m ? [[h, "h"], [m, "min"]] : [[h, "h"]];
}

// Minutes of outage touching midnight: at the start of `periods` when `first`, else at the end.
export function overnight(periods, first) {
  if (!Array.isArray(periods) || !periods.length) return 0;
  const p = first ? periods[0] : periods[periods.length - 1];
  if (p.state !== "off" || (first ? p.start !== "00:00" : p.end !== "24:00")) return 0;
  return minutes(p.end) - minutes(p.start);
}

// One mark per outage of a day: where its middle is (0 to 1), its full length in
// hours, counting the part on the other side of midnight (`carry`), and whether it
// has ended by `now` (null for a day that is not today).
export function outageMarks(periods, now, carry = { before: 0, after: 0 }) {
  return (periods || [])
    .filter((p) => p.state === "off")
    .map((p) => {
      const start = minutes(p.start);
      const end = minutes(p.end);
      const extra = (start === 0 ? carry.before : 0) + (end === DAY ? carry.after : 0);
      return { mid: (start + end) / 2 / DAY, hours: (end - start + extra) / 60, end, done: now !== null && end <= now };
    });
}

// When a timestamp was, in Kyiv: "today", "yesterday" or "DD.MM", and the clock time.
export function changedWhen(value, now = new Date()) {
  const date = value ? new Date(value) : null;
  if (!date || Number.isNaN(date.getTime())) return null;
  const day = KYIV_DATE.format(date);
  const today = KYIV_DATE.format(now);
  // The calendar day before, not 24 hours before, which is off by one on DST days.
  const [y, m, d] = today.split("-").map(Number);
  const yesterday = new Date(Date.UTC(y, m - 1, d - 1)).toISOString().slice(0, 10);
  const when = day === today ? "today" : day === yesterday ? "yesterday" : `${day.slice(8, 10)}.${day.slice(5, 7)}`;
  return { when, time: KYIV_CLOCK.format(date) };
}
