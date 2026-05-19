"""Entry point. Prompts the user for a city (defaulting to IP-detected
location), then kicks off the crew."""

import sys
from typing import Optional

import openlit
import requests
from dotenv import load_dotenv

from .crew import SocialImpactCrew
from .llm import detect_provider, no_provider_message
from .tools.custom_tool import GeocodeTool

# One-liner observability: auto-instruments LLM + HTTP calls. Default OTLP
# endpoint is http://127.0.0.1:4318; override with OTEL_EXPORTER_OTLP_ENDPOINT.
# Silent no-op if no collector is running.
openlit.init(application_name="social_impact_crew_cli")

# Short timeout so a slow / blocked geo lookup doesn't stall startup.
IP_LOOKUP_TIMEOUT = 5


def _detect_city_from_ip() -> Optional[str]:
    """Guess the user's city from their public IP.

    Uses ipinfo.io (HTTPS, no key, 50k req/month free). Returns None on any
    failure — we silently fall back to the manual prompt rather than crashing
    when the user is offline or behind a VPN that blocks the lookup.
    """
    try:
        r = requests.get("https://ipinfo.io/json", timeout=IP_LOOKUP_TIMEOUT)
        r.raise_for_status()
        city = r.json().get("city")
        return city or None
    except requests.RequestException:
        return None


def _prompt_city() -> str:
    """Resolve the city to use, in priority order: CLI arg > user input > IP > Chennai."""
    # CLI arg wins so non-interactive runs (CI, demos) don't hang on input().
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:]).strip()

    detected = _detect_city_from_ip()
    if detected:
        raw = input(f"Which city? [press Enter for {detected}]: ").strip()
        return raw or detected

    # No CLI arg, IP lookup failed — fall back to plain prompt.
    raw = input("Which city? (e.g. Chennai, Bengaluru, Mumbai): ").strip()
    return raw or "Chennai"


def run() -> None:
    load_dotenv()

    # Fail fast with a friendly message if no LLM provider is configured.
    # The same check runs again inside crew.py when agents are built; doing
    # it here avoids confusing partial-startup tracebacks.
    choice = detect_provider()
    if choice is None:
        sys.exit(no_provider_message())
    print(f"[LLM] Using {choice.provider} → {choice.model} (via {choice.source})")

    city = _prompt_city()
    print(f"\nKicking off crew for: {city}\n")

    # Pre-resolve coordinates so the agents don't have to (the LLM was
    # hallucinating coords for the weather call — see api.py comment).
    geo_str = GeocodeTool()._run(city=city)
    if geo_str.startswith("ERROR"):
        sys.exit(geo_str)
    lat_s, lon_s, resolved_name, country = geo_str.split(",", 3)
    lat, lon = float(lat_s), float(lon_s)
    print(f"[geo] {city} -> {resolved_name}, {country} ({lat}, {lon})\n")

    crew_obj = SocialImpactCrew().crew()
    result = crew_obj.kickoff(inputs={"city": city, "lat": lat, "lon": lon})

    print("\n" + "=" * 60)
    print(f"FINAL MEME for {city}")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    run()
