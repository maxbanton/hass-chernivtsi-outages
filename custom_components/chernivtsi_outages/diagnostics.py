"""Diagnostics: what each source returned and how the fetch schedule stands.

Nothing here is secret: the schedule is public and the entry holds only the
chosen groups.
"""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import OutageConfigEntry
from .model import encode


def _iso(value: Any) -> str | None:
    return value.isoformat() if value else None


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: OutageConfigEntry
) -> dict[str, Any]:
    c = entry.runtime_data
    return {
        "groups": c.groups,
        "site": {
            "last_fetch": _iso(c.last_site),
            "errors": c.site_errors,
            "error": c.site_error,
            "retry_at": _iso(c.site_retry_at),
        },
        "telegram": {
            "ok": c.telegram_ok,
            "error": c.telegram_error,
            "last_post_id": c.last_post_id,
            "posts": [
                {
                    "id": p.id,
                    "posted": p.posted.isoformat(),
                    "date": p.day.isoformat(),
                    "outages": p.outages,
                    "text_schedule": p.groups is not None,
                }
                for p in c.posts
            ],
        },
        "days": {
            day.isoformat(): {
                "source": s.source,
                "active": s.active,
                "degraded": s.degraded,
                "updated": _iso(s.updated),
                "changed": _iso(s.changed),
                "revisions": c.revisions.get(day, 0),
                "groups": {g: encode(slots) for g, slots in s.groups.items()},
            }
            for day, s in sorted(c.days.items())
        },
    }
