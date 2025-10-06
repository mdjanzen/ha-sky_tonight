"""Helpers for sun events."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

from skyfield.almanac import find_risings, find_settings
from skyfield.api import Topos, load

from homeassistant.const import SUN_EVENT_SUNRISE, SUN_EVENT_SUNSET
from homeassistant.core import HomeAssistant, callback
from homeassistant.loader import bind_hass
from homeassistant.util.hass_dict import HassKey

from .const import BODIES_DICT

if TYPE_CHECKING:
    import astral
    import astral.location

DATA_LOCATION_CACHE: HassKey[
    dict[tuple[str, str, str, float, float], astral.location.Location]
] = HassKey("astral_location_cache")


@callback
@bind_hass
def get_astral_location(
    hass: HomeAssistant,
) -> tuple[astral.location.Location, astral.Elevation]:
    """Get an astral location for the current Home Assistant configuration."""
    from astral import LocationInfo  # noqa: PLC0415
    from astral.location import Location  # noqa: PLC0415

    latitude = hass.config.latitude
    longitude = hass.config.longitude
    timezone = str(hass.config.time_zone)
    elevation = hass.config.elevation
    info = ("", "", timezone, latitude, longitude)

    # Cache astral locations so they aren't recreated with the same args
    if DATA_LOCATION_CACHE not in hass.data:
        hass.data[DATA_LOCATION_CACHE] = {}

    if info not in hass.data[DATA_LOCATION_CACHE]:
        hass.data[DATA_LOCATION_CACHE][info] = Location(LocationInfo(*info))

    return hass.data[DATA_LOCATION_CACHE][info], elevation


@callback
@bind_hass
def get_astral_event_next(
    eph: Any,
    location: astral.location.Location,
    elevation: astral.Elevation,
    celestial_object: str,
    event: str,
    utc_point_in_time: datetime.datetime | None = None,
    offset: datetime.timedelta | None = None,
) -> datetime.datetime:
    """Get the next rising or setting event time for a celestial object at a given location.

    Args:
        eph: The ephemeris data containing celestial objects.
        location: The observer's location as an astral Location.
        elevation: The observer's elevation above sea level.
        celestial_object: The name of the celestial object to observe.
        event: The event type, either SUN_EVENT_SUNRISE or SUN_EVENT_SUNSET.
        utc_point_in_time: The UTC datetime to start searching from.
        offset: An optional time offset to apply.

    Returns:
        The UTC datetime of the next specified event for the celestial object.
    """
    # Load the ephemeris and timescale

    # eph = hass.data[DOMAIN]["ephemeris"]
    ts = load.timescale()

    earth = eph["earth"]
    # Define your observer's location (latitude, longitude, elevation)
    # Replace with your actual coordinates
    observer = earth + Topos(
        location.latitude, location.longitude, elevation_m=elevation
    )

    # Define the time range for your search
    # For example, search for settings within a specific day
    t0 = ts.utc(utc_point_in_time)  # Start of the day
    t1 = ts.utc(utc_point_in_time + datetime.timedelta(days=2))

    # Find the setting times of Mars
    # The find_settings function returns a tuple of (times, events)
    # where events indicate the type of event (0 for setting)
    if event == SUN_EVENT_SUNRISE:
        times, events = find_risings(
            observer, eph[BODIES_DICT[celestial_object]], t0, t1
        )
    elif event == SUN_EVENT_SUNSET:
        times, events = find_settings(
            observer, eph[BODIES_DICT[celestial_object]], t0, t1
        )
    else:
        raise ValueError("Unsupported event type")

    if not times or times[0] is None:
        return datetime.datetime.now(datetime.UTC)
    return times[0].utc_datetime()


@callback
@bind_hass
def get_astral_position(
    eph: Any,
    location: astral.location.Location,
    elevation: astral.Elevation,
    celestial_object: str,
    utc_point_in_time: datetime.datetime | None = None,
    offset: datetime.timedelta | None = None,
) -> datetime.datetime:
    """Calculate the altitude and azimuth of a celestial object for a given location and time.

    Args:
        eph: The ephemeris data containing celestial objects.
        location: The observer's location as an astral Location.
        elevation: The observer's elevation above sea level.
        celestial_object: The name of the celestial object to observe.
        utc_point_in_time: The UTC datetime for which to calculate the position (optional).
        offset: An optional time offset to apply.

    Returns:
        A tuple containing the altitude and azimuth of the celestial object.
    """
    # Load the ephemeris and timescale

    # eph = hass.data[DOMAIN]["ephemeris"]
    ts = load.timescale()
    t = ts.now()

    earth = eph["earth"]
    # Define your observer's location (latitude, longitude, elevation)
    # Replace with your actual coordinates
    observer = Topos(location.latitude, location.longitude, elevation_m=elevation)
    apparent = (
        (earth + observer).at(t).observe(eph[BODIES_DICT[celestial_object]]).apparent()
    )

    alt, az, distance = apparent.altaz()

    return (
        round(alt.degrees, 0),
        round(az.degrees, 0),
    )
