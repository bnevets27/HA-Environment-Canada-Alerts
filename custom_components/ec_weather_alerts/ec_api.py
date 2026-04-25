"""Environment Canada alerts API fetcher."""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from .const import EC_ALERTS_BASE_URL

NO_ALERTS_MESSAGE = "No alerts in effect."

# Stop parsing once the bulletin reaches stock follow-up text.
BOILER_START_RE = re.compile(
    r"^(For road conditions and other traveller information|"
    r"Please continue to monitor alerts|"
    r"To report severe weather|"
    r"For more information about the alerting program|"
    r"In effect for:|Follow:)",
    re.I,
)


def level_emoji(level: str) -> str:
    """Return an emoji indicator for the alert severity level."""
    s = (level or "").lower()
    if s.startswith("red warning"):
        return "\U0001F534"
    if s.startswith("orange warning"):
        return "\U0001F7E0"
    if s.startswith("yellow warning"):
        return "\U0001F7E1"
    if "special weather statement" in s:
        return "\u26AA"
    return "\u26A0"


def severity_rank(level: str) -> int:
    """Return a numeric severity rank for sorting (higher = more severe)."""
    s = (level or "").lower()
    if s.startswith("red warning"):
        return 4
    if s.startswith("orange warning"):
        return 3
    if s.startswith("yellow warning"):
        return 2
    if "special weather statement" in s:
        return 1
    return 0


def normalize_issue_time_text(value: str) -> str:
    """Normalize EC's time format to a parseable format."""
    if not value:
        return ""
    value = value.replace("p.m.", "PM").replace("a.m.", "AM")
    value = value.replace("p.m", "PM").replace("a.m", "AM")
    return value.strip()


def parse_issue_time(issue_time_text: str, timezone: ZoneInfo | None = None) -> tuple[str, str]:
    """Parse an EC issue time string into human and ISO formats."""
    if timezone is None:
        timezone = ZoneInfo("UTC")

    raw = normalize_issue_time_text(issue_time_text)
    if not raw:
        return "", ""

    parts = raw.split()
    if len(parts) >= 7:
        time_part = parts[0]
        ampm = parts[1]
        cleaned = " ".join([time_part, ampm] + parts[3:7])
        try:
            dt = datetime.strptime(cleaned, "%I:%M %p %A %d %B %Y").replace(
                tzinfo=timezone
            )
            pretty = dt.strftime("%A, %d %B %Y at %I:%M %p").replace(" 0", " ")
            return pretty, dt.isoformat()
        except ValueError:
            pass

    return issue_time_text.strip(), ""


def extract_initial_state(html: str) -> dict | None:
    """Extract the JSON object from window.__INITIAL_STATE__ in the page HTML."""
    match = re.search(
        r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;\s*\(function\(\)\{",
        html,
        re.S,
    )
    if not match:
        match = re.search(
            r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;</script>",
            html,
            re.S,
        )
    if not match:
        return None

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def zone_key_from_code(zone_code: str) -> str:
    """Extract a zone key from a zone code string or URL."""
    if zone_code.startswith("http"):
        query = parse_qs(urlparse(zone_code).query)
        return next(iter(query.keys()), zone_code)
    return zone_code


def split_sections(text: str) -> dict[str, str]:
    """Parse alert text into structured sections."""
    output = {"headline": "", "what": "", "when": "", "additional": ""}

    if not text:
        return output

    lines = [
        line.strip()
        for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]
    kept_lines: list[str] = []
    for line in lines:
        if BOILER_START_RE.match(line):
            break
        kept_lines.append(line)

    lines = [line for line in kept_lines if line]
    if lines:
        output["headline"] = lines[0].rstrip(".").strip()

    current = None
    buffer: dict[str, list[str]] = {"what": [], "when": [], "additional": []}

    for line in lines:
        lowered = line.lower()

        if lowered.startswith("what:"):
            current = "what"
            rest = line[5:].strip()
            if rest:
                buffer["what"].append(rest)
            continue

        if lowered.startswith("when:"):
            current = "when"
            rest = line[5:].strip()
            if rest:
                buffer["when"].append(rest)
            continue

        if lowered.startswith("additional information:"):
            current = "additional"
            rest = line[len("additional information:") :].strip()
            if rest:
                buffer["additional"].append(rest)
            continue

        if current is None:
            continue

        buffer[current].append(line)

    for key in ("what", "when", "additional"):
        output[key] = re.sub(r"\s+", " ", " ".join(buffer[key])).strip()

    return output


def _empty_result(url: str, zone_key: str, error: str = "") -> dict:
    """Return a normalized empty result payload."""
    result = {
        "url": url,
        "zone_key": zone_key,
        "display_name": "",
        "province_codes": "",
        "timezone": "",
        "count": 0,
        "max_level": "",
        "summary_md": NO_ALERTS_MESSAGE,
        "detail_md": NO_ALERTS_MESSAGE,
        "alerts": [],
    }
    if error:
        result["error"] = error
    return result


def fetch_ec_alerts(zone_code: str, timezone: ZoneInfo | None = None) -> dict:
    """Fetch and parse weather alerts from Environment Canada."""
    url = f"{EC_ALERTS_BASE_URL}?{zone_code}="
    preferred_zone_key = zone_key_from_code(zone_code)

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "HomeAssistant-EC-Alerts/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", errors="ignore")

    state = extract_initial_state(html)
    if not state:
        return _empty_result(
            url,
            preferred_zone_key,
            "Could not find/parse window.__INITIAL_STATE__",
        )

    zones = (((state.get("alert") or {}).get("alert")) or {})
    if not isinstance(zones, dict) or not zones:
        return _empty_result(url, preferred_zone_key, "No zone data in initial state")

    zone_key = (
        preferred_zone_key if preferred_zone_key in zones else next(iter(zones.keys()))
    )
    zone = zones.get(zone_key, {})
    raw_alerts = zone.get("alerts") or []
    zone_timezone = zone.get("timezone") or ""
    display_name = zone.get("displayName") or zone.get("publicZoneCode") or zone_key
    province_codes = zone.get("provinceCodes", "")

    parse_timezone = timezone
    if parse_timezone is None and zone_timezone:
        try:
            parse_timezone = ZoneInfo(zone_timezone)
        except Exception:
            parse_timezone = None

    summary_lines: list[str] = []
    detail_blocks: list[str] = []
    alerts_out: list[dict] = []

    max_level = ""
    max_rank = -1

    for alert in raw_alerts:
        title = (alert.get("bannerText") or alert.get("alertBannerText") or "").strip()
        if not title:
            title = "Alert"

        issued_raw = (alert.get("issueTimeText") or "").strip()
        issued_pretty, issued_iso = parse_issue_time(issued_raw, parse_timezone)

        sections = split_sections(alert.get("text") or "")
        headline = sections.get("headline", "")

        if " - " in title:
            level = title.split(" - ", 1)[0].strip()
            short = title
        else:
            level = title
            short = f"{title} - {headline}" if headline else title

        rank = severity_rank(level)
        if rank > max_rank:
            max_rank = rank
            max_level = level

        summary_lines.append(f"{level_emoji(level)} {short}")

        block = [f"**{title}**"]
        if issued_pretty:
            block.append(f"*Issued: {issued_pretty}*")
        if sections.get("what"):
            block.append(f"**What:** {sections['what']}")
        if sections.get("when"):
            block.append(f"**When:** {sections['when']}")
        if sections.get("additional"):
            block.append(f"**Additional info:** {sections['additional']}")

        detail_blocks.append("\n\n".join(block))

        alerts_out.append(
            {
                "title": title,
                "level": level,
                "issued_raw": issued_raw,
                "issued_pretty": issued_pretty,
                "issued_iso": issued_iso,
                "headline": headline,
                "what": sections.get("what", ""),
                "when": sections.get("when", ""),
                "additional": sections.get("additional", ""),
                "colour": alert.get("colour", ""),
                "alert_id": alert.get("alertId", ""),
                "alert_code": alert.get("alertCode", ""),
                "status": alert.get("status", ""),
            }
        )

    return {
        "url": url,
        "zone_key": zone_key,
        "display_name": display_name,
        "province_codes": province_codes,
        "timezone": zone_timezone,
        "count": len(alerts_out),
        "max_level": max_level,
        "summary_md": "\n".join(summary_lines) if summary_lines else NO_ALERTS_MESSAGE,
        "detail_md": (
            "\n\n---\n\n".join(detail_blocks) if detail_blocks else NO_ALERTS_MESSAGE
        ),
        "alerts": alerts_out,
    }
