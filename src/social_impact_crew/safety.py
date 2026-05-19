"""Rule-based safety layer — runs BEFORE the LLM, with no LLM in the loop.

Mirrors BreezyBuddy's pattern: safety must never depend on a model. If the
air is dangerous, we return a hardcoded health alert and skip the meme
generation entirely. The meme writer never gets a chance to joke about
hazardous pollution.

Also includes the prompt-injection sanitiser adapted from BreezyBuddy.
"""

import re
from typing import Optional

# ---------- AQI hazard gate ----------

# European AQI bands (EEA scale). >100 = "Extremely poor".
# We add an extra "hazardous" threshold at 150 to mirror US AQI vocabulary
# (the user's spec said "unhealthy >100", "hazardous" is the next step up).
HAZARDOUS_AQI = 150
UNHEALTHY_AQI = 100


def aqi_safety_override(city: str, european_aqi: Optional[float]) -> Optional[str]:
    """Return a hardcoded health alert string if AQI is dangerous, else None.

    The caller should return this string AS the meme (skip the LLM call).
    Phrasing is plain, urgent, and personality-independent — when the air is
    this bad, jokes are inappropriate.
    """
    if european_aqi is None:
        return None
    if european_aqi >= HAZARDOUS_AQI:
        return (
            f"⚠️ Air in {city} is hazardous right now (AQI {int(european_aqi)}).\n"
            f"Stay indoors. Wear an N95 if you must go out. "
            f"Kids, elderly, and anyone with asthma should not leave home."
        )
    if european_aqi >= UNHEALTHY_AQI:
        return (
            f"⚠️ Air in {city} is unhealthy (AQI {int(european_aqi)}).\n"
            f"Limit outdoor time. Mask up if you go out. "
            f"At-risk groups (kids, elderly, asthma): stay inside if you can."
        )
    return None


# ---------- Prompt-injection sanitiser ----------
# Direct port of BreezyBuddy's regex set. Not a security boundary — soft
# defence-in-depth so the most common "ignore previous instructions" /
# "you are now" / "reveal your system prompt" phrasings get replaced with
# neutral markers before the LLM sees them.

_INJECTION_PATTERNS: list = [
    (re.compile(
        r"\b(?:ignore|forget|disregard)\s+(?:your|the|all|previous|above|prior)\b"
        r"[^.\n]{0,40}?(?:instructions?|rules?|prompts?|system|directives?)",
        re.IGNORECASE,
    ), "[neutralized: injection attempt]"),
    (re.compile(r"\bsystem\s+prompt\b", re.IGNORECASE),
     "[neutralized: 'system prompt']"),
    (re.compile(r"\byou\s+are\s+now\s+(?:a|an|the)\b", re.IGNORECASE),
     "[neutralized: role override]"),
    (re.compile(
        r"\boverride\s+(?:your|the|all)\b[^.\n]{0,40}?"
        r"(?:instructions?|rules?|prompts?|settings|character)",
        re.IGNORECASE,
    ), "[neutralized: override attempt]"),
    (re.compile(
        r"\b(?:reveal|show|print|tell\s+me|repeat)\s+(?:me\s+)?"
        r"(?:your\s+)?(?:full\s+|entire\s+|complete\s+)?(?:system\s+)?prompt\b",
        re.IGNORECASE,
    ), "[neutralized: prompt-disclosure attempt]"),
    (re.compile(r"\bnew\s+instructions?\s*:", re.IGNORECASE),
     "[neutralized: new-instructions marker]"),
]


def sanitize_user_input(text: str) -> str:
    """Replace common prompt-injection patterns with neutral markers.

    Never rejects the message — the user might legitimately discuss prompt
    injection. We just make sure the LLM sees the user *mentioned* the
    concept rather than seeing the literal directive form.
    """
    if not text:
        return text
    for pattern, replacement in _INJECTION_PATTERNS:
        text = pattern.sub(replacement, text)
    return text
