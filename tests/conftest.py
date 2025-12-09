"""Fixtures for Chernivtsi Power Schedule tests."""
import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.cv_oblenergo.const import DOMAIN, CONF_GROUP
from custom_components.cv_oblenergo.api import (
    ScheduleData,
    GroupSchedule,
    TimeSlot,
    PowerScheduleApiClient,
)


# Sample HTML response from the schedule page
SAMPLE_SCHEDULE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<div id="gsv" highlight="0">
    <ul>
        <p>09.12.2025
</p>
    </ul>
    <div>
        <div id="inf1" data-id="1"><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u></div>
        <div id="inf2" data-id="2"><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u></div>
        <div id="inf3" data-id="3"><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u></div>
        <div id="inf4" data-id="4"><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u></div>
        <div id="inf5" data-id="5"><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u></div>
        <div id="inf6" data-id="6"><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o></div>
        <div id="inf7" data-id="7"><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u></div>
        <div id="inf8" data-id="8"><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u></div>
        <div id="inf9" data-id="9"><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o></div>
        <div id="inf10" data-id="10"><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o></div>
        <div id="inf11" data-id="11"><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o></div>
        <div id="inf12" data-id="12"><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><o>в</o><s>мз</s><u>з</u><u>з</u><u>з</u><u>з</u><u>з</u></div>
    </div>
</div>
</body>
</html>
"""


@pytest.fixture
def sample_html() -> str:
    """Return sample HTML schedule."""
    return SAMPLE_SCHEDULE_HTML


@pytest.fixture
def sample_schedule_data() -> ScheduleData:
    """Create sample schedule data for testing."""
    slots_group1 = []
    # Create 48 slots for group 1 based on the sample HTML pattern
    # Pattern: off, off, maybe, on, on, on, on, on, on, on, off, off...
    states = ["off", "off", "maybe", "on", "on", "on", "on", "on", "on", "on",
              "off", "off", "off", "off", "off", "off", "off", "off", "maybe", "on",
              "on", "on", "off", "off", "off", "off", "off", "off", "off", "off",
              "maybe", "on", "on", "on", "off", "off", "off", "off", "off", "off",
              "off", "off", "maybe", "on", "on", "on", "on", "on"]
    
    for i, state in enumerate(states):
        hour = i // 2
        minute = 30 if i % 2 else 0
        slots_group1.append(TimeSlot(hour=hour, minute=minute, state=state))
    
    group1 = GroupSchedule(
        group=1,
        date=date(2025, 12, 9),
        slots=slots_group1,
    )
    
    # Create simple schedule for group 12 (user's group)
    slots_group12 = []
    states_g12 = ["on", "on", "off", "off", "off", "off", "off", "off", "off", "off",
                  "maybe", "on", "on", "on", "on", "on", "on", "on", "off", "off",
                  "off", "off", "off", "off", "off", "off", "maybe", "on", "on", "on",
                  "on", "on", "on", "on", "off", "off", "off", "off", "off", "off",
                  "off", "off", "maybe", "on", "on", "on", "on", "on"]
    
    for i, state in enumerate(states_g12):
        hour = i // 2
        minute = 30 if i % 2 else 0
        slots_group12.append(TimeSlot(hour=hour, minute=minute, state=state))
    
    group12 = GroupSchedule(
        group=12,
        date=date(2025, 12, 9),
        slots=slots_group12,
    )
    
    return ScheduleData(
        date=date(2025, 12, 9),
        groups={1: group1, 12: group12},
        last_updated=datetime(2025, 12, 9, 9, 0, 0),
    )


@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {CONF_GROUP: 12}
    entry.options = {}
    entry.unique_id = "cv_oblenergo_group_12"
    return entry


@pytest.fixture
def mock_aiohttp_session():
    """Create a mock aiohttp session."""
    session = MagicMock()
    return session

