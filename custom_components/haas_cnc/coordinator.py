"""MQTT Data Coordinator for HAAS CNC integration.

Subscribes to all relevant MQTT topics published by the
Haas MQTT MTConnect Adapter and stores the latest values.
Entities register callbacks here to receive live updates
without polling.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback

from .const import (
    DOMAIN,
    TOPIC_AVAIL,
    TOPIC_MODE,
    TOPIC_EXECUTION,
    TOPIC_PROGRAM,
    TOPIC_PART_COUNT,
    TOPIC_X_ACT,
    TOPIC_Y_ACT,
    TOPIC_Z_ACT,
    TOPIC_POSITION,
    TOPIC_SPEED,
    TOPIC_COOLANT_LEVEL,
    TOPIC_LOAD,
    TOPIC_TOOL,
    TOPIC_TIMESTAMP,
    TOPIC_ALARM,
    TOPIC_ALARM_CODE,
    TOPIC_A_ACT,
    TOPIC_B_ACT,
    TOPIC_TOOL_LENGTH,
    TOPIC_TOOL_DIAMETER,
    TOPIC_WORK_OFFSET,
    TOPIC_AIR_PRESSURE,
    TOPIC_CYCLE_TIME,
    TOPIC_RUN_TIME,
    AVAIL_AVAILABLE,
)

_LOGGER = logging.getLogger(__name__)

# All sub-topics the coordinator subscribes to
ALL_TOPICS = [
    TOPIC_AVAIL,
    TOPIC_MODE,
    TOPIC_EXECUTION,
    TOPIC_PROGRAM,
    TOPIC_PART_COUNT,
    TOPIC_X_ACT,
    TOPIC_Y_ACT,
    TOPIC_Z_ACT,
    TOPIC_POSITION,
    TOPIC_SPEED,
    TOPIC_COOLANT_LEVEL,
    TOPIC_LOAD,
    TOPIC_TOOL,
    TOPIC_TIMESTAMP,
    TOPIC_ALARM,
    TOPIC_ALARM_CODE,
    TOPIC_A_ACT,
    TOPIC_B_ACT,
    TOPIC_TOOL_LENGTH,
    TOPIC_TOOL_DIAMETER,
    TOPIC_WORK_OFFSET,
    TOPIC_AIR_PRESSURE,
    TOPIC_CYCLE_TIME,
    TOPIC_RUN_TIME,
]


class HaasDataCoordinator:
    """Central coordinator for HAAS machine data via MQTT.

    All sensor and binary_sensor entities register a callback with this
    coordinator.  When a matching MQTT message arrives the coordinator
    stores the value and invokes the registered callbacks so entities can
    update their state without any polling.
    """

    def __init__(self, hass: HomeAssistant, topic_prefix: str, machine_name: str) -> None:
        """Initialise the coordinator."""
        self.hass = hass
        self.topic_prefix = topic_prefix
        self.machine_name = machine_name

        # Live data store  {subtopic: value}
        self.data: dict[str, str | None] = {t: None for t in ALL_TOPICS}
        self.last_update: datetime | None = None

        # Subscriber callbacks  {subtopic: [callback, ...]}
        self._subscribers: dict[str, list[Callable[[], None]]] = {
            t: [] for t in ALL_TOPICS
        }
        # Catch-all subscribers notified on every update
        self._global_subscribers: list[Callable[[], None]] = []

        # MQTT unsubscribe handles
        self._unsubscribe_handles: list[Callable[[], None]] = []

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    async def async_subscribe_all(self) -> None:
        """Subscribe to all MQTT sub-topics."""
        for subtopic in ALL_TOPICS:
            full_topic = f"{self.topic_prefix}{subtopic}"
            _LOGGER.debug("[%s] Subscribing to %s", self.machine_name, full_topic)

            # Closure captures the subtopic for each loop iteration
            async def _handle_message(
                msg: mqtt.ReceiveMessage, _subtopic: str = subtopic
            ) -> None:
                self._handle_mqtt(msg, _subtopic)

            handle = await mqtt.async_subscribe(
                self.hass, full_topic, _handle_message, qos=0
            )
            self._unsubscribe_handles.append(handle)

    async def async_unsubscribe_all(self) -> None:
        """Unsubscribe from all MQTT topics (called on integration unload)."""
        for handle in self._unsubscribe_handles:
            handle()
        self._unsubscribe_handles.clear()

    # ------------------------------------------------------------------
    # Entity registration
    # ------------------------------------------------------------------

    def register_callback(
        self, subtopic: str, cb: Callable[[], None]
    ) -> Callable[[], None]:
        """Register *cb* to be called when *subtopic* receives a new value.

        Returns an unregister function for use in async_will_remove_from_hass.
        """
        self._subscribers.setdefault(subtopic, []).append(cb)

        def _remove() -> None:
            self._subscribers[subtopic].remove(cb)

        return _remove

    def register_global_callback(self, cb: Callable[[], None]) -> Callable[[], None]:
        """Register *cb* to be called on every data update."""
        self._global_subscribers.append(cb)

        def _remove() -> None:
            self._global_subscribers.remove(cb)

        return _remove

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @callback
    def _handle_mqtt(self, msg: mqtt.ReceiveMessage, subtopic: str) -> None:
        """Handle an incoming MQTT message."""
        payload = msg.payload
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", errors="replace")

        _LOGGER.debug(
            "[%s] MQTT %s -> %r", self.machine_name, subtopic, payload
        )

        self.data[subtopic] = payload.strip() if payload else None
        self.last_update = datetime.now()

        # Notify topic-specific subscribers
        for cb in list(self._subscribers.get(subtopic, [])):
            cb()

        # Notify global subscribers
        for cb in list(self._global_subscribers):
            cb()

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def get(self, subtopic: str, default: str | None = None) -> str | None:
        """Return the current value for *subtopic*."""
        return self.data.get(subtopic, default)

    @property
    def is_available(self) -> bool:
        """Return True when the machine reports AVAILABLE."""
        return self.data.get(TOPIC_AVAIL) == AVAIL_AVAILABLE

    @property
    def execution(self) -> str | None:
        """Return the current execution state."""
        return self.data.get(TOPIC_EXECUTION)

    @property
    def program(self) -> str | None:
        """Return the currently loaded program name."""
        return self.data.get(TOPIC_PROGRAM)
