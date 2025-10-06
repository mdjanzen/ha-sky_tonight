"""Sensor platform for Sun integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
    RestoreSensor,
)
from homeassistant.const import DEGREE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import (
    DeviceEntryType,
    DeviceInfo,
    async_get as async_get_device_registry,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, SIGNAL_EVENTS_CHANGED, SIGNAL_POSITION_CHANGED
from .entity import CelestialBody, SunConfigEntry

ENTITY_ID_SENSOR_FORMAT = SENSOR_DOMAIN + ".sky_{}"


@dataclass(kw_only=True, frozen=True)
class SunSensorEntityDescription(SensorEntityDescription):
    """Describes a Sun sensor entity."""

    value_fn: Callable[[CelestialBody], StateType | datetime]
    signal: str


SENSOR_TYPES: tuple[SunSensorEntityDescription, ...] = (
    SunSensorEntityDescription(
        key="next_rising",
        device_class=SensorDeviceClass.TIMESTAMP,
        translation_key="next_rising",
        value_fn=lambda data: data.next_rising,
        signal=SIGNAL_EVENTS_CHANGED,
    ),
    SunSensorEntityDescription(
        key="next_setting",
        device_class=SensorDeviceClass.TIMESTAMP,
        translation_key="next_setting",
        value_fn=lambda data: data.next_setting,
        signal=SIGNAL_EVENTS_CHANGED,
    ),
    SunSensorEntityDescription(
        key="solar_elevation",
        translation_key="solar_elevation",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.solar_elevation,
        # entity_registry_enabled_default=False,
        native_unit_of_measurement=DEGREE,
        signal=SIGNAL_POSITION_CHANGED,
    ),
    SunSensorEntityDescription(
        key="solar_azimuth",
        translation_key="solar_azimuth",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.solar_azimuth,
        # entity_registry_enabled_default=False,
        native_unit_of_measurement=DEGREE,
        signal=SIGNAL_POSITION_CHANGED,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SunConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Sun sensor platform."""

    # Remove entities for bodies that are no longer selected
    bodies = list(entry.runtime_data.keys())
    cleanup_removed_bodies(hass, entry, bodies)

    sensors = []
    for body in entry.runtime_data.values():
        sensors.extend(
            [
                SunSensor(body, description, entry.entry_id)
                for description in SENSOR_TYPES
            ]
        )
    async_add_entities(sensors)


def cleanup_removed_bodies(hass, entry, current_bodies):
    """Remove entities and parent devices for bodies that are no longer selected."""
    entity_registry = async_get_entity_registry(hass)
    device_registry = async_get_device_registry(hass)
    valid_unique_ids = {
        f"{entry.entry_id}-{body}-{desc.key}"
        for body in current_bodies
        for desc in SENSOR_TYPES
    }
    # Remove entities
    for entity in list(entity_registry.entities.values()):
        if (
            entity.config_entry_id == entry.entry_id
            and entity.domain == "sensor"
            and entity.unique_id not in valid_unique_ids
        ):
            entity_registry.async_remove(entity.entity_id)
    # Remove devices with no entities
    for device in list(device_registry.devices.values()):
        if entry.entry_id in device.config_entries:
            # Check if device has any remaining entities
            device_entities = [
                e for e in entity_registry.entities.values() if e.device_id == device.id
            ]
            if not device_entities:
                device_registry.async_remove_device(device.id)


class SunSensor(RestoreSensor, SensorEntity):
    """Representation of a Sun Sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    entity_description: SunSensorEntityDescription

    def __init__(
        self,
        celBody: CelestialBody,
        entity_description: SunSensorEntityDescription,
        entry_id: str,
    ) -> None:
        """Initiate Sun Sensor."""
        self.entity_description = entity_description
        self.entity_id = ENTITY_ID_SENSOR_FORMAT.format(
            f"{celBody.object}-{entity_description.key}"
        )
        self._attr_unique_id = f"{entry_id}-{celBody.object}-{entity_description.key}"
        self.body = celBody
        self._attr_device_info = DeviceInfo(
            name=celBody.object,
            identifiers={(DOMAIN, f"{entry_id}-{celBody.object}")},
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> StateType | datetime:
        """Return value of sensor."""
        return self.entity_description.value_fn(self.body)

    async def async_added_to_hass(self) -> None:
        """Register signal listener and restore state when added to hass."""
        await super().async_added_to_hass()

        # Restore previous state if available
        if (last_state := await self.async_get_last_state()) is not None:
            # Only restore if the value is not already set by the body
            if self.native_value is None:
                self._attr_native_value = last_state.state

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self.entity_description.signal,
                self.async_write_ha_state,
            )
        )

    async def async_will_remove_from_hass(self) -> None:
        """Call when entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        # if self.entity_description.key == "solar_rising":
        #     async_delete_issue(self.hass, DOMAIN, "deprecated_sun_solar_rising")
