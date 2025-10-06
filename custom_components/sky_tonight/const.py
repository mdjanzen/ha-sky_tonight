"""Constants for the SkyTonight integration."""

from typing import Final

DOMAIN: Final = "sky_tonight"

DEFAULT_NAME: Final = "Sky Tonight"

SIGNAL_POSITION_CHANGED = f"{DOMAIN}_position_changed"
SIGNAL_EVENTS_CHANGED = f"{DOMAIN}_events_changed"


STATE_ABOVE_HORIZON = "above_horizon"
STATE_BELOW_HORIZON = "below_horizon"


STATE_ATTR_AZIMUTH = "azimuth"
STATE_ATTR_ELEVATION = "elevation"
STATE_ATTR_RISING = "rising"
STATE_ATTR_NEXT_RISING = "next_rising"
STATE_ATTR_NEXT_SETTING = "next_setting"


BODIES = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
]
AVAILABLE_BODIES = {
    "sun": "Sun",
    "moon": "Moon",
    "mercury": "Mercury",
    "venus": "Venus",
    "mars": "Mars",
    "jupiter": "Jupiter",
    "saturn": "Saturn",
    "uranus": "Uranus",
    "neptune": "Neptune",
    "pluto": "Pluto",
}

BODIES_DICT = {
    "sun": "SUN",
    "moon": "Moon",
    "mercury": "MERCURY BARYCENTER",
    "venus": "Venus BARYCENTER",
    "mars": "Mars BARYCENTER",
    "jupiter": "JUPITER BARYCENTER",
    "saturn": "SATURN BARYCENTER",
    "uranus": "URANUS BARYCENTER",
    "neptune": "NEPTUNE BARYCENTER",
    "pluto": "PLUTO BARYCENTER",
}

# 0 SOLAR SYSTEM BARYCENTER, 1 MERCURY BARYCENTER, 2 VENUS BARYCENTER, 3 EARTH BARYCENTER, 4 MARS BARYCENTER, 5 JUPITER BARYCENTER, 6 SATURN BARYCENTER, 7 URANUS BARYCENTER, 8 NEPTUNE BARYCENTER, 9 PLUTO BARYCENTER, 10 SUN, 199 MERCURY, 399 EARTH, 299 VENUS, 301 MOON, 499 MARS"
