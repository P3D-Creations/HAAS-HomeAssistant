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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_LAST_UPDATE,
    ATTR_TOPIC_PREFIX,
    AVAIL_AVAILABLE,
    CONF_MACHINE_NAME,
    CONF_TOPIC_PREFIX,
    DEFAULT_MACHINE_NAME,
    DEFAULT_TOPIC_PREFIX,
    DOMAIN,
    EXECUTION_ACTIVE,
    EXECUTION_IDLE,
    TOPIC_ALARM,
    TOPIC_AVAIL,
    TOPIC_EXECUTION,
    UPDATE_GROUP_REALTIME,
)
from .coordinator import HaasDataCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class HaasBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Extends BinarySensorEntityDescription with HAAS-specific fields."""

    subtopic: str = ""
    update_group: str = UPDATE_GROUP_REALTIME
    # Returns True/False from raw MQTT payload string
    is_on_fn: Callable[[str | None], bool] = field(
        default_factory=lambda: lambda v: bool(v)
    )


BINARY_SENSOR_DESCRIPTIONS: list[HaasBinarySensorEntityDescription] = [
    HaasBinarySensorEntityDescription(
        key="available",
        subtopic=TOPIC_AVAIL,
        name="Machine Available",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:lan-connect",
        update_group=UPDATE_GROUP_REALTIME,
        is_on_fn=lambda v: v == AVAIL_AVAILABLE,
    ),
    HaasBinarySensorEntityDescription(
        key="running",
        subtopic=TOPIC_EXECUTION,
        name="Running",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:play",
        update_group=UPDATE_GROUP_REALTIME,
        is_on_fn=lambda v: v not in (None, EXECUTION_IDLE, "IDLE") and bool(v),
    ),
    HaasBinarySensorEntityDescription(
        key="alarm_active",
        subtopic=TOPIC_ALARM,
        name="Alarm Active",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alarm-light-outline",
        update_group=UPDATE_GROUP_REALTIME,
        is_on_fn=lambda v: bool(v) and v.strip() not in ("", "0", "NONE", "CLEAR"),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAAS CNC binary sensors from a config entry."""
    coordinator: HaasDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    machine_name: str = entry.data.get(CONF_MACHINE_NAME, DEFAULT_MACHINE_NAME)
    topic_prefix: str = entry.data.get(CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX)

    entities = [
        HaasCncBinarySensor(coordinator, description, machine_name, topic_prefix)
        for description in BINARY_SENSOR_DESCRIPTIONS
    ]
    async_add_entities(entities)


class HaasCncBinarySensor(BinarySensorEntity):
    """Representation of a HAAS CNC binary sensor."""

    entity_description: HaasBinarySensorEntityDescription
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: HaasDataCoordinator,
        description: HaasBinarySensorEntityDescription,
        machine_name: str,
        topic_prefix: str,
    ) -> None:
        """Initialise the binary sensor."""
        self.entity_description = description
        self._coordinator = coordinator
        self._machine_name = machine_name
        self._topic_prefix = topic_prefix
        self._unsubscribe: Callable[[], None] | None = None

        self._attr_unique_id = (
            f"{topic_prefix.rstrip('/')}_{description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, topic_prefix.rstrip("/"))},
            name=machine_name,
            manufacturer="Haas Automation",
            model="UMC-500",
            sw_version="NGC",
        )

    async def async_added_to_hass(self) -> None:
        """Register callback."""
        self._unsubscribe = self._coordinator.register_callback(
            self.entity_description.subtopic, self._handle_update
        )

    async def async_will_remove_from_hass(self) -> None:
        """Remove callback."""
        if self._unsubscribe:
            self._unsubscribe()

    @callback
    def _handle_update(self) -> None:
        """Push state update to HA."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return availability."""
        return self._coordinator.data.get(self.entity_description.subtopic) is not None

    @property
    def is_on(self) -> bool | None:
        """Return True when the condition represented is active."""
        raw = self._coordinator.get(self.entity_description.subtopic)
        try:
            return self.entity_description.is_on_fn(raw)
        except Exception:  # noqa: BLE001
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return state attributes."""
        attrs: dict[str, Any] = {ATTR_TOPIC_PREFIX: self._topic_prefix}
        if self._coordinator.last_update:
            attrs[ATTR_LAST_UPDATE] = self._coordinator.last_update.isoformat()
        return attrs
