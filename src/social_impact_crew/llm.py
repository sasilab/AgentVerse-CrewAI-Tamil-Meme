"""LLM provider auto-detection.

Why a separate module: both main.py (startup check) and crew.py (agent build)
need to know which provider is configured. Putting the logic here means
provider rules live in one place, and the .env contract is documented in code
right next to .env.example.

Detection rules, in order:
  1. If MODEL env var is set explicitly, trust it (advanced users override).
  2. Otherwise scan keys: GROQ_API_KEY -> GEMINI_API_KEY -> OPENAI_API_KEY.
  3. Otherwise probe local Ollama (no key needed; check :11434).
  4. Otherwise: no provider — print friendly help and bail.
"""

import os
from dataclasses import dataclass
from typing import Optional

import requests
from crewai import LLM

# Default model strings per provider. Picked free/cheap defaults so learners
# don't burn money on their first run.
DEFAULTS = {
    "groq": "groq/llama-3.3-70b-versatile",
    "gemini": "gemini/gemini-2.0-flash",
    "openai": "gpt-4o-mini",
    "ollama": "ollama/llama3.2",
}

OLLAMA_DEFAULT_URL = "http://localhost:11434"


@dataclass
class ProviderChoice:
    provider: str        # e.g. "groq"
    model: str           # e.g. "groq/llama-3.3-70b-versatile"
    source: str          # "MODEL env var" or "GROQ_API_KEY" etc — for logging


def _ollama_running() -> bool:
    """Cheap liveness probe for a local Ollama server."""
    url = os.getenv("OLLAMA_BASE_URL", OLLAMA_DEFAULT_URL)
    try:
        # 1s timeout — we don't want startup to stall if the user has no Ollama.
        r = requests.get(url, timeout=1)
        return r.ok
    except requests.RequestException:
        return False


def detect_provider() -> Optional[ProviderChoice]:
    """Return the best provider choice, or None if nothing is configured."""
    # 1) Explicit MODEL wins. We still try to infer the provider name for
    #    nicer logging, but trust the user's string verbatim.
    explicit = os.getenv("MODEL")
    if explicit:
        provider = explicit.split("/", 1)[0] if "/" in explicit else "openai"
        return ProviderChoice(provider=provider, model=explicit, source="MODEL env var")

    # 2) Hosted providers in preference order: free first, paid last.
    if os.getenv("GROQ_API_KEY"):
        return ProviderChoice("groq", DEFAULTS["groq"], "GROQ_API_KEY")
    if os.getenv("GEMINI_API_KEY"):
        return ProviderChoice("gemini", DEFAULTS["gemini"], "GEMINI_API_KEY")
    if os.getenv("OPENAI_API_KEY"):
        return ProviderChoice("openai", DEFAULTS["openai"], "OPENAI_API_KEY")

    # 3) Local Ollama — no key, just needs the server running.
    if os.getenv("OLLAMA_BASE_URL") or _ollama_running():
        model = os.getenv("OLLAMA_MODEL", DEFAULTS["ollama"])
        return ProviderChoice("ollama", model, "local Ollama server")

    return None


def build_llm(temperature: float = 0.4) -> LLM:
    """Build the configured LLM. Raises RuntimeError if nothing is set up.

    Default temperature 0.4 keeps fact-oriented agents (weather, pollution)
    grounded. Creative agents like the meme writer should pass a higher
    value (e.g. 0.9) for punchier, more varied output.
    """
    choice = detect_provider()
    if choice is None:
        raise RuntimeError(no_provider_message())
    return LLM(model=choice.model, temperature=temperature)


def no_provider_message() -> str:
    """Friendly help text listing every supported provider."""
    return (
        "\n"
        "No LLM provider detected. Add ONE of these to your .env:\n"
        "\n"
        "  Groq (free, fast):\n"
        "    GROQ_API_KEY=...        https://console.groq.com/keys\n"
        "\n"
        "  Gemini (free tier):\n"
        "    GEMINI_API_KEY=...      https://aistudio.google.com/apikey\n"
        "\n"
        "  OpenAI (paid):\n"
        "    OPENAI_API_KEY=...      https://platform.openai.com/api-keys\n"
        "\n"
        "  Ollama (local, free, no key):\n"
        "    Run `ollama serve` then `ollama pull llama3.2`\n"
        "    Optional: OLLAMA_MODEL=ollama/<model>  OLLAMA_BASE_URL=http://localhost:11434\n"
        "\n"
        "Advanced: set MODEL=<provider>/<model> in .env to override the defaults.\n"
    )
