// Rules of the outage card, run with `node --test "tests/js/*.test.mjs"`.
import assert from "node:assert/strict";
import { describe, test } from "node:test";

import {
  changedWhen,
  countdown,
  formatClock,
  hhmm,
  kyivMinutes,
  mergeDays,
  nextEvent,
  outageMarks,
  overnight,
} from "../../custom_components/chernivtsi_outages/frontend/outages-card-logic.js";

// A day from 48 half hour codes, as the site writes them: u on, o off, s maybe.
function day(codes) {
  const state = { u: "on", o: "off", s: "maybe" };
  const periods = [];
  [...codes].forEach((c, i) => {
    const end = i === 47 ? "24:00" : hhmm((i + 1) * 30);
    const last = periods[periods.length - 1];
    if (last && last.state === state[c]) last.end = end;
    else periods.push({ start: hhmm(i * 30), end, state: state[c] });
  });
  return periods;
}
const ON = "u".repeat(48);
const at = (h, m = 0) => h * 60 + m;
const schedule = (today, tomorrow = null, active = true) => ({ today: day(today), tomorrow: tomorrow && day(tomorrow), schedule_active: active });

describe("nextEvent", () => {
  test("an outage later today", () => {
    assert.deepEqual(nextEvent(schedule("uu" + "oooo" + "u".repeat(42), ON), at(0, 40)), {
      kind: "next", at: "01:00", to: "03:00", tomorrow: false, in: 20,
    });
  });
  test("an outage tomorrow says so", () => {
    assert.deepEqual(nextEvent(schedule(ON, "u".repeat(16) + "ooooo" + "u".repeat(27)), at(23)), {
      kind: "next", at: "08:00", to: "10:30", tomorrow: true, in: 540,
    });
  });
  test("power back after midnight says tomorrow, and whether possibly powered hours follow", () => {
    assert.deepEqual(nextEvent(schedule("o".repeat(48), "oooooo" + "s" + "u".repeat(41)), at(23)), {
      kind: "back", at: "03:00", maybe: true, tomorrow: true, in: 240,
    });
  });
  test("an outage across midnight is one outage", () => {
    const e = nextEvent(schedule("u".repeat(46) + "oo", "oo" + "u".repeat(46)), at(20));
    assert.deepEqual(e, { kind: "next", at: "23:00", to: "01:00", tomorrow: false, in: 180 });
  });
  test("an outage running into an unpublished tomorrow has no known end", () => {
    assert.deepEqual(nextEvent(schedule("u".repeat(46) + "oo", null), at(23, 10)), { kind: "off" });
    assert.deepEqual(nextEvent(schedule("u".repeat(46) + "oo", null), at(20)), {
      kind: "next", at: "23:00", to: null, tomorrow: false, in: 180,
    });
  });
  test("no more outages in what is published", () => {
    assert.deepEqual(nextEvent(schedule("oo" + "u".repeat(46), ON), at(12)), { kind: "none" });
  });
  test("a quiet day stays quiet unless tomorrow has an outage", () => {
    assert.deepEqual(nextEvent(schedule(ON, null, false), at(12)), { kind: "quiet" });
    assert.equal(nextEvent(schedule(ON, "oo" + "u".repeat(46), false), at(12)).kind, "next");
  });
  test("an unpublished today is unknown", () => {
    assert.deepEqual(nextEvent({ today: null, tomorrow: null }, at(12)), { kind: "unknown" });
  });
});

describe("countdown", () => {
  test("minutes, hours and minutes, whole hours", () => {
    assert.deepEqual(countdown(25), [[25, "min"]]);
    assert.deepEqual(countdown(130), [[2, "h"], [10, "min"]]);
    assert.deepEqual(countdown(120), [[2, "h"]]);
    assert.deepEqual(countdown(1500), [[25, "h"]]);
  });
  test("never says in 0 minutes", () => {
    assert.deepEqual(countdown(0), [[1, "min"]]);
    assert.deepEqual(countdown(0.4), [[1, "min"]]);
  });
});

describe("mergeDays", () => {
  test("joins the same state across midnight", () => {
    const merged = mergeDays(day("u".repeat(46) + "oo"), day("oo" + "u".repeat(46)));
    assert.deepEqual(merged, [
      { state: "on", s: 0, e: 1380 },
      { state: "off", s: 1380, e: 1500 },
      { state: "on", s: 1500, e: 2880 },
    ]);
  });
});

describe("outage lengths", () => {
  test("an outage touching midnight counts the other day's part", () => {
    const today = day("u".repeat(46) + "oo");
    const tomorrow = day("oo" + "u".repeat(46));
    assert.equal(overnight(tomorrow, true), 60);
    assert.equal(overnight(today, false), 60);
    assert.deepEqual(outageMarks(today, null, { before: 0, after: overnight(tomorrow, true) }).map((m) => m.hours), [2]);
    assert.deepEqual(outageMarks(tomorrow, null, { before: overnight(today, false), after: 0 }).map((m) => m.hours), [2]);
  });
  test("nothing carries when the day does not start or end with an outage", () => {
    assert.equal(overnight(day(ON), true), 0);
    assert.equal(overnight(null, true), 0);
  });
  test("each mark sits at its outage's middle and knows whether it has ended", () => {
    const marks = outageMarks(day("u".repeat(35) + "oooo" + "s" + "u".repeat(8)), at(20));
    assert.equal(marks.length, 1);
    assert.equal(marks[0].hours, 2);
    assert.equal(marks[0].mid, (at(17, 30) + at(19, 30)) / 2 / 1440);
    assert.equal(marks[0].done, true);
    assert.equal(outageMarks(day("u".repeat(35) + "oooo" + "s" + "u".repeat(8)), at(18))[0].done, false);
  });
});

describe("changedWhen", () => {
  const now = new Date("2026-11-04T08:00:00Z"); // 10:00 in Kyiv
  test("today, yesterday or the date, in Kyiv time", () => {
    assert.deepEqual(changedWhen("2026-11-04T06:15:00Z", now), { when: "today", time: "08:15" });
    assert.deepEqual(changedWhen("2026-11-03T19:52:41Z", now), { when: "yesterday", time: "21:52" });
    assert.deepEqual(changedWhen("2026-11-01T10:00:00Z", now), { when: "01.11", time: "12:00" });
  });
  test("just after midnight in Kyiv it is already the next day", () => {
    // 22:30 UTC on the 3rd is 00:30 in Kyiv on the 4th.
    assert.deepEqual(changedWhen("2026-11-03T22:30:00Z", now), { when: "today", time: "00:30" });
  });
  test("yesterday is the calendar day before, also across a clock change", () => {
    // Kyiv moves from summer to winter time on 25 October 2026.
    const after = new Date("2026-10-26T00:10:00Z"); // 02:10 on the 26th in Kyiv
    assert.equal(changedWhen("2026-10-25T20:00:00Z", after).when, "yesterday");
  });
  test("no time for a missing or broken value", () => {
    assert.equal(changedWhen(null, now), null);
    assert.equal(changedWhen("unknown", now), null);
  });
});

describe("clock", () => {
  test("24 and 12 hour formats, and 24:00 as midnight", () => {
    assert.equal(formatClock("08:00", false), "08:00");
    assert.equal(formatClock("24:00", false), "00:00");
    assert.equal(formatClock("13:30", true), "1:30 PM");
    assert.equal(formatClock("00:30", true), "12:30 AM");
  });
  test("Kyiv minutes whatever the machine's zone", () => {
    assert.equal(kyivMinutes(new Date("2026-11-04T08:00:00Z")), at(10));
  });
});
