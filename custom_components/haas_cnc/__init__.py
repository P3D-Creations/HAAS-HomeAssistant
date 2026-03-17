"""HAAS CNC Machine Monitor – Home Assistant custom integration.

Entry point: sets up the MQTT coordinator, then forwards platform setup
to sensor and binary_sensor platforms.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_MACHINE_NAME,
    CONF_TOPIC_PREFIX,
    DEFAULT_MACHINE_NAME,
    DEFAULT_TOPIC_PREFIX,
    DOMAIN,
)
from .coordinator import HaasDataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HAAS CNC from a config entry."""
    topic_prefix: str = entry.data.get(CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX)
    machine_name: str = entry.data.get(CONF_MACHINE_NAME, DEFAULT_MACHINE_NAME)

    coordinator = HaasDataCoordinator(hass, topic_prefix, machine_name)

    # Subscribe to MQTT topics.  Raises if MQTT is not available.
    try:
        await coordinator.async_subscribe_all()
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady(
            f"Unable to subscribe to MQTT topics for {machine_name}: {err}"
        ) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Support options updates (e.g. changing topic prefix via the UI)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.info(
        "HAAS CNC integration loaded – machine: %s, prefix: %s",
        machine_name,
        topic_prefix,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: HaasDataCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_unsubscribe_all()

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update – reload the entry."""
    await hass.config_entries.async_reload(entry.entry_id)
