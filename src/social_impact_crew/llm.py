"""LLM provider auto-detection with BYOK runtime overrides.

Two modes:
1. **Env-based** (CLI / first run): set GROQ_API_KEY (or GEMINI/OPENAI),
   or run Ollama locally — auto-detected.
2. **Runtime overrides** (Settings panel): the API request reads user prefs
   from preferences.py, calls `set_runtime_overrides(prefs)` BEFORE
   `kickoff()`, and the crew's agents build their LLMs with the user's
   provider/key without touching env. This is what makes "drop your own key
   in Settings and it works" possible — no restart needed.
"""

import os
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

import requests
from crewai import LLM

# Default model strings per provider. Free / cheap defaults so learners
# don't burn money on their first run.
DEFAULTS = {
    "groq": "groq/llama-3.3-70b-versatile",
    "gemini": "gemini/gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "claude": "claude-3-5-sonnet-20241022",
    "ollama": "ollama/llama3.2",
}

OLLAMA_DEFAULT_URL = "http://localhost:11434"

# Per-request override dict. Cleared after each kickoff.
_runtime_overrides: ContextVar[dict] = ContextVar("llm_overrides", default={})


@dataclass
class ProviderChoice:
    provider: str
    model: str
    source: str  # human-readable origin: "user settings", "GROQ_API_KEY", etc.


# ---------- runtime overrides (API path) ----------

def set_runtime_overrides(prefs: dict) -> None:
    """Call before crew.kickoff() to override env-based detection.

    Reads `provider`, `model`, `api_key`, `base_url` from `prefs`. If `api_key`
    or `provider` is missing/blank, this is a no-op (env detection kicks in).
    """
    _runtime_overrides.set({
        "provider": (prefs.get("provider") or "").strip(),
        "model": (prefs.get("model") or "").strip(),
        "api_key": (prefs.get("api_key") or "").strip(),
        "base_url": (prefs.get("base_url") or "").strip(),
    })


def clear_runtime_overrides() -> None:
    _runtime_overrides.set({})


# ---------- internal helpers ----------

def _ollama_running() -> bool:
    url = os.getenv("OLLAMA_BASE_URL", OLLAMA_DEFAULT_URL)
    try:
        r = requests.get(url, timeout=1)
        return r.ok
    except requests.RequestException:
        return False


def _normalise_model_string(provider: str, model: str) -> str:
    """Match LiteLLM's `provider/model` convention. Pass-through if already prefixed."""
    if not model:
        return DEFAULTS.get(provider, "")
    if "/" in model:
        return model
    if provider == "openai":
        return model  # litellm accepts bare openai model names
    if provider == "claude":
        return model  # litellm accepts bare claude model names
    return f"{provider}/{model}"


def detect_provider() -> Optional[ProviderChoice]:
    """Return the best provider choice from runtime overrides or env."""
    # 1. Runtime overrides (Settings panel) — preferred when api_key is set.
    overrides = _runtime_overrides.get()
    if overrides.get("api_key") and overrides.get("provider"):
        return ProviderChoice(
            provider=overrides["provider"],
            model=_normalise_model_string(overrides["provider"], overrides["model"]),
            source="user settings",
        )

    # 2. Explicit MODEL env var wins among env sources.
    explicit = os.getenv("MODEL")
    if explicit:
        provider = explicit.split("/", 1)[0] if "/" in explicit else "openai"
        return ProviderChoice(provider=provider, model=explicit, source="MODEL env var")

    # 3. Hosted providers in preference order: free first.
    if os.getenv("GROQ_API_KEY"):
        return ProviderChoice("groq", DEFAULTS["groq"], "GROQ_API_KEY")
    if os.getenv("GEMINI_API_KEY"):
        return ProviderChoice("gemini", DEFAULTS["gemini"], "GEMINI_API_KEY")
    if os.getenv("OPENAI_API_KEY"):
        return ProviderChoice("openai", DEFAULTS["openai"], "OPENAI_API_KEY")

    # 4. Local Ollama.
    if os.getenv("OLLAMA_BASE_URL") or _ollama_running():
        model = os.getenv("OLLAMA_MODEL", DEFAULTS["ollama"])
        return ProviderChoice("ollama", model, "local Ollama server")

    return None


# ---------- public build_llm ----------

def build_llm(temperature: float = 0.4) -> LLM:
    """Build the configured LLM. Reads runtime overrides first, then env."""
    choice = detect_provider()
    if choice is None:
        raise RuntimeError(no_provider_message())

    kwargs = {"model": choice.model, "temperature": temperature}

    overrides = _runtime_overrides.get()
    # When source is "user settings", pass api_key directly so we don't
    # depend on env vars being set in the server process.
    if choice.source == "user settings":
        if overrides.get("api_key"):
            kwargs["api_key"] = overrides["api_key"]
        if overrides.get("base_url"):
            kwargs["base_url"] = overrides["base_url"]

    return LLM(**kwargs)


def no_provider_message() -> str:
    return (
        "\n"
        "No LLM provider detected. Either:\n"
        "  - Open Settings in the web UI and paste a Groq / Gemini / OpenAI / Claude key, OR\n"
        "  - Run Ollama locally (`ollama serve` then `ollama pull llama3.2`), OR\n"
        "  - Set GROQ_API_KEY (or GEMINI_API_KEY / OPENAI_API_KEY) in .env\n"
        "\n"
        "Get a free Groq key at https://console.groq.com/keys\n"
    )


# ---------- connection test (used by /api/test-llm) ----------

def test_connection(provider: str, model: str, api_key: str = "", base_url: str = "") -> dict:
    """Single quick call to verify the credentials work. Returns {ok, ...}."""
    try:
        model_str = _normalise_model_string(provider, model or DEFAULTS.get(provider, ""))
        kwargs = {"model": model_str, "temperature": 0.0}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        llm = LLM(**kwargs)
        # `call` is CrewAI 1.x's blocking single-prompt helper.
        reply = llm.call(messages=[{"role": "user", "content": "Reply with the single word: OK"}])
        return {"ok": True, "reply": str(reply)[:200]}
    except Exception as e:
        msg = str(e).lower()
        category = "unknown"
        if "api key" in msg or "unauthorized" in msg or "401" in msg:
            category = "auth"
        elif "rate limit" in msg or "429" in msg or "quota" in msg:
            category = "rate_limit"
        elif "connection" in msg or "refused" in msg or "could not connect" in msg:
            category = "connection"
        return {"ok": False, "category": category, "error": str(e)[:300]}
