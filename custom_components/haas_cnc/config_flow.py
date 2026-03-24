"""Config flow for HAAS CNC Machine Monitor.

Asks for the machine's IP/hostname, MTConnect agent port, MDC port,
and a friendly name.  Validates connectivity before creating the entry.
"""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HaasApiClient
from .const import (
    CONF_HOST,
    CONF_MACHINE_NAME,
    CONF_MDC_PORT,
    CONF_MTCONNECT_DEVICE,
    CONF_MTCONNECT_PORT,
    DEFAULT_MACHINE_NAME,
    DEFAULT_MDC_PORT,
    DEFAULT_MTCONNECT_DEVICE,
    DEFAULT_MTCONNECT_PORT,
    DOMAIN,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_MACHINE_NAME, default=DEFAULT_MACHINE_NAME): str,
        vol.Optional(CONF_MTCONNECT_PORT, default=DEFAULT_MTCONNECT_PORT): int,
        vol.Optional(CONF_MDC_PORT, default=DEFAULT_MDC_PORT): int,
        vol.Optional(CONF_MTCONNECT_DEVICE, default=DEFAULT_MTCONNECT_DEVICE): str,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_MTCONNECT_PORT): int,
        vol.Optional(CONF_MDC_PORT): int,
        vol.Optional(CONF_MTCONNECT_DEVICE): str,
    }
)


class HaasCncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HAAS CNC Machine Monitor."""

    VERSION = 2  # bumped – schema changed from MQTT to HTTP/TCP

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            mtconnect_port = user_input.get(CONF_MTCONNECT_PORT, DEFAULT_MTCONNECT_PORT)
            mdc_port = user_input.get(CONF_MDC_PORT, DEFAULT_MDC_PORT)
            device = user_input.get(CONF_MTCONNECT_DEVICE, DEFAULT_MTCONNECT_DEVICE)

            # Prevent duplicate entries with the same host
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            # Validate connection
            session = async_get_clientsession(self.hass)
            api = HaasApiClient(
                host=host,
                mtconnect_port=mtconnect_port,
                mdc_port=mdc_port,
                mtconnect_device=device,
                session=session,
            )
            success, source = await api.async_test_connection()

            if not success:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_MACHINE_NAME],
                    data=user_input,
                    description_placeholders={"source": source},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
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

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_MTCONNECT_PORT,
                        default=self.config_entry.data.get(
                            CONF_MTCONNECT_PORT, DEFAULT_MTCONNECT_PORT
                        ),
                    ): int,
                    vol.Optional(
                        CONF_MDC_PORT,
                        default=self.config_entry.data.get(
                            CONF_MDC_PORT, DEFAULT_MDC_PORT
                        ),
                    ): int,
                    vol.Optional(
                        CONF_MTCONNECT_DEVICE,
                        default=self.config_entry.data.get(
                            CONF_MTCONNECT_DEVICE, DEFAULT_MTCONNECT_DEVICE
                        ),
                    ): str,
                }
            ),
        )
