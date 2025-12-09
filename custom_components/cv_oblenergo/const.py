"""Constants for Chernivtsi Power Schedule integration.

This is an UNOFFICIAL integration and is not affiliated with or endorsed by
the regional electricity company. Data is sourced from publicly available
schedule information.
"""

DOMAIN = "cv_oblenergo"

# Schedule URL (public data source)
SCHEDULE_URL = "https://oblenergo.cv.ua/shutdowns/"

# Power states
STATE_ON = "on"  # з - заживлені (powered)
STATE_OFF = "off"  # в - відключені (disconnected)
STATE_MAYBE = "maybe"  # мз - можливо заживлені (possibly powered)

# State translations for UI
STATE_TRANSLATIONS = {
    STATE_ON: "Electricity ON",
    STATE_OFF: "Electricity OFF",
    STATE_MAYBE: "Possibly ON",
}

STATE_TRANSLATIONS_UA = {
    STATE_ON: "Заживлено",
    STATE_OFF: "Відключено",
    STATE_MAYBE: "Можливо заживлено",
}

# HTML tag to state mapping
TAG_TO_STATE = {
    "u": STATE_ON,    # <u>з</u> - powered
    "o": STATE_OFF,  # <o>в</o> - disconnected
    "s": STATE_MAYBE,  # <s>мз</s> - maybe powered
}

# Number of groups
NUM_GROUPS = 12

# Number of time slots (48 = 24 hours * 2 half-hours)
NUM_SLOTS = 48

# Slot duration in minutes
SLOT_DURATION_MINUTES = 30

# Configuration keys
CONF_GROUP = "group"

# Default update interval (minutes)
DEFAULT_UPDATE_INTERVAL = 30

# Attribution
ATTRIBUTION = "Data from oblenergo.cv.ua (unofficial)"
