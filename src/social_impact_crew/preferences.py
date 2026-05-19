"""JSON-file preferences store (BreezyBuddy-style).

Single-user, local-first. Stored at data/user_preferences.json. Async lock
keeps concurrent /api/settings writes from corrupting the file. Atomic
rename on write.

The JSON file is the source of truth for runtime config: provider, model,
API key, city, personality, language, notification settings. /api/run reads
this on every request so changes in the Settings panel take effect
immediately without restart.
"""

import asyncio
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from .personality import DEFAULT_LANGUAGE, DEFAULT_PERSONALITY

# Resolve data/user_preferences.json relative to the EPISODE root.
# This file lives at: <episode>/src/social_impact_crew/preferences.py
# parents[0] = social_impact_crew/ (package), [1] = src/, [2] = episode root.
_EPISODE_ROOT = Path(__file__).resolve().parents[2]
_DATA_PATH = _EPISODE_ROOT / "data" / "user_preferences.json"

_lock = asyncio.Lock()

DEFAULT_PREFERENCES: dict = {
    # Location
    "city": "",
    "coordinates": {"lat": None, "lon": None, "country": ""},

    # LLM provider (BYOK)
    "provider": "groq",
    "model": "llama-3.3-70b-versatile",
    "api_key": "",
    "base_url": "",

    # Voice
    "personality": DEFAULT_PERSONALITY,
    "language": DEFAULT_LANGUAGE,

    # Health / notification preferences
    "preferences": {
        "notifications_enabled": True,
        # User-facing options were 30 / 60 / 180 (min). Default to 60.
        "nudge_interval_minutes": 60,
        # AQI thresholds that trigger the OS-level notification.
        # We notify when european_aqi crosses this. Default 100 = unhealthy.
        "notify_aqi_threshold": 100,
        # Sensitive group (mirrors BreezyBuddy interests). Used in safety prompt.
        "sensitive_groups": [],   # e.g. ["asthma", "elderly", "kids"]
        # Background Mode (frontend collapses to floating pill, notif-only).
        "background_mode": False,
    },
}


def _ensure_file() -> None:
    if not _DATA_PATH.exists():
        _DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_PREFERENCES, f, indent=2)


def _read_sync() -> dict:
    _ensure_file()
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = deepcopy(DEFAULT_PREFERENCES)
        _write_sync(data)

    # Merge in missing keys from defaults (forward-compat with older files).
    merged = deepcopy(DEFAULT_PREFERENCES)
    merged.update({k: v for k, v in data.items() if k in DEFAULT_PREFERENCES})
    merged["preferences"] = {
        **DEFAULT_PREFERENCES["preferences"],
        **(data.get("preferences") or {}),
    }
    return merged


def _write_sync(data: dict) -> None:
    _DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = _DATA_PATH.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, _DATA_PATH)


async def load_preferences() -> dict:
    async with _lock:
        return _read_sync()


async def save_preferences(data: dict) -> dict:
    """Overwrite preferences with `data`. Unknown keys are silently dropped."""
    async with _lock:
        merged = deepcopy(DEFAULT_PREFERENCES)
        for key in DEFAULT_PREFERENCES:
            if key in data:
                merged[key] = data[key]
        if isinstance(data.get("preferences"), dict):
            merged["preferences"] = {
                **DEFAULT_PREFERENCES["preferences"],
                **data["preferences"],
            }
        _write_sync(merged)
        return merged


async def update_preference(key: str, value: Any) -> dict:
    """Update a single top-level key. Use dot syntax for nested: `preferences.foo`."""
    async with _lock:
        data = _read_sync()
        if "." in key:
            top, sub = key.split(".", 1)
            data.setdefault(top, {})[sub] = value
        else:
            data[key] = value
        _write_sync(data)
        return data
