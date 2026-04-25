"""Environment Canada Weather Alerts integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS, CONF_ZONE_CODE, CONF_FRIENDLY_NAME
from .coordinator import ECWeatherAlertsCoordinator

_LOGGER = logging.getLogger(__name__)

ECWeatherAlertsConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: ECWeatherAlertsConfigEntry) -> bool:
    """Set up Environment Canada Weather Alerts from a config entry."""
    zone_code = entry.data[CONF_ZONE_CODE]
    friendly_name = entry.data.get(CONF_FRIENDLY_NAME, zone_code)

    coordinator = ECWeatherAlertsCoordinator(hass, zone_code, friendly_name)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ECWeatherAlertsConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
