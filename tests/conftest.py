"""Shared fixtures."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from .helpers import FakeWeb


@pytest.fixture
def web() -> FakeWeb:
    fake = FakeWeb()

    async def fetch(_client, url: str) -> str:
        return await fake.fetch(url)

    with patch("custom_components.chernivtsi_outages.api.Client.fetch", fetch):
        yield fake


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    return
