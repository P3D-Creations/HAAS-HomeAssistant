"""HAAS CNC Machine Monitor – Home Assistant custom integration.

Entry point: creates the unified API client, spins up three
``DataUpdateCoordinator`` tiers (fast / medium / slow), then
forwards platform setup to sensor and binary_sensor.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HaasApiClient
from .const import (
    CONF_HOST,
    CONF_MACHINE_NAME,
    CONF_MDC_PORT,
    CONF_MTCONNECT_DEVICE,
    CONF_MTCONNECT_PORT,
    COORD_FAST,
    COORD_MEDIUM,
    COORD_SLOW,
    DEFAULT_MACHINE_NAME,
    DEFAULT_MDC_PORT,
    DEFAULT_MTCONNECT_DEVICE,
    DEFAULT_MTCONNECT_PORT,
    DOMAIN,
)
from .coordinator import (
    HaasFastCoordinator,
    HaasMediumCoordinator,
    HaasSlowCoordinator,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HAAS CNC from a config entry."""
    host: str = entry.data[CONF_HOST]
    machine_name: str = entry.data.get(CONF_MACHINE_NAME, DEFAULT_MACHINE_NAME)
    mtconnect_port: int = entry.data.get(CONF_MTCONNECT_PORT, DEFAULT_MTCONNECT_PORT)
    mdc_port: int = entry.data.get(CONF_MDC_PORT, DEFAULT_MDC_PORT)
    mtconnect_device: str = entry.data.get(CONF_MTCONNECT_DEVICE, DEFAULT_MTCONNECT_DEVICE)

    session = async_get_clientsession(hass)
    api = HaasApiClient(
        host=host,
        mtconnect_port=mtconnect_port,
        mdc_port=mdc_port,
        mtconnect_device=mtconnect_device,
        session=session,
    )

    # Validate connectivity
    success, source = await api.async_test_connection()
    if not success:
        raise ConfigEntryNotReady(
            f"Cannot reach HAAS machine at {host} "
            f"(tried MTConnect :{mtconnect_port} and MDC :{mdc_port})"
        )
    _LOGGER.info(
        "Connected to %s at %s via %s", machine_name, host, source,
    )

    # Create coordinator tiers
    fast_coord = HaasFastCoordinator(hass, api, machine_name)
    medium_coord = HaasMediumCoordinator(hass, api, machine_name)
    slow_coord = HaasSlowCoordinator(hass, api, machine_name)

    # Initial refresh – raises UpdateFailed → ConfigEntryNotReady
    await fast_coord.async_config_entry_first_refresh()
    await medium_coord.async_config_entry_first_refresh()
    await slow_coord.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        COORD_FAST: fast_coord,
        COORD_MEDIUM: medium_coord,
        COORD_SLOW: slow_coord,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.info(
        "HAAS CNC integration loaded – machine: %s, host: %s, source: %s",
        machine_name, host, source,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        api: HaasApiClient = entry_data["api"]
        await api.close()

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update – reload the entry."""
    await hass.config_entries.async_reload(entry.entry_id)
