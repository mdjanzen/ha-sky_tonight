from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import OptionsFlowWithReload
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, AVAILABLE_BODIES

_LOGGER = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────
#  CONFIG FLOW
# ───────────────────────────────────────────────────────────────
class SkyTonightConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow for Sky Tonight."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        """Handle the initial setup step."""
        if user_input is not None:
            # Save initial selection into entry.data
            return self.async_create_entry(title="Sky Tonight", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    "bodies",
                    default=[
                        "mercury",
                        "venus",
                        "mars",
                        "jupiter",
                        "saturn",
                    ],
                ): cv.multi_select(AVAILABLE_BODIES)
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={
                "info": "Select which celestial bodies to track."
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow handler."""
        return SkyTonightOptionsFlowHandler()


# ───────────────────────────────────────────────────────────────
#  OPTIONS FLOW (gear icon)
# ───────────────────────────────────────────────────────────────
class SkyTonightOptionsFlowHandler(OptionsFlowWithReload):
    """Handle options flow when user clicks the gear icon."""

    # def __init__(self, config_entry: config_entries.ConfigEntry):
    #    """Initialize the options flow."""
    #    self.config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            # Save new options
            return self.async_create_entry(title="", data=user_input)

        # Use current options or fallback to original data
        current = self.config_entry.options.get(
            "bodies",
            self.config_entry.data.get(
                "bodies",
                [
                    "mercury",
                    "venus",
                    "mars",
                    "jupiter",
                    "saturn",
                ],
            ),
        )

        schema = vol.Schema(
            {vol.Required("bodies", default=current): cv.multi_select(AVAILABLE_BODIES)}
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "info": "Update which celestial bodies you want to track."
            },
        )
