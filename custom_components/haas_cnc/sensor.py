"""Sensor platform for HAAS CNC Machine Monitor.

Each sensor is bound to a coordinator tier (fast / medium / slow) and
extracts its value from the coordinator's ``data`` dict via a
``value_fn`` lambda.  Entity descriptions are frozen dataclasses for
safety and clarity.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
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
    UnitOfSpeed,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_DATA_SOURCE,
    ATTR_LAST_UPDATE,
    CONF_HOST,
    CONF_MACHINE_NAME,
    COORD_FAST,
    COORD_MEDIUM,
    COORD_SLOW,
    DEFAULT_MACHINE_NAME,
    DOMAIN,
    KEY_A_ACT,
    KEY_ALARM,
    KEY_ALARM_CODE,
    KEY_B_ACT,
    KEY_BLOCK,
    KEY_COOLANT_LEVEL,
    KEY_CYCLE_TIME,
    KEY_EXECUTION,
    KEY_LINE,
    KEY_MODE,
    KEY_MODEL,
    KEY_MOTION_TIME,
    KEY_PART_COUNT,
    KEY_PATH_FEEDRATE,
    KEY_POWER_ON_TIME,
    KEY_PROGRAM,
    KEY_SERIAL,
    KEY_SOFTWARE_VERSION,
    KEY_SPINDLE_LOAD,
    KEY_SPINDLE_SPEED,
    KEY_TOOL_DIAMETER,
    KEY_TOOL_LENGTH,
    KEY_TOOL_NUMBER,
    KEY_WORK_OFFSET,
    KEY_X_ACT,
    KEY_Y_ACT,
    KEY_Z_ACT,
)
from .coordinator import HaasBaseCoordinator, _safe_get

_LOGGER = logging.getLogger(__name__)


# ======================================================================
# Entity description dataclass
# ======================================================================

@dataclass(frozen=True)
class HaasSensorEntityDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with coordinator binding."""

    coordinator_key: str = COORD_FAST
    value_fn: Callable[[dict[str, Any]], Any] = lambda d: None
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


# ======================================================================
# Sensor descriptions
# ======================================================================

SENSOR_DESCRIPTIONS: tuple[HaasSensorEntityDescription, ...] = (
    # ---- Fast tier: execution / positions / spindle ----
    HaasSensorEntityDescription(
        key="execution",
        name="Execution State",
        icon="mdi:play-circle-outline",
        coordinator_key=COORD_FAST,
        value_fn=lambda d: _safe_get(d, KEY_EXECUTION),
    ),
    HaasSensorEntityDescription(
        key="mode",
        name="Operating Mode",
        icon="mdi:cog-outline",
        coordinator_key=COORD_FAST,
        value_fn=lambda d: _safe_get(d, KEY_MODE),
    ),
    HaasSensorEntityDescription(
        key="program",
        name="Active Program",
        icon="mdi:file-code-outline",
        coordinator_key=COORD_FAST,
        value_fn=lambda d: _safe_get(d, KEY_PROGRAM),
    ),
    HaasSensorEntityDescription(
        key="block",
        name="Current Block",
        icon="mdi:code-braces",
        coordinator_key=COORD_FAST,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _safe_get(d, KEY_BLOCK),
    ),
    HaasSensorEntityDescription(
        key="line",
        name="Line Number",
        icon="mdi:format-list-numbered",
        coordinator_key=COORD_FAST,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _safe_get(d, KEY_LINE),
    ),
    # Axis positions
    HaasSensorEntityDescription(
        key="x_act",
        name="X Position",
        icon="mdi:axis-x-arrow",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        coordinator_key=COORD_FAST,
        value_fn=lambda d: _safe_get(d, KEY_X_ACT),
    ),
    HaasSensorEntityDescription(
        key="y_act",
        name="Y Position",
        icon="mdi:axis-y-arrow",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        coordinator_key=COORD_FAST,
        value_fn=lambda d: _safe_get(d, KEY_Y_ACT),
    ),
    HaasSensorEntityDescription(
        key="z_act",
        name="Z Position",
        icon="mdi:axis-z-arrow",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        coordinator_key=COORD_FAST,
        value_fn=lambda d: _safe_get(d, KEY_Z_ACT),
    ),
    HaasSensorEntityDescription(
        key="a_act",
        name="A Axis Position",
        icon="mdi:rotate-3d-variant",
        native_unit_of_measurement="°",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        coordinator_key=COORD_FAST,
        value_fn=lambda d: _safe_get(d, KEY_A_ACT),
    ),
    HaasSensorEntityDescription(
        key="b_act",
        name="B Axis Position",
        icon="mdi:rotate-3d-variant",
        native_unit_of_measurement="°",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        coordinator_key=COORD_FAST,
        value_fn=lambda d: _safe_get(d, KEY_B_ACT),
    ),
    # Spindle
    HaasSensorEntityDescription(
        key="spindle_speed",
        name="Spindle Speed",
        icon="mdi:rotate-right",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        coordinator_key=COORD_FAST,
        value_fn=lambda d: _safe_get(d, KEY_SPINDLE_SPEED),
    ),
    HaasSensorEntityDescription(
        key="spindle_load",
        name="Spindle Load",
        icon="mdi:gauge",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        coordinator_key=COORD_FAST,
        value_fn=lambda d: _safe_get(d, KEY_SPINDLE_LOAD),
    ),
    HaasSensorEntityDescription(
        key="path_feedrate",
        name="Path Feedrate",
        icon="mdi:speedometer",
        native_unit_of_measurement="mm/min",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        coordinator_key=COORD_FAST,
        value_fn=lambda d: _safe_get(d, KEY_PATH_FEEDRATE),
    ),

    # ---- Medium tier: tool / offsets / part count / alarms ----
    HaasSensorEntityDescription(
        key="tool_number",
        name="Tool in Spindle",
        icon="mdi:tools",
        coordinator_key=COORD_MEDIUM,
        value_fn=lambda d: _safe_get(d, KEY_TOOL_NUMBER),
    ),
    HaasSensorEntityDescription(
        key="tool_length",
        name="Tool Length Offset",
        icon="mdi:ruler",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        coordinator_key=COORD_MEDIUM,
        value_fn=lambda d: _safe_get(d, KEY_TOOL_LENGTH),
    ),
    HaasSensorEntityDescription(
        key="tool_diameter",
        name="Tool Diameter Offset",
        icon="mdi:diameter-variant",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        coordinator_key=COORD_MEDIUM,
        value_fn=lambda d: _safe_get(d, KEY_TOOL_DIAMETER),
    ),
    HaasSensorEntityDescription(
        key="work_offset",
        name="Active Work Offset",
        icon="mdi:crosshairs-gps",
        coordinator_key=COORD_MEDIUM,
        value_fn=lambda d: _safe_get(d, KEY_WORK_OFFSET),
    ),
    HaasSensorEntityDescription(
        key="part_count",
        name="Part Count",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        coordinator_key=COORD_MEDIUM,
        value_fn=lambda d: _safe_get(d, KEY_PART_COUNT),
    ),
    HaasSensorEntityDescription(
        key="coolant_level",
        name="Coolant Level",
        icon="mdi:water-percent",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        coordinator_key=COORD_MEDIUM,
        value_fn=lambda d: _safe_get(d, KEY_COOLANT_LEVEL),
    ),
    HaasSensorEntityDescription(
        key="alarm",
        name="Alarm",
        icon="mdi:alarm-light",
        coordinator_key=COORD_MEDIUM,
        value_fn=lambda d: _safe_get(d, KEY_ALARM),
    ),
    HaasSensorEntityDescription(
        key="alarm_code",
        name="Alarm Code",
        icon="mdi:alert-circle-outline",
        coordinator_key=COORD_MEDIUM,
        value_fn=lambda d: _safe_get(d, KEY_ALARM_CODE),
    ),

    # ---- Slow tier: machine identity / accumulated times ----
    HaasSensorEntityDescription(
        key="serial_number",
        name="Serial Number",
        icon="mdi:identifier",
        coordinator_key=COORD_SLOW,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _safe_get(d, KEY_SERIAL),
    ),
    HaasSensorEntityDescription(
        key="model",
        name="Model",
        icon="mdi:factory",
        coordinator_key=COORD_SLOW,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _safe_get(d, KEY_MODEL),
    ),
    HaasSensorEntityDescription(
        key="software_version",
        name="Software Version",
        icon="mdi:chip",
        coordinator_key=COORD_SLOW,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _safe_get(d, KEY_SOFTWARE_VERSION),
    ),
    HaasSensorEntityDescription(
        key="power_on_time",
        name="Power-On Time",
        icon="mdi:clock-start",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        coordinator_key=COORD_SLOW,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _safe_get(d, KEY_POWER_ON_TIME),
    ),
    HaasSensorEntityDescription(
        key="motion_time",
        name="Motion Time",
        icon="mdi:timer-outline",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        coordinator_key=COORD_SLOW,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _safe_get(d, KEY_MOTION_TIME),
    ),
    HaasSensorEntityDescription(
        key="cycle_time",
        name="Cycle Time",
        icon="mdi:timer-outline",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        coordinator_key=COORD_SLOW,
        value_fn=lambda d: _safe_get(d, KEY_CYCLE_TIME),
    ),
)


# ======================================================================
# Platform setup
# ======================================================================

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAAS CNC sensors from a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    machine_name: str = entry.data.get(CONF_MACHINE_NAME, DEFAULT_MACHINE_NAME)
    host: str = entry.data[CONF_HOST]

    coordinators: dict[str, HaasBaseCoordinator] = {
        COORD_FAST: entry_data[COORD_FAST],
        COORD_MEDIUM: entry_data[COORD_MEDIUM],
        COORD_SLOW: entry_data[COORD_SLOW],
    }

    entities = [
        HaasCncSensor(
            coordinator=coordinators[desc.coordinator_key],
            description=desc,
            machine_name=machine_name,
            host=host,
        )
        for desc in SENSOR_DESCRIPTIONS
    ]
    async_add_entities(entities)


# ======================================================================
# Sensor entity
# ======================================================================

class HaasCncSensor(CoordinatorEntity[HaasBaseCoordinator], SensorEntity):
    """Representation of a HAAS CNC sensor entity."""

    entity_description: HaasSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HaasBaseCoordinator,
        description: HaasSensorEntityDescription,
        machine_name: str,
        host: str,
    ) -> None:
        """Initialise the sensor."""
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
    def native_value(self) -> Any:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        try:
            return self.entity_description.value_fn(self.coordinator.data)
        except (KeyError, TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs: dict[str, Any] = {}
        if self.coordinator.data:
            attrs[ATTR_DATA_SOURCE] = self.coordinator.data.get("_source", "unknown")
        if self.coordinator.last_update_success_time:
            attrs[ATTR_LAST_UPDATE] = self.coordinator.last_update_success_time.isoformat()
        if self.entity_description.attributes_fn and self.coordinator.data:
            attrs.update(self.entity_description.attributes_fn(self.coordinator.data))
        return attrs
