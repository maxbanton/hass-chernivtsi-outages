"""Builders for site and channel pages, and a fake web to serve them."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from custom_components.chernivtsi_outages.api import FetchError
from custom_components.chernivtsi_outages.const import (
    GROUPS,
    KYIV,
    TELEGRAM_URL,
)

FIXTURES = Path(__file__).parent / "fixtures"
ON = "u" * 48
NOTICE = "Шановні абоненти! Передайте показники лічильника."


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def codes(off: tuple[int, int] | None = None, maybe: int | None = None) -> str:
    """48 slot codes, all on except an outage [start, end) and one maybe slot."""
    row = list(ON)
    if off:
        row[off[0] : off[1]] = "o" * (off[1] - off[0])
    if maybe is not None:
        row[maybe] = "s"
    return "".join(row)


def site_page(day: date, stamp: str, rows: dict[int, str] | None = None) -> str:
    rows = rows or {}
    tags = {"u": "<u>з</u>", "o": "<o>в</o>", "s": "<s>мз</s>"}
    cells = "".join(
        f'<div id="inf{g}" data-id="{g}">{"".join(tags[c] for c in rows.get(g, ON))}</div>'
        for g in GROUPS
    )
    return (
        "<html><head><title>Відключення - АТ &quot;Чернівціобленерго&quot;</title></head><body>"
        f"<p>Графік актуальний станом на <b>{stamp}</b></p>"
        f'<div id="gsv" highlight="0"><ul><p>{day:%d.%m.%Y}\n</p></ul><div>{cells}</div></div>'
        "</body></html>"
    )


def empty_site_page() -> str:
    return (
        "<html><head><title>Відключення - АТ &quot;Чернівціобленерго&quot;</title></head>"
        "<body><p>Графік погодинних відключень</p></body></html>"
    )


def windows(row: str) -> list[str]:
    lines, start = [], None
    for i, code in enumerate(row + "o"):
        if code == "u" and start is None:
            start = i
        elif code != "u" and start is not None:
            begin = f"{start // 2:02d}:{30 * (start % 2):02d}"
            lines.append(f"з {begin}" if i == 48 else f"{begin} - {i // 2:02d}:{30 * (i % 2):02d}")
            start = None
    return lines


def schedule_text(day: date, rows: dict[int, str] | None = None) -> str:
    rows = rows or {}
    blocks = [f"💡 Група {g}\n" + "\n".join(windows(rows.get(g, ON))) for g in GROUPS]
    text = f"⚡️ Орієнтовний графік заживлення для груп споживачів • {day:%d.%m.%Y}\n\n"
    return text + "\n\n".join(blocks) + "\n\n☝️Дізнатись номер своєї групи можна за пошуком"


def image_text(day: date) -> str:
    return (
        f"⚡ Орієнтовний графік заживлення на {day:%d.%m.%Y}\n"
        "━━━━━━━━\n🔍 Дізнатись номер своєї групи"
    )


def quiet_text(day: date) -> str:
    return f"✨ На {day:%d.%m.%Y}\nЕлектропостачання без обмежень для всіх груп споживачів!"


def telegram_page(posts: list[tuple[int, datetime, str]]) -> str:
    items = "".join(
        f'<div class="tgme_widget_message_wrap"><div class="tgme_widget_message" '
        f'data-post="oe_cv_ua/{pid}"><div class="tgme_widget_message_text js-message_text" '
        f'dir="auto">{text.replace(chr(10), "<br/>")}</div>'
        f'<a class="tgme_widget_message_date"><time datetime="{posted.isoformat()}" '
        f'class="time">00:00</time></a></div></div>'
        for pid, posted, text in posts
    )
    return f'<html><body><section class="tgme_channel_history">{items}</section></body></html>'


class FakeWeb:
    """Answers fetches from a URL map and records what was asked."""

    def __init__(self) -> None:
        self.pages: dict[str, str | Exception] = {
            TELEGRAM_URL: telegram_page([(1, datetime(2026, 1, 5, 12, tzinfo=KYIV), NOTICE)]),
        }
        self.calls: list[str] = []

    def set(self, url: str, page: str | Exception) -> None:
        self.pages[url] = page

    def count(self, url: str) -> int:
        return self.calls.count(url)

    async def fetch(self, url: str) -> str:
        self.calls.append(url)
        page = self.pages.get(url, FetchError("HTTP 404"))
        if isinstance(page, Exception):
            raise page
        return page
