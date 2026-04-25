"""Sensor platform for Environment Canada Weather Alerts."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ATTRIBUTION,
    CONF_ZONE_CODE,
    CONF_FRIENDLY_NAME,
    CONF_REGION_NAME,
)
from .coordinator import ECWeatherAlertsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EC Weather Alerts sensors from a config entry."""
    coordinator: ECWeatherAlertsCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        ECAlertCountSensor(coordinator, entry),
        ECAlertSummarySensor(coordinator, entry),
        ECAlertDetailSensor(coordinator, entry),
        ECAlertMaxLevelSensor(coordinator, entry),
    ]

    async_add_entities(entities, True)


class ECAlertBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for EC Weather Alert sensors."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ECWeatherAlertsCoordinator,
        entry: ConfigEntry,
        sensor_key: str,
        name_suffix: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._sensor_key = sensor_key
        zone_code = entry.data[CONF_ZONE_CODE]
        friendly_name = entry.data.get(CONF_FRIENDLY_NAME, zone_code)

        self._attr_unique_id = f"{zone_code}_{sensor_key}"
        self._attr_name = f"{friendly_name} {name_suffix}"

    @property
    def device_info(self):
        """Return device info to group sensors under one device."""
        zone_code = self._entry.data[CONF_ZONE_CODE]
        friendly_name = self._entry.data.get(CONF_FRIENDLY_NAME, zone_code)
        region_name = self._entry.data.get(CONF_REGION_NAME, zone_code)
        return {
            "identifiers": {(DOMAIN, zone_code)},
            "name": f"EC Alerts - {friendly_name}",
            "manufacturer": "Environment and Climate Change Canada",
            "model": f"Weather Alerts ({region_name})",
            "entry_type": "service",
        }

    def _shared_attributes(self) -> dict[str, Any]:
        """Return shared region metadata."""
        data = self.coordinator.data or {}
        zone_code = self._entry.data[CONF_ZONE_CODE]
        return {
            "zone_code": zone_code,
            "region_name": data.get(
                "display_name",
                self._entry.data.get(CONF_REGION_NAME, zone_code),
            ),
            "province_codes": data.get("province_codes", ""),
            "timezone": data.get("timezone", ""),
            "url": data.get("url", ""),
        }


class ECAlertCountSensor(ECAlertBaseSensor):
    """Sensor showing the number of active alerts."""

    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "alert_count", "Alert Count")

    @property
    def native_value(self) -> int:
        """Return the number of active alerts."""
        if self.coordinator.data:
            return self.coordinator.data.get("count", 0)
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        data = self.coordinator.data or {}
        attrs = self._shared_attributes()
        attrs["zone_key"] = data.get("zone_key", "")
        # Include individual alert details as attributes
        alerts = data.get("alerts", [])
        for i, alert in enumerate(alerts, 1):
            attrs[f"alert_{i}_title"] = alert.get("title", "")
            attrs[f"alert_{i}_level"] = alert.get("level", "")
            attrs[f"alert_{i}_issued"] = alert.get("issued_pretty", "")
            attrs[f"alert_{i}_what"] = alert.get("what", "")
            attrs[f"alert_{i}_when"] = alert.get("when", "")
        return attrs


class ECAlertSummarySensor(ECAlertBaseSensor):
    """Sensor providing a short markdown summary of alerts."""

    _attr_icon = "mdi:weather-lightning-rainy"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "summary", "Alert Summary")

    @property
    def native_value(self) -> str:
        """Return the summary markdown."""
        if self.coordinator.data:
            return self.coordinator.data.get("summary_md", "No alerts in effect.")
        return "No alerts in effect."

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the full summary and alert count."""
        data = self.coordinator.data or {}
        attrs = self._shared_attributes()
        attrs.update(
            {
                "summary_md": data.get("summary_md", "No alerts in effect."),
                "count": data.get("count", 0),
                "max_level": data.get("max_level", ""),
            }
        )
        return attrs


class ECAlertDetailSensor(ECAlertBaseSensor):
    """Sensor providing detailed markdown of alerts."""

    _attr_icon = "mdi:text-box-outline"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "detail", "Alert Detail")

    @property
    def native_value(self) -> str:
        """Return alert count as state (detail is too long for state)."""
        if self.coordinator.data:
            count = self.coordinator.data.get("count", 0)
            if count == 0:
                return "No alerts"
            return f"{count} alert{'s' if count != 1 else ''}"
        return "No alerts"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the full detail markdown and structured alert data."""
        data = self.coordinator.data or {}
        attrs = self._shared_attributes()
        attrs.update(
            {
                "detail_md": data.get("detail_md", "No alerts in effect."),
                "summary_md": data.get("summary_md", "No alerts in effect."),
                "count": data.get("count", 0),
                "max_level": data.get("max_level", ""),
                "alerts": data.get("alerts", []),
            }
        )
        return attrs


class ECAlertMaxLevelSensor(ECAlertBaseSensor):
    """Sensor showing the highest active alert severity level."""

    _attr_icon = "mdi:shield-alert-outline"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "max_level", "Max Alert Level")

    @property
    def native_value(self) -> str:
        """Return the highest severity level."""
        if self.coordinator.data:
            return self.coordinator.data.get("max_level", "") or "None"
        return "None"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the count and URL."""
        data = self.coordinator.data or {}
        attrs = self._shared_attributes()
        attrs.update(
            {
                "count": data.get("count", 0),
            }
        )
        return attrs
