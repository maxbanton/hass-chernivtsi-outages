"""HTTP access to the schedule page and the Telegram channel."""
from __future__ import annotations

import aiohttp

from .const import REQUEST_TIMEOUT


class FetchError(Exception):
    """A page could not be fetched."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def _retry_after(value: str | None) -> float | None:
    try:
        return max(float(value), 0) if value is not None else None
    except ValueError:
        return None


class Client:
    """Fetches pages with a User-Agent that says who is asking."""

    def __init__(self, session: aiohttp.ClientSession, user_agent: str) -> None:
        self._session = session
        self._headers = {"User-Agent": user_agent}

    async def fetch(self, url: str) -> str:
        try:
            async with self._session.get(
                url,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                if response.status >= 400:
                    raise FetchError(
                        f"HTTP {response.status}",
                        _retry_after(response.headers.get("Retry-After")),
                    )
                return await response.text()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise FetchError(str(err) or type(err).__name__) from err
