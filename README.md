# Chernivtsi Power Outages for Home Assistant

[![Tests](https://github.com/maxbanton/hass-chernivtsi-outages/actions/workflows/tests.yml/badge.svg)](https://github.com/maxbanton/hass-chernivtsi-outages/actions/workflows/tests.yml)
[![Validate](https://github.com/maxbanton/hass-chernivtsi-outages/actions/workflows/validate.yml/badge.svg)](https://github.com/maxbanton/hass-chernivtsi-outages/actions/workflows/validate.yml)
[![License](https://img.shields.io/github/license/maxbanton/hass-chernivtsi-outages)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.12%2B-41BDF5.svg)](https://www.home-assistant.io)

Scheduled power outages in the Chernivtsi region (Bukovyna, Ukraine) in Home
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
- run the boiler, washer or heating in the hours when power is scheduled;
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
| Schedule now | `sensor.outage_group_12_schedule_now` | `on`, `off` or `maybe` right now, as scheduled. Attributes `today` and `tomorrow` hold each day's periods. |
| Power by schedule | `binary_sensor.outage_group_12_power_by_schedule` | On while power is scheduled. Off during an outage and during a possible outage. |
| Expected next outage | `sensor.outage_group_12_expected_next_outage` | Start of the next scheduled outage that has not begun yet. Attributes `end` and `duration_hours`. |
| Expected power back | `sensor.outage_group_12_expected_power_back` | Scheduled end of the current outage, or of the next one. Attribute `then` says whether `on` or `maybe` follows. |
| Scheduled outage hours today | `sensor.outage_group_12_scheduled_outage_hours_today` | Scheduled outage hours today. |
| Possible outage hours today | `sensor.outage_group_12_possible_outage_hours_today` | Possible outage hours today. Disabled by default. |
| Schedule changed at | `sensor.outage_group_12_schedule_changed_at` | When the current version of today's schedule was published (diagnostic). |
| Scheduled outages | `calendar.outage_group_12_scheduled_outages` | Outages and possible outages, today and tomorrow. |
| Schedule change | `event.outage_group_12_schedule_change` | Fires when the schedule changes (see below). |

All of these describe the published schedule, not the actual state of the grid:
emergency outages and delays happen. Use your own grid sensor for what really
happens.

States change at :00 and :30. Anything that depends on a schedule not
published yet is `unknown`, such as the end of an outage that runs past
midnight.

The hours sensors keep each half hour as it was scheduled at the time, so a
later revision does not rewrite the past. Attributes: `revisions_today`,
`originally_scheduled_hours`.

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
`changes` list has all of them. Nothing fires when Home Assistant starts, so
automations that plan around outages should also run at startup.

## Where the data comes from

The schedule comes from the oblenergo.cv.ua schedule page. The oblenergo
Telegram channel tells the integration when a new schedule is out, so changes
show up within minutes while the site is asked only a few times a day.

If the site is down, the hours posted in the channel are used. The channel
lists only the hours with power, so the rest of the day is shown as an outage
and the Schedule now sensor has `degraded: true`.

## Installation

### HACS

1. In HACS, open the menu, choose **Custom repositories** and add
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
entity: sensor.outage_group_12_schedule_now
```

It shows the current state with a countdown to what comes next, and today and
tomorrow as timelines. `title` replaces the header text; an empty `title` hides
the header.

## Automation examples

Notify 30 minutes before an outage:

```yaml
automation:
  - alias: Outage in 30 minutes
    triggers:
      - trigger: time
        at:
          entity_id: sensor.outage_group_12_expected_next_outage
          offset: "-00:30:00"
    actions:
      - action: notify.notify
        data:
          message: >-
            Outage at {{ as_timestamp(states('sensor.outage_group_12_expected_next_outage'))
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

- **Diagnostics:** the integration's menu has **Download diagnostics**. Attach the
  file when you open an issue.
- **Repairs:** if the site's or the channel's page layout changes, a repair
  issue appears. Please open an issue in this repository.

## Removal

Delete the integration under **Settings > Devices & services**. The card's
dashboard resource and the stored schedule are removed with it. Then remove the
files, or uninstall it in HACS.

## License

MIT
