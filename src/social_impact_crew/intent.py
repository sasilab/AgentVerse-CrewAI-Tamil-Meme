"""Intent classification for the chat endpoint.

Two layers, BreezyBuddy-inspired but explicit (we don't have a ReAct loop):
  1. Fast path — regex for obvious greetings / settings commands / common
     casual phrases. Free, instant, catches 80% of "hi", "enne thangam",
     "how are you", etc.
  2. LLM fallback — one short call with `temperature=0` for ambiguous
     messages. Extracts the city name when intent is CITY.

Also includes a geocoder-result validator: even when intent says CITY, the
returned match must be plausibly close to the input. Without this, Tamil
chitchat like "enne chellam" fuzzy-matched random small towns.
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal, Optional

Intent = Literal["city", "casual", "settings"]


@dataclass
class IntentResult:
    intent: Intent
    city: Optional[str] = None      # set when intent == "city"
    source: str = ""                # "fast" | "llm" | "default" — for logging


# --- Fast-path patterns ----------------------------------------------------

# Obvious greetings / sign-offs / acknowledgements (English + Tamil/Tanglish).
# Word boundaries keep "hi" from matching inside "Hilo" or "Chiang".
_CASUAL_OPENERS = re.compile(
    r"^\s*(?:hi|hello|hey|yo|sup|hola|namaste|vanakkam|gm|gn|"
    r"good\s*(?:morning|night|evening|afternoon)|"
    r"bye|cheers|thanks?|thx|ok|okay|sure|seri|aama|illa)\b",
    re.IGNORECASE,
)

# Common Tamil/Tanglish affectionate or filler words that geocoders abuse.
_TAMIL_CASUAL = re.compile(
    r"\b(?:enne|enna|yenna|thangam|chellam|kannu|raasaa|machaan|machi|"
    r"daa|dei|ponga|vaanga|seri|aana|innum|po|vada|saami)\b",
    re.IGNORECASE,
)

# Questions / emotions / pleasantries.
_CASUAL_QUESTIONS = re.compile(
    r"\b(?:how\s+are\s+you|what(?:'?s|\s+is)\s+up|wassup|are\s+you\s+(?:there|ok|real)|"
    r"who\s+are\s+you|what\s+can\s+you\s+do|what'?s\s+your\s+name|"
    r"love|miss|happy|sad|angry|tired|sick|sleepy|bored|stressed|anxious)\b",
    re.IGNORECASE,
)

# Settings commands.
_SETTINGS_PATTERNS = re.compile(
    r"\b(?:change|switch|set|update|open|show|go\s+to)\s+"
    r"(?:my\s+|the\s+)?(?:settings|language|personality|provider|model|city|location|key|tone|voice)\b",
    re.IGNORECASE,
)


def fast_classify(text: str) -> Optional[IntentResult]:
    """Return a classification if the message obviously matches one,
    otherwise None (caller should fall back to the LLM)."""
    s = (text or "").strip()
    if not s:
        return IntentResult(intent="casual", source="fast:empty")

    if _SETTINGS_PATTERNS.search(s):
        return IntentResult(intent="settings", source="fast:settings")

    if _CASUAL_OPENERS.search(s) or _TAMIL_CASUAL.search(s) or _CASUAL_QUESTIONS.search(s):
        return IntentResult(intent="casual", source="fast:casual")

    # Plain question (no city-looking words) — let LLM decide rather than
    # blindly geocoding "?" or "??".
    if s.endswith("?") and not re.search(r"\b[A-ZÀ-Ÿ][a-zà-ÿ]{2,}\b", s):
        return IntentResult(intent="casual", source="fast:question-mark-only")

    return None  # ambiguous — caller must invoke the LLM classifier


# --- LLM classifier --------------------------------------------------------

_CLASSIFY_PROMPT = """Classify this user message and reply in EXACTLY one of these formats on a single line:

  CITY: <city name>     — message names a real city or asks about weather/air quality somewhere
  CASUAL                — greeting, question, emotion, chitchat, anything not asking about a place
  SETTINGS              — user wants to change language / personality / provider / city / model

Examples:
"Chennai"                                 -> CITY: Chennai
"weather in Mumbai please"                -> CITY: Mumbai
"how is the air in Delhi today"           -> CITY: Delhi
"São Paulo"                               -> CITY: São Paulo
"hi"                                      -> CASUAL
"enne thangam"                            -> CASUAL
"how are you"                             -> CASUAL
"what can you do"                         -> CASUAL
"I'm tired"                               -> CASUAL
"change my language to Tamil"             -> SETTINGS
"open settings"                           -> SETTINGS

Message: {message}
Classification:"""


def llm_classify(message: str, llm) -> IntentResult:
    """Last-resort: one short LLM call with temperature 0.

    `llm` is a CrewAI LLM instance. We use its blocking `.call()` helper
    so this stays simple to invoke from a sync FastAPI handler.
    """
    try:
        reply = llm.call(messages=[
            {"role": "user", "content": _CLASSIFY_PROMPT.format(message=message)},
        ])
    except Exception:
        # Classifier failure shouldn't break the app — assume casual so we
        # never accidentally geocode garbage.
        return IntentResult(intent="casual", source="llm:error")

    text = str(reply).strip()
    upper = text.upper()
    if upper.startswith("CITY:"):
        city = text.split(":", 1)[1].strip().strip('"\'.,;:!?')
        if city:
            return IntentResult(intent="city", city=city, source="llm:city")
        return IntentResult(intent="casual", source="llm:empty-city")
    if upper.startswith("SETTINGS"):
        return IntentResult(intent="settings", source="llm:settings")
    return IntentResult(intent="casual", source="llm:casual")


# --- Geocode validation ----------------------------------------------------

def is_plausible_geocode(input_city: str, geocode_str: str) -> bool:
    """Check whether the geocoder's returned match is actually close to the input.

    `geocode_str` is what GeocodeTool returns: "lat,lon,name,country".
    Reject obvious mismatches (e.g. typed "enne chellam" -> matched "Rasipuram"):
      - name shares ≥ 50% similarity (covers "Bengaluru" vs "Bangalore"), OR
      - name contains/is-contained-by input (substring fuzzy match), OR
      - input is a long string (3+ words) that contains the returned name.
    """
    try:
        _, _, name, _ = geocode_str.split(",", 3)
    except ValueError:
        return False

    inp = (input_city or "").lower().strip()
    name = (name or "").lower().strip()
    if not name or not inp:
        return False

    if inp == name or inp in name or name in inp:
        return True

    sim = SequenceMatcher(None, inp, name).ratio()
    if sim >= 0.5:
        return True

    # Multi-word input that explicitly mentions the city name as a token.
    tokens_inp = set(re.findall(r"[a-zà-ÿ]{3,}", inp))
    tokens_name = set(re.findall(r"[a-zà-ÿ]{3,}", name))
    if tokens_name & tokens_inp:
        return True

    return False
