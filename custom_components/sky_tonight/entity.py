"""Support for functionality to keep track of the body."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from astral.location import Elevation, Location

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EVENT_CORE_CONFIG_UPDATE,
    SUN_EVENT_SUNRISE,
    SUN_EVENT_SUNSET,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers import event
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    SIGNAL_EVENTS_CHANGED,
    SIGNAL_POSITION_CHANGED,
    STATE_ABOVE_HORIZON,
    STATE_ATTR_AZIMUTH,
    STATE_ATTR_ELEVATION,
    STATE_ATTR_RISING,
    STATE_BELOW_HORIZON,
    STATE_ATTR_NEXT_RISING,
    STATE_ATTR_NEXT_SETTING,
)
from .skyfield_helper import (
    get_astral_event_next,
    get_astral_location,
    get_astral_position,
)

type SunConfigEntry = ConfigEntry[CelestialBody]

_LOGGER = logging.getLogger(__name__)


# As documented in wikipedia: https://en.wikipedia.org/wiki/Twilight
# body is:
# < -18° of horizon - all stars visible
PHASE_NIGHT = "night"
# 18°-12° - some stars not visible
PHASE_ASTRONOMICAL_TWILIGHT = "astronomical_twilight"
# 12°-6° - horizon visible
PHASE_NAUTICAL_TWILIGHT = "nautical_twilight"
# 6°-0° - objects visible
PHASE_TWILIGHT = "twilight"
# 0°-10° above horizon, body low on horizon
PHASE_SMALL_DAY = "small_day"
# > 10° above horizon
PHASE_DAY = "day"

# 4 mins is one degree of arc change of the body on its circle.
# During the night and the middle of the day we don't update
# that much since it's not important.
_PHASE_UPDATES = {
    PHASE_NIGHT: timedelta(minutes=4 * 5),
    PHASE_ASTRONOMICAL_TWILIGHT: timedelta(minutes=4 * 2),
    PHASE_NAUTICAL_TWILIGHT: timedelta(minutes=4),
    PHASE_TWILIGHT: timedelta(minutes=2),
    PHASE_SMALL_DAY: timedelta(minutes=2),
    PHASE_DAY: timedelta(minutes=4),
}


class CelestialBody(Entity):
    """Representation of the Sun."""

    _unrecorded_attributes = frozenset(
        {
            STATE_ATTR_AZIMUTH,
            STATE_ATTR_ELEVATION,
            STATE_ATTR_RISING,
            STATE_ATTR_NEXT_RISING,
            STATE_ATTR_NEXT_SETTING,
        }
    )

    location: Location
    elevation: Elevation
    next_rising: datetime
    next_setting: datetime
    solar_elevation: float
    solar_azimuth: float
    rising: bool
    _next_change: datetime

    def __init__(self, obj: str, hass: HomeAssistant) -> None:
        """Initialize the body."""
        self._attr_name = obj
        self.object = obj
        self.entity_id = "sky_tonight." + obj.lower()

        self.hass = hass
        self.phase: str | None = None

        # Initialize
        self.location = None
        self.elevation = None
        self.next_rising = None
        self.next_setting = None
        self.solar_elevation = None
        self.solar_azimuth = None
        self.rising = None
        self._next_change = None

        self._config_listener: CALLBACK_TYPE | None = None
        self._update_events_listener: CALLBACK_TYPE | None = None
        self._update_body_position_listener: CALLBACK_TYPE | None = None
        self._config_listener = self.hass.bus.async_listen(
            EVENT_CORE_CONFIG_UPDATE, self.update_location
        )

    async def async_added_to_hass(self) -> None:
        """Update after entity has been added."""
        await super().async_added_to_hass()
        self.update_location(initial=True)

    @callback
    def update_location(self, _: Event | None = None, initial: bool = False) -> None:
        """Update location."""
        location, elevation = get_astral_location(self.hass)
        if not initial and location == self.location:
            return
        self.location = location
        self.elevation = elevation
        if self._update_events_listener:
            self._update_events_listener()
        self.update_events()

    @callback
    def remove_listeners(self) -> None:
        """Remove listeners."""
        if self._config_listener:
            self._config_listener()
        if self._update_events_listener:
            self._update_events_listener()
        if self._update_body_position_listener:
            self._update_body_position_listener()

    @property
    def state(self) -> str:
        """Return the state of the body."""
        # 0.8333 is the same value as astral uses
        if self.solar_elevation > -0.833:
            return STATE_ABOVE_HORIZON

        return STATE_BELOW_HORIZON

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the body."""
        return {
            STATE_ATTR_NEXT_RISING: self.next_rising.isoformat(),
            STATE_ATTR_NEXT_SETTING: self.next_setting.isoformat(),
            STATE_ATTR_ELEVATION: self.solar_elevation,
            STATE_ATTR_AZIMUTH: self.solar_azimuth,
        }

    def _check_event(
        self, utc_point_in_time: datetime, event: str, before: str | None
    ) -> datetime:
        next_utc = get_astral_event_next(
            self.hass.data[DOMAIN]["ephemeris"],
            self.location,
            self.elevation,
            self.object,
            event,
            utc_point_in_time,
        )
        if next_utc < self._next_change:
            self._next_change = next_utc
            # self.phase = before
        return next_utc

    @callback
    def update_events(self, now: datetime | None = None) -> None:
        """Update the attributes containing solar events."""
        # Grab current time in case system clock changed since last time we ran.
        utc_point_in_time = dt_util.utcnow()
        self._next_change = utc_point_in_time + timedelta(days=400)

        self.next_rising = self._check_event(utc_point_in_time, SUN_EVENT_SUNRISE, None)
        self.next_setting = self._check_event(utc_point_in_time, SUN_EVENT_SUNSET, None)

        if self.phase is None:
            elevation = self.location.solar_elevation(self._next_change, self.elevation)
            if elevation >= 10:
                self.phase = PHASE_DAY
            elif elevation >= 0:
                self.phase = PHASE_SMALL_DAY
            elif elevation >= -6:
                self.phase = PHASE_TWILIGHT
            elif elevation >= -12:
                self.phase = PHASE_NAUTICAL_TWILIGHT
            elif elevation >= -18:
                self.phase = PHASE_ASTRONOMICAL_TWILIGHT
            else:
                self.phase = PHASE_NIGHT

        _LOGGER.debug(
            "body phase_update@%s: phase=%s", utc_point_in_time.isoformat(), self.phase
        )
        if self._update_body_position_listener:
            self._update_body_position_listener()
        self.update_body_position()
        async_dispatcher_send(self.hass, SIGNAL_EVENTS_CHANGED)

        # Set timer for the next solar event
        self._update_events_listener = event.async_track_point_in_utc_time(
            self.hass, self.update_events, self._next_change
        )
        _LOGGER.debug("next time: %s", self._next_change.isoformat())

    @callback
    def update_body_position(self, now: datetime | None = None) -> None:
        """Calculate the position of the body."""
        # Grab current time in case system clock changed since last time we ran.
        utc_point_in_time = dt_util.utcnow()

        self.solar_elevation, self.solar_azimuth = get_astral_position(
            self.hass.data[DOMAIN]["ephemeris"],
            self.location,
            self.elevation,
            self.object,
            utc_point_in_time,
        )

        _LOGGER.debug(
            "body position_update@%s: elevation=%s azimuth=%s",
            utc_point_in_time.isoformat(),
            self.solar_elevation,
            self.solar_azimuth,
        )
        self.async_write_ha_state()

        async_dispatcher_send(self.hass, SIGNAL_POSITION_CHANGED)

        # Next update as per the current phase
        assert self.phase
        delta = _PHASE_UPDATES[self.phase]
        # if the next update is within 1.25 of the next
        # position update just drop it
        if utc_point_in_time + delta * 1.25 > self._next_change:
            self._update_body_position_listener = None
            return
        self._update_body_position_listener = event.async_track_point_in_utc_time(
            self.hass, self.update_body_position, utc_point_in_time + delta
        )
