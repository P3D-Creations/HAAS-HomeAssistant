"""Config flow for HAAS CNC Machine Monitor."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import mqtt
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_MACHINE_NAME,
    CONF_TOPIC_PREFIX,
    DEFAULT_MACHINE_NAME,
    DEFAULT_TOPIC_PREFIX,
    DOMAIN,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MACHINE_NAME, default=DEFAULT_MACHINE_NAME): str,
        vol.Required(CONF_TOPIC_PREFIX, default=DEFAULT_TOPIC_PREFIX): str,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOPIC_PREFIX): str,
    }
)


class HaasCncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HAAS CNC Machine Monitor."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Verify MQTT is available
            if not await mqtt.async_wait_for_mqtt_client(self.hass):
                errors["base"] = "mqtt_not_available"
            else:
                # Prevent duplicate entries with the same topic prefix
                await self.async_set_unique_id(
                    user_input[CONF_TOPIC_PREFIX].rstrip("/")
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_MACHINE_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "default_prefix": DEFAULT_TOPIC_PREFIX,
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HaasCncOptionsFlow:
        """Return the options flow handler."""
        return HaasCncOptionsFlow(config_entry)


class HaasCncOptionsFlow(config_entries.OptionsFlow):
    """Handle an options flow for HAAS CNC Machine Monitor."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialise options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_prefix = self.config_entry.data.get(
            CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TOPIC_PREFIX, default=current_prefix): str,
                }
            ),
        )
