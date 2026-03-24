"""Data coordinators for HAAS CNC integration.

Three ``DataUpdateCoordinator`` tiers fetch machine data at different
intervals through the unified ``HaasApiClient``:

  - **Fast**  (~2 s): execution state, axis positions, spindle, feedrate
  - **Medium** (~10 s): tool info, work offset, part count, alarms, mode
  - **Slow**  (~600 s): serial number, model, software version, accum. times
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HaasApiClient
from .const import (
    COORD_FAST,
    COORD_MEDIUM,
    COORD_SLOW,
    DOMAIN,
    UPDATE_INTERVAL_FAST,
    UPDATE_INTERVAL_MEDIUM,
    UPDATE_INTERVAL_SLOW,
)

_LOGGER = logging.getLogger(__name__)

# Retry MTConnect every N slow-tier cycles (600 s × 5 = ~50 min)
_MTCONNECT_RETRY_CYCLES = 5


# ======================================================================
# Safe accessor for entity value_fn lambdas
# ======================================================================

def _safe_get(data: dict[str, Any] | None, key: str, default: Any = None) -> Any:
    """Safely retrieve a key from coordinator data, returning *default* on failure."""
    if data is None:
        return default
    return data.get(key, default)


# ======================================================================
# Base coordinator
# ======================================================================

class HaasBaseCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Base class with shared helpers."""

    coordinator_key: str  # overridden in subclasses

    def __init__(
        self,
        hass: HomeAssistant,
        api: HaasApiClient,
        name: str,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{name}",
            update_interval=update_interval,
        )
        self.api = api

    def get(self, key: str, default: Any = None) -> Any:
        """Convenience accessor for entity descriptions."""
        return _safe_get(self.data, key, default)


# ======================================================================
# Fast coordinator  (~2 s)
# ======================================================================

class HaasFastCoordinator(HaasBaseCoordinator):
    """Polls positions, spindle, execution state."""

    coordinator_key = COORD_FAST

    def __init__(self, hass: HomeAssistant, api: HaasApiClient, machine: str) -> None:
        super().__init__(
            hass, api, f"{machine}_fast",
            timedelta(seconds=UPDATE_INTERVAL_FAST),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.async_get_fast_data()
        except Exception as err:
            raise UpdateFailed(f"Fast data update failed: {err}") from err


# ======================================================================
# Medium coordinator  (~10 s)
# ======================================================================

class HaasMediumCoordinator(HaasBaseCoordinator):
    """Polls tool info, work offset, part count, alarms."""

    coordinator_key = COORD_MEDIUM

    def __init__(self, hass: HomeAssistant, api: HaasApiClient, machine: str) -> None:
        super().__init__(
            hass, api, f"{machine}_medium",
            timedelta(seconds=UPDATE_INTERVAL_MEDIUM),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.async_get_medium_data()
        except Exception as err:
            raise UpdateFailed(f"Medium data update failed: {err}") from err


# ======================================================================
# Slow coordinator  (~600 s)
# ======================================================================

class HaasSlowCoordinator(HaasBaseCoordinator):
    """Polls machine identity and accumulated times.

    Also periodically retries MTConnect if it was down.
    """

    coordinator_key = COORD_SLOW

    def __init__(self, hass: HomeAssistant, api: HaasApiClient, machine: str) -> None:
        super().__init__(
            hass, api, f"{machine}_slow",
            timedelta(seconds=UPDATE_INTERVAL_SLOW),
        )
        self._cycle = 0

    async def _async_update_data(self) -> dict[str, Any]:
        # Periodically retry MTConnect
        self._cycle += 1
        if self._cycle % _MTCONNECT_RETRY_CYCLES == 0:
            await self.api.async_retry_mtconnect()

        try:
            return await self.api.async_get_slow_data()
        except Exception as err:
            raise UpdateFailed(f"Slow data update failed: {err}") from err
