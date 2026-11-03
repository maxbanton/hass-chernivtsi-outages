"""Constants for Chernivtsi Power Outages."""
from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo

DOMAIN = "chernivtsi_outages"

CONF_GROUPS = "groups"
GROUPS = tuple(range(1, 13))

# The schedule is published in Kyiv wall-clock time, whatever timezone the
# Home Assistant instance runs in.
KYIV = ZoneInfo("Europe/Kyiv")

SITE_URL = "https://oblenergo.cv.ua/shutdowns/"
SITE_NEXT_URL = "https://oblenergo.cv.ua/shutdowns/?next="
SEARCH_URL = "https://oblenergo.cv.ua/shutdowns-search/"
TELEGRAM_URL = "https://t.me/s/oe_cv_ua"
REPO_URL = "https://github.com/maxbanton/hass-chernivtsi-outages"

# The channel is checked often because Telegram carries that load. The site is
# fetched only when the channel announces a schedule, plus a safety fetch whose
# interval depends on whether outages are happening at all.
TELEGRAM_INTERVAL = timedelta(minutes=5)
SITE_SAFETY_ACTIVE = timedelta(hours=1)
SITE_SAFETY_QUIET = timedelta(hours=6)
SITE_SAFETY_NO_TELEGRAM = timedelta(minutes=30)
SITE_BACKOFF_MAX = timedelta(hours=1)
VERIFY_ATTEMPTS = 3
REQUEST_TIMEOUT = 30

SOURCE_SITE = "site"
SOURCE_TELEGRAM = "telegram"

STORAGE_VERSION = 1
