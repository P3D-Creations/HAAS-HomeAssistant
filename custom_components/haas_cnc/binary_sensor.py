"""Binary sensor platform for HAAS CNC Machine Monitor."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_DATA_SOURCE,
    ATTR_LAST_UPDATE,
    AVAIL_AVAILABLE,
    CONF_HOST,
    CONF_MACHINE_NAME,
    COORD_FAST,
    COORD_MEDIUM,
    DEFAULT_MACHINE_NAME,
    DOMAIN,
    EXECUTION_IDLE,
    KEY_ALARM,
    KEY_AVAIL,
    KEY_EXECUTION,
)
from .coordinator import HaasBaseCoordinator, _safe_get

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class HaasBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Extends BinarySensorEntityDescription with coordinator binding."""

    coordinator_key: str = COORD_FAST
    is_on_fn: Callable[[dict[str, Any]], bool | None] = lambda d: None


BINARY_SENSOR_DESCRIPTIONS: tuple[HaasBinarySensorEntityDescription, ...] = (
    HaasBinarySensorEntityDescription(
        key="available",
        name="Machine Available",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:lan-connect",
        coordinator_key=COORD_FAST,
        is_on_fn=lambda d: _safe_get(d, KEY_AVAIL) == AVAIL_AVAILABLE,
    ),
    HaasBinarySensorEntityDescription(
        key="running",
        name="Running",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:play",
        coordinator_key=COORD_FAST,
        is_on_fn=lambda d: (
            _safe_get(d, KEY_EXECUTION) not in (None, EXECUTION_IDLE, "IDLE", "READY", "STOPPED")
            and _safe_get(d, KEY_EXECUTION) is not None
        ),
    ),
    HaasBinarySensorEntityDescription(
        key="alarm_active",
        name="Alarm Active",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alarm-light-outline",
        coordinator_key=COORD_MEDIUM,
        is_on_fn=lambda d: (
            _safe_get(d, KEY_ALARM) is not None
            and str(_safe_get(d, KEY_ALARM, "")).strip() not in ("", "NONE", "CLEAR", "NORMAL")
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAAS CNC binary sensors from a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    machine_name: str = entry.data.get(CONF_MACHINE_NAME, DEFAULT_MACHINE_NAME)
    host: str = entry.data[CONF_HOST]

    coordinators: dict[str, HaasBaseCoordinator] = {
        COORD_FAST: entry_data[COORD_FAST],
        COORD_MEDIUM: entry_data[COORD_MEDIUM],
    }

    entities = [
        HaasCncBinarySensor(
            coordinator=coordinators[desc.coordinator_key],
            description=desc,
            machine_name=machine_name,
            host=host,
        )
        for desc in BINARY_SENSOR_DESCRIPTIONS
    ]
    async_add_entities(entities)


class HaasCncBinarySensor(CoordinatorEntity[HaasBaseCoordinator], BinarySensorEntity):
    """Representation of a HAAS CNC binary sensor."""

    entity_description: HaasBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HaasBaseCoordinator,
        description: HaasBinarySensorEntityDescription,
        machine_name: str,
        host: str,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._machine_name = machine_name
        self._host = host

        self._attr_unique_id = f"{host}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host)},
            name=machine_name,
            manufacturer="Haas Automation",
            model="UMC-500",
            sw_version="NGC",
        )

    @property
    def is_on(self) -> bool | None:
        """Return True when the condition is active."""
        if self.coordinator.data is None:
            return None
        try:
            return self.entity_description.is_on_fn(self.coordinator.data)
        except (KeyError, TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return state attributes."""
        attrs: dict[str, Any] = {}
        if self.coordinator.data:
            attrs[ATTR_DATA_SOURCE] = self.coordinator.data.get("_source", "unknown")
        if self.coordinator.last_update_success_time:
            attrs[ATTR_LAST_UPDATE] = self.coordinator.last_update_success_time.isoformat()
        return attrs
