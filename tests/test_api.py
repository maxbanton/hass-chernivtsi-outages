"""The HTTP client: User-Agent, errors and Retry-After."""

from __future__ import annotations

import asyncio

import aiohttp
import pytest
import pytest_asyncio
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.chernivtsi_outages.api import Client, FetchError

URL = "https://example.test/page"


@pytest_asyncio.fixture
async def client(aioclient_mock: AiohttpClientMocker):
    session = aioclient_mock.create_session(asyncio.get_running_loop())
    yield Client(session, "agent/1")
    await session.close()


async def test_fetch_sends_the_user_agent(
    aioclient_mock: AiohttpClientMocker, client: Client
) -> None:
    aioclient_mock.get(URL, text="hello")
    assert await client.fetch(URL) == "hello"
    assert aioclient_mock.mock_calls[0][3]["User-Agent"] == "agent/1"


@pytest.mark.parametrize(
    ("headers", "retry_after"),
    [({"Retry-After": "120"}, 120.0), ({"Retry-After": "soon"}, None), ({}, None)],
)
async def test_http_errors_carry_retry_after(
    aioclient_mock: AiohttpClientMocker,
    client: Client,
    headers: dict[str, str],
    retry_after: float | None,
) -> None:
    aioclient_mock.get(URL, status=429, headers=headers)
    with pytest.raises(FetchError) as err:
        await client.fetch(URL)
    assert err.value.retry_after == retry_after
    assert str(err.value) == "HTTP 429"


@pytest.mark.parametrize("exc", [aiohttp.ClientConnectionError(), TimeoutError()])
async def test_network_errors(
    aioclient_mock: AiohttpClientMocker, client: Client, exc: Exception
) -> None:
    aioclient_mock.get(URL, exc=exc)
    with pytest.raises(FetchError):
        await client.fetch(URL)
