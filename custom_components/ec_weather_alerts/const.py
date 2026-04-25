"""Constants for the Environment Canada Weather Alerts integration."""

DOMAIN = "ec_weather_alerts"
PLATFORMS = ["sensor"]

CONF_ZONE_CODE = "zone_code"
CONF_FRIENDLY_NAME = "friendly_name"
CONF_REGION_NAME = "region_name"

# How often to poll EC (seconds)
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes

# Base URL for the EC alerts report page
EC_ALERTS_BASE_URL = "https://weather.gc.ca/warnings/report_e.html"

# Attribution
ATTRIBUTION = "Data provided by Environment and Climate Change Canada"
