# Environment Canada Weather Alerts for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Home Assistant custom integration that fetches detailed Environment Canada weather alerts and exposes them as sensors that are easy to use in dashboards and automations.

## Features

- UI-based setup through `Settings -> Devices & Services`
- Accepts either a full Environment Canada warning URL or a raw zone code
- Supports multiple configured regions
- Creates four sensors per region:
  - Alert Count
  - Alert Summary
  - Alert Detail
  - Max Alert Level
- Exposes markdown-ready attributes for Lovelace cards
- Includes example dashboard cards and an automation in [`examples/`](examples/)

## Installation

### HACS custom repository

1. Open HACS in Home Assistant.
2. Select the three-dot menu in the top-right corner.
3. Choose `Custom repositories`.
4. Add your GitHub repository URL:

   ```text
   https://github.com/YOUR_GITHUB_USERNAME/ha-environment-canada-alerts
   ```

5. Select `Integration` as the category.
6. Install `Environment Canada Weather Alerts`.
7. Restart Home Assistant.

### Manual installation

1. Copy `custom_components/ec_weather_alerts` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

### Find your zone code

Environment Canada's current public alert index is:

```text
https://weather.gc.ca/index_e.html?layers=alert
```

To find your zone code:

1. Open the alert index page above.
2. Search for your city or browse to your province and region.
3. Open the warning report page for your region.
4. Copy the code from the URL:

   ```text
   https://weather.gc.ca/warnings/report_e.html?nl18=
   ```

5. In this example, the zone code is `nl18`.

You can paste either the full warning URL or only the zone code into the integration.

Examples:

| Region | Zone code |
| --- | --- |
| Northern Peninsula East | `nl18` |
| Southern Ontario, ON | `onrm96_e` |
| Calgary, AB | `abcn11` |
| Vancouver, BC | `bccn10_e` |

### Add the integration

1. In Home Assistant, go to `Settings -> Devices & Services`.
2. Click `Add Integration`.
3. Search for `Environment Canada Weather Alerts`.
4. Paste your zone code or full warning URL.
5. Optionally enter a friendly name.

If you leave the friendly name blank, the integration uses the official Environment Canada region name automatically.

## Entities created

Each configured region creates these sensors:

| Entity | Purpose |
| --- | --- |
| `sensor.<region>_alert_count` | Number of active alerts |
| `sensor.<region>_alert_summary` | Short summary text |
| `sensor.<region>_alert_detail` | Full detail text in attributes |
| `sensor.<region>_max_alert_level` | Highest active severity |

Common attributes include:

- `zone_code`
- `region_name`
- `province_codes`
- `timezone`
- `url`

The detail sensor also includes:

- `detail_md`
- `summary_md`
- `alerts`

## Dashboard examples

Ready-to-paste examples live in [`examples/`](examples/):

- [`examples/lovelace/alert_summary_card.yaml`](examples/lovelace/alert_summary_card.yaml)
- [`examples/lovelace/alert_detail_card.yaml`](examples/lovelace/alert_detail_card.yaml)
- [`examples/lovelace/alert_overview_stack.yaml`](examples/lovelace/alert_overview_stack.yaml)
- [`examples/automations/notify_on_new_alert.yaml`](examples/automations/notify_on_new_alert.yaml)

Quick example:

```yaml
type: markdown
title: Weather Alerts
content: >
  {{ state_attr('sensor.my_region_alert_detail', 'detail_md')
     | default('No alerts in effect.', true) }}
entity_id: sensor.my_region_alert_detail
```

## Disclaimer

This project is not affiliated with, endorsed by, or connected to Environment and Climate Change Canada. Data is sourced from publicly available `weather.gc.ca` pages.
