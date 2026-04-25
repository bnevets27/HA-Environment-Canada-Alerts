"""Config flow for Environment Canada Weather Alerts."""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse, parse_qs

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, CONF_ZONE_CODE, CONF_FRIENDLY_NAME, CONF_REGION_NAME
from .ec_api import fetch_ec_alerts

_LOGGER = logging.getLogger(__name__)

# Regex: valid EC zone codes like "nl18", "onrm96_e", "abcn11", "bccn10_e", etc.
ZONE_CODE_RE = re.compile(r"^[a-z]{2,6}[a-z0-9_]{2,20}$", re.I)


def _extract_zone_code(user_input: str) -> str:
    """Extract zone code from user input (could be a URL or raw zone code)."""
    user_input = user_input.strip()

    # If the user pasted a full URL like:
    # https://weather.gc.ca/warnings/report_e.html?nl18=
    if user_input.startswith("http"):
        parsed = urlparse(user_input)
        qs = parse_qs(parsed.query)
        # The zone code is the first query parameter name (key with empty value)
        # e.g. ?nl18= -> {"nl18": [""]}
        for key in qs:
            clean = key.strip().rstrip("=")
            if clean:
                return clean
        # Fallback: try extracting from the raw query string
        raw_query = parsed.query.strip().rstrip("=")
        if raw_query and ZONE_CODE_RE.match(raw_query):
            return raw_query
        raise InvalidZoneCode("Could not extract zone code from URL")

    # Raw zone code: strip trailing = if present
    clean = user_input.strip().rstrip("=").strip()
    if not clean:
        raise InvalidZoneCode("Zone code is empty")

    return clean


async def _validate_zone_code(hass: HomeAssistant, zone_code: str) -> dict:
    """Validate the zone code by trying to fetch data from EC."""
    try:
        result = await hass.async_add_executor_job(fetch_ec_alerts, zone_code)
    except Exception as err:
        _LOGGER.error("Failed to fetch EC data for zone %s: %s", zone_code, err)
        raise CannotConnect from err

    if result.get("error") and result.get("count", 0) == 0:
        error = result.get("error", "")
        if error == "No zone data in initial state":
            raise InvalidZoneCode(error)
        if "Could not find/parse" in error:
            raise CannotConnect(error)

    return result


class ECWeatherAlertsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Environment Canada Weather Alerts."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                zone_code = _extract_zone_code(user_input[CONF_ZONE_CODE])
            except InvalidZoneCode:
                errors[CONF_ZONE_CODE] = "invalid_zone_code"
            else:
                # Check for duplicate entries
                await self.async_set_unique_id(zone_code)
                self._abort_if_unique_id_configured()

                try:
                    validation = await _validate_zone_code(self.hass, zone_code)
                except InvalidZoneCode:
                    errors[CONF_ZONE_CODE] = "invalid_zone_code"
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                else:
                    friendly_name = user_input.get(CONF_FRIENDLY_NAME, "").strip()
                    if not friendly_name:
                        friendly_name = validation.get("display_name") or zone_code

                    return self.async_create_entry(
                        title=friendly_name,
                        data={
                            CONF_ZONE_CODE: zone_code,
                            CONF_FRIENDLY_NAME: friendly_name,
                            CONF_REGION_NAME: validation.get("display_name", zone_code),
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ZONE_CODE): str,
                    vol.Optional(CONF_FRIENDLY_NAME, default=""): str,
                }
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidZoneCode(HomeAssistantError):
    """Error to indicate the zone code is invalid."""
