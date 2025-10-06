"""The SkyTonight integration."""

from __future__ import annotations

import logging

from skyfield.api import load

from homeassistant.components.config import config_entries
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.typing import ConfigType

# The sensor platform is pre-imported here to ensure
# it gets loaded when the base component is loaded
# as we will always load it and we do not want to have
# to wait for the import executor when its busy later
# in the startup process.
from . import sensor as sensor_pre_import  # noqa: F401
from .const import (  # noqa: F401  # noqa: F401
    DOMAIN,
    STATE_ABOVE_HORIZON,
    STATE_BELOW_HORIZON,
)
from .entity import CelestialBody, SunConfigEntry

PLATFORMS = [Platform.SENSOR]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Track the state of the body."""
    if not hass.config_entries.async_entries(DOMAIN):
        # We avoid creating an import flow if its already
        # setup since it will have to import the config_flow
        # module.
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=config,
            )
        )
    eph = await hass.async_add_executor_job(load, "de421.bsp")
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["ephemeris"] = eph
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SunConfigEntry) -> bool:
    """Set up from a config entry."""
    bodies = entry.options.get("bodies", entry.data.get("bodies", ["sun"]))
    _LOGGER.info("Setting up Sky Tonight for: %s", bodies)
    celBodiesDict = {}

    for body in bodies:
        obj = CelestialBody(body, hass)
        celBodiesDict[body] = obj
        entry.async_on_unload(obj.remove_listeners)

    entry.runtime_data = celBodiesDict
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Trigger an immediate update for all bodies after reload
    for body in celBodiesDict.values():
        body.update_location(initial=True)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Handle options updates."""
    await hass.config_entries.async_reload(entry.entry_id)
