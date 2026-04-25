"""Data coordinator for Environment Canada Weather Alerts."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .ec_api import fetch_ec_alerts

_LOGGER = logging.getLogger(__name__)


class ECWeatherAlertsCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch Environment Canada alert data."""

    def __init__(
        self,
        hass: HomeAssistant,
        zone_code: str,
        friendly_name: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{zone_code}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.zone_code = zone_code
        self.friendly_name = friendly_name

    async def _async_update_data(self) -> dict:
        """Fetch data from Environment Canada."""
        try:
            data = await self.hass.async_add_executor_job(
                fetch_ec_alerts, self.zone_code
            )
        except Exception as err:
            raise UpdateFailed(f"Error fetching EC alerts for {self.zone_code}: {err}") from err

        if data.get("error") and "Could not find/parse" in data.get("error", ""):
            _LOGGER.warning(
                "EC alerts page structure may have changed for zone %s: %s",
                self.zone_code,
                data.get("error"),
            )

        return data
