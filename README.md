# Chernivtsi Power Outages for Home Assistant

[![Tests](https://github.com/maxbanton/hass-chernivtsi-outages/actions/workflows/tests.yml/badge.svg)](https://github.com/maxbanton/hass-chernivtsi-outages/actions/workflows/tests.yml)
[![Validate](https://github.com/maxbanton/hass-chernivtsi-outages/actions/workflows/validate.yml/badge.svg)](https://github.com/maxbanton/hass-chernivtsi-outages/actions/workflows/validate.yml)
[![License](https://img.shields.io/github/license/maxbanton/hass-chernivtsi-outages)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.12%2B-41BDF5.svg)](https://www.home-assistant.io)

Scheduled power outages of the Chernivtsi region (Bukovyna, Ukraine) in Home
Assistant: the current state of your outage group, the next outage, when power
comes back, a calendar, events when the schedule changes, and a dashboard card.

[Українською](README.uk.md)

> **Unofficial.** This project is not affiliated with or endorsed by
> JSC "Chernivtsioblenergo". It reads the schedule they publish on
> [oblenergo.cv.ua](https://oblenergo.cv.ua/shutdowns/) and their
> [Telegram channel](https://t.me/oe_cv_ua). Emergency outages happen regardless
> of any schedule.

## What it is for

The schedule changes several times a day, outages get moved earlier or later,
and tomorrow's schedule often appears late in the evening. With the schedule in
Home Assistant you can:

- charge a home battery from the grid before an outage starts, and plan again
  every time the schedule changes;
- check that the battery holds enough energy for the coming outage, and shed
  load early if it does not;
- run the boiler, washer or heating in the hours when power is guaranteed;
- get a notification before an outage and when the schedule changes;
- compare scheduled outage hours with what actually happened.

## The three states

Every half hour of the schedule is one of:

| State | On the site | Meaning |
|---|---|---|
| `on` | green, "з" | power is on |
| `off` | red, "в" | scheduled outage |
| `maybe` | grey, "мз" | possible outage, power may or may not be on |

The integration keeps the three apart everywhere. A possible outage is never
counted as power on, and never as an outage.

## Entities

One device per outage group, with these entities:

| Entity | Example | Description |
|---|---|---|
| Schedule | `sensor.outage_group_12_schedule` | `on`, `off` or `maybe` right now. Attributes `today` and `tomorrow` hold the day's periods. |
| Scheduled outage | `binary_sensor.outage_group_12_scheduled_outage` | On during a scheduled outage. |
| Next outage | `sensor.outage_group_12_next_outage` | Start of the next outage that has not begun yet. Attributes: `end`, `duration_hours`. |
| Power back | `sensor.outage_group_12_power_back` | End of the current outage, or of the next one. Attribute `then` says whether `on` or `maybe` follows. |
| Outage hours today | `sensor.outage_group_12_outage_hours_today` | Scheduled outage hours today. |
| Possible outage hours today | `sensor.outage_group_12_possible_outage_hours_today` | Possible outage hours today. |
| Schedule updated | `sensor.outage_group_12_schedule_updated` | The time the publisher says the schedule is current as of (diagnostic). |
| Outages | `calendar.outage_group_12_outages` | Outages and possible outages, today and tomorrow. |
| Schedule change | `event.outage_group_12_schedule_change` | Fires when the schedule changes, see below. |

States change exactly at :00 and :30. Times that depend on a day that is not
published yet are `unknown`: an outage running to midnight has no known end
until tomorrow's schedule is out.

The hours sensors count each half hour as it was scheduled when it passed, so a
later revision does not rewrite the past. Their attributes show
`revisions_today` and `originally_scheduled_hours`, the first version of the
day.

### Schedule change events

The event entity fires one of these types, with `date` and a `changes` list
(`type`, `start`, `end`, `old_start`, `old_end`):

| Event type | When |
|---|---|
| `schedule_published` | a schedule for a new day appeared |
| `outage_earlier` | an outage now starts earlier |
| `outage_added` | a new outage |
| `outage_longer` | an outage now ends later |
| `outage_later` | an outage now starts later |
| `outage_shorter` | an outage now ends earlier |
| `outage_removed` | an outage was cancelled |
| `schedule_changed` | anything else changed, such as possible outage hours |

When several things change at once, the most urgent type is reported and the
`changes` list has all of them. Nothing fires on Home Assistant start, so
automations that plan around outages should also run at start.

## Where the data comes from, and how often

The schedule page on oblenergo.cv.ua is the source of truth. It is not cached,
and every installation of this integration adds to its load, so the
integration asks as little as it can:

- The oblenergo Telegram channel is read every 5 minutes. That load is on
  Telegram, not on oblenergo.
- The site is fetched only when the channel announces a schedule, plus one
  safety fetch an hour while outages are on, or every 6 hours when there are
  none. If the channel cannot be read, the site is checked every 30 minutes.
- One fetch serves all your groups. Half hour boundaries are computed locally.
- Errors back off exponentially, and `Retry-After` is respected.
- Requests carry a User-Agent naming this project, so the site's admins can
  see who is asking and reach the project.

That is about 4 site requests a day without outages, and about 30 on a day with
frequent changes.

If the site is down, the hours listed in the channel are used. The channel
lists only the hours with power, so in that case every other half hour is shown
as an outage, and the Schedule sensor has `degraded: true`. Assuming an outage
is the safer mistake.

When the site shows no schedule at all, there are no outages. Right after a
day with outages, though, a missing schedule more likely means "not published
yet", so today stays `unknown` until a schedule or a "no outages" post appears.

## Installation

### HACS

1. In HACS, open the menu, choose **Custom repositories**, add
   `https://github.com/maxbanton/hass-chernivtsi-outages` as an **Integration**.
2. Install **Chernivtsi Power Outages** and restart Home Assistant.

### Manual

Copy `custom_components/chernivtsi_outages` into your `config/custom_components`
folder and restart Home Assistant.

## Configuration

**Settings > Devices & services > Add integration > Chernivtsi Power Outages**,
then pick one or more groups. Find your group by address on the
[oblenergo search page](https://oblenergo.cv.ua/shutdowns-search/). Change the
groups later in the integration's options.

## Card

The integration ships a dashboard card and loads it for you. Add it from the
card picker (**Chernivtsi Power Outages**) or in YAML:

```yaml
type: custom:chernivtsi-outages-card
entity: sensor.outage_group_12_schedule
```

It shows today and tomorrow as 48 half hour cells, a marker at the current
time, the next outage or when power comes back, and a legend. Outages are also
hatched and possible outages outlined, so the card does not rely on colour
alone. `title` overrides the heading.

## Automation examples

Notify 30 minutes before an outage:

```yaml
automation:
  - alias: Outage in 30 minutes
    triggers:
      - trigger: time
        at:
          entity_id: sensor.outage_group_12_next_outage
          offset: "-00:30:00"
    actions:
      - action: notify.notify
        data:
          message: >-
            Outage at {{ as_timestamp(states('sensor.outage_group_12_next_outage'))
            | timestamp_custom('%H:%M') }}
```

React to a changed schedule:

```yaml
automation:
  - alias: Outage moved earlier
    triggers:
      - trigger: state
        entity_id: event.outage_group_12_schedule_change
    conditions:
      - condition: template
        value_template: "{{ trigger.to_state.attributes.event_type in ['outage_earlier', 'outage_added'] }}"
    actions:
      - action: notify.notify
        data:
          message: "Outage schedule changed: {{ trigger.to_state.attributes.event_type }}"
```

Compare scheduled with actual outage hours, using your own sensor for grid
presence:

```yaml
sensor:
  - platform: history_stats
    name: Actual outage hours today
    entity_id: binary_sensor.grid_power
    state: "off"
    type: time
    start: "{{ today_at() }}"
    end: "{{ now() }}"
```

## Troubleshooting

- **Diagnostics:** the integration's menu has **Download diagnostics**, with
  what each source returned and when the site was last fetched.
- **Repairs:** if the site's or the channel's page layout changes, a repair
  issue appears. Please open an issue in this repository.

## Removal

Delete the integration under **Settings > Devices & services**. The card's
dashboard resource and the stored schedule are removed with it. Then remove the
files, or uninstall it in HACS.

## License

MIT
