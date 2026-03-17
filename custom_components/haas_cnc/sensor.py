"""Sensor platform for HAAS CNC Machine Monitor.

Each sensor maps to one MQTT sub-topic published by the
Haas MQTT MTConnect Adapter.  Sensors are grouped by update
frequency so future polling logic (if needed) can be targeted.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfLength,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_LAST_UPDATE,
    ATTR_TOPIC_PREFIX,
    CONF_MACHINE_NAME,
    CONF_TOPIC_PREFIX,
    DEFAULT_MACHINE_NAME,
    DEFAULT_TOPIC_PREFIX,
    DOMAIN,
    TOPIC_A_ACT,
    TOPIC_AIR_PRESSURE,
    TOPIC_ALARM,
    TOPIC_ALARM_CODE,
    TOPIC_B_ACT,
    TOPIC_COOLANT_LEVEL,
    TOPIC_CYCLE_TIME,
    TOPIC_EXECUTION,
    TOPIC_LOAD,
    TOPIC_MODE,
    TOPIC_PART_COUNT,
    TOPIC_PROGRAM,
    TOPIC_RUN_TIME,
    TOPIC_SPEED,
    TOPIC_TIMESTAMP,
    TOPIC_TOOL,
    TOPIC_TOOL_DIAMETER,
    TOPIC_TOOL_LENGTH,
    TOPIC_WORK_OFFSET,
    TOPIC_X_ACT,
    TOPIC_Y_ACT,
    TOPIC_Z_ACT,
    UPDATE_GROUP_REALTIME,
    UPDATE_GROUP_SLOW,
    UPDATE_GROUP_STANDARD,
)
from .coordinator import HaasDataCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class HaasSensorEntityDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with HAAS-specific fields."""

    subtopic: str = ""
    update_group: str = UPDATE_GROUP_REALTIME
    # Optional transform applied to raw MQTT payload before setting state
    value_fn: Callable[[str], Any] | None = None
    # Extra attributes added to the entity (lambdas receive coordinator)
    extra_attrs_fn: Callable[[HaasDataCoordinator], dict[str, Any]] | None = None


# ---------------------------------------------------------------------------
# Sensor descriptions
# Each entry maps directly to one MQTT subtopic.
# ---------------------------------------------------------------------------
SENSOR_DESCRIPTIONS: list[HaasSensorEntityDescription] = [
    # --- Program / Execution ---
    HaasSensorEntityDescription(
        key="execution",
        subtopic=TOPIC_EXECUTION,
        name="Execution State",
        icon="mdi:play-circle-outline",
        update_group=UPDATE_GROUP_REALTIME,
    ),
    HaasSensorEntityDescription(
        key="mode",
        subtopic=TOPIC_MODE,
        name="Operating Mode",
        icon="mdi:cog-outline",
        update_group=UPDATE_GROUP_REALTIME,
    ),
    HaasSensorEntityDescription(
        key="program",
        subtopic=TOPIC_PROGRAM,
        name="Active Program",
        icon="mdi:file-code-outline",
        update_group=UPDATE_GROUP_REALTIME,
    ),
    HaasSensorEntityDescription(
        key="part_count",
        subtopic=TOPIC_PART_COUNT,
        name="Part Count",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        update_group=UPDATE_GROUP_REALTIME,
        value_fn=lambda v: int(float(v)) if v else None,
    ),
    # --- Axis Positions ---
    HaasSensorEntityDescription(
        key="x_act",
        subtopic=TOPIC_X_ACT,
        name="X Position",
        icon="mdi:axis-x-arrow",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        update_group=UPDATE_GROUP_REALTIME,
        value_fn=lambda v: float(v) if v else None,
    ),
    HaasSensorEntityDescription(
        key="y_act",
        subtopic=TOPIC_Y_ACT,
        name="Y Position",
        icon="mdi:axis-y-arrow",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        update_group=UPDATE_GROUP_REALTIME,
        value_fn=lambda v: float(v) if v else None,
    ),
    HaasSensorEntityDescription(
        key="z_act",
        subtopic=TOPIC_Z_ACT,
        name="Z Position",
        icon="mdi:axis-z-arrow",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        update_group=UPDATE_GROUP_REALTIME,
        value_fn=lambda v: float(v) if v else None,
    ),
    HaasSensorEntityDescription(
        key="a_act",
        subtopic=TOPIC_A_ACT,
        name="A Axis Position",
        icon="mdi:rotate-3d-variant",
        native_unit_of_measurement="°",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        update_group=UPDATE_GROUP_REALTIME,
        value_fn=lambda v: float(v) if v else None,
    ),
    HaasSensorEntityDescription(
        key="b_act",
        subtopic=TOPIC_B_ACT,
        name="B Axis Position",
        icon="mdi:rotate-3d-variant",
        native_unit_of_measurement="°",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        update_group=UPDATE_GROUP_REALTIME,
        value_fn=lambda v: float(v) if v else None,
    ),
    # --- Spindle ---
    HaasSensorEntityDescription(
        key="speed",
        subtopic=TOPIC_SPEED,
        name="Spindle Speed",
        icon="mdi:rotate-right",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        update_group=UPDATE_GROUP_REALTIME,
        value_fn=lambda v: float(v) if v else None,
    ),
    HaasSensorEntityDescription(
        key="load",
        subtopic=TOPIC_LOAD,
        name="Spindle Load",
        icon="mdi:gauge",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        update_group=UPDATE_GROUP_REALTIME,
        value_fn=lambda v: float(v) if v else None,
    ),
    # --- Fluids / Environment ---
    HaasSensorEntityDescription(
        key="coolant_level",
        subtopic=TOPIC_COOLANT_LEVEL,
        name="Coolant Level",
        icon="mdi:water-percent",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        update_group=UPDATE_GROUP_REALTIME,
        value_fn=lambda v: float(v) if v else None,
    ),
    HaasSensorEntityDescription(
        key="air_pressure",
        subtopic=TOPIC_AIR_PRESSURE,
        name="Air Pressure",
        icon="mdi:air-filter",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        update_group=UPDATE_GROUP_REALTIME,
        value_fn=lambda v: float(v) if v else None,
    ),
    # --- Tool Information ---
    HaasSensorEntityDescription(
        key="tool",
        subtopic=TOPIC_TOOL,
        name="Tool in Spindle",
        icon="mdi:tools",
        update_group=UPDATE_GROUP_STANDARD,
        value_fn=lambda v: int(float(v)) if v else None,
    ),
    HaasSensorEntityDescription(
        key="tool_length",
        subtopic=TOPIC_TOOL_LENGTH,
        name="Tool Length Offset",
        icon="mdi:ruler",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        update_group=UPDATE_GROUP_STANDARD,
        value_fn=lambda v: float(v) if v else None,
    ),
    HaasSensorEntityDescription(
        key="tool_diameter",
        subtopic=TOPIC_TOOL_DIAMETER,
        name="Tool Diameter Offset",
        icon="mdi:diameter-variant",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        update_group=UPDATE_GROUP_STANDARD,
        value_fn=lambda v: float(v) if v else None,
    ),
    HaasSensorEntityDescription(
        key="work_offset",
        subtopic=TOPIC_WORK_OFFSET,
        name="Active Work Offset",
        icon="mdi:crosshairs-gps",
        update_group=UPDATE_GROUP_STANDARD,
    ),
    # --- Alarms ---
    HaasSensorEntityDescription(
        key="alarm",
        subtopic=TOPIC_ALARM,
        name="Alarm",
        icon="mdi:alarm-light",
        update_group=UPDATE_GROUP_REALTIME,
    ),
    HaasSensorEntityDescription(
        key="alarm_code",
        subtopic=TOPIC_ALARM_CODE,
        name="Alarm Code",
        icon="mdi:alert-circle-outline",
        update_group=UPDATE_GROUP_REALTIME,
    ),
    # --- Timing ---
    HaasSensorEntityDescription(
        key="cycle_time",
        subtopic=TOPIC_CYCLE_TIME,
        name="Cycle Time",
        icon="mdi:timer-outline",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        update_group=UPDATE_GROUP_REALTIME,
        value_fn=lambda v: float(v) if v else None,
    ),
    HaasSensorEntityDescription(
        key="run_time",
        subtopic=TOPIC_RUN_TIME,
        name="Run Time",
        icon="mdi:clock-start",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        update_group=UPDATE_GROUP_REALTIME,
        value_fn=lambda v: float(v) if v else None,
    ),
    # --- Raw timestamp from adapter ---
    HaasSensorEntityDescription(
        key="adapter_timestamp",
        subtopic=TOPIC_TIMESTAMP,
        name="Adapter Timestamp",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
        update_group=UPDATE_GROUP_REALTIME,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAAS CNC sensors from a config entry."""
    coordinator: HaasDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    machine_name: str = entry.data.get(CONF_MACHINE_NAME, DEFAULT_MACHINE_NAME)
    topic_prefix: str = entry.data.get(CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX)

    entities = [
        HaasCncSensor(coordinator, description, machine_name, topic_prefix)
        for description in SENSOR_DESCRIPTIONS
    ]
    async_add_entities(entities)


class HaasCncSensor(SensorEntity):
    """Representation of a HAAS CNC sensor entity."""

    entity_description: HaasSensorEntityDescription
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: HaasDataCoordinator,
        description: HaasSensorEntityDescription,
        machine_name: str,
        topic_prefix: str,
    ) -> None:
        """Initialise the sensor."""
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

    # ------------------------------------------------------------------
    # HA lifecycle
    # ------------------------------------------------------------------

    async def async_added_to_hass(self) -> None:
        """Register with the coordinator when added to HA."""
        self._unsubscribe = self._coordinator.register_callback(
            self.entity_description.subtopic, self._handle_update
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up subscription when removed."""
        if self._unsubscribe:
            self._unsubscribe()

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @callback
    def _handle_update(self) -> None:
        """Called by coordinator when our subtopic has a new value."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Entity is available when the coordinator has received at least one update."""
        return self._coordinator.data.get(self.entity_description.subtopic) is not None

    @property
    def native_value(self) -> Any:
        """Return the sensor value, applying optional transform."""
        raw = self._coordinator.get(self.entity_description.subtopic)
        if raw is None:
            return None
        try:
            if self.entity_description.value_fn:
                return self.entity_description.value_fn(raw)
            return raw
        except (ValueError, TypeError):
            _LOGGER.warning(
                "[%s] Could not parse value %r for %s",
                self._machine_name,
                raw,
                self.entity_description.key,
            )
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs: dict[str, Any] = {
            ATTR_TOPIC_PREFIX: self._topic_prefix,
        }
        if self._coordinator.last_update:
            attrs[ATTR_LAST_UPDATE] = self._coordinator.last_update.isoformat()
        if self.entity_description.extra_attrs_fn:
            attrs.update(self.entity_description.extra_attrs_fn(self._coordinator))
        return attrs
