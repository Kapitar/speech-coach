"""
Configuration helpers for the elevenLabs pipeline.

This module is responsible for loading environment variables and exposing a
simple settings object that other modules can rely on.  The primary goal is to
centralise API key handling so that we fail fast when credentials are missing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv


DEFAULT_GEMINI_PRIMARY = "gemini-2.5-flash"

DEFAULT_GEMINI_FALLBACKS = [
    "models/gemini-2.5-flash",
    "models/gemini-2.5-pro",
    "models/gemini-1.5-flash-002",
    "models/gemini-1.5-pro-latest",
]


@dataclass(frozen=True)
class Settings:
    """Strongly-typed view of the configuration required by the pipeline."""

    elevenlabs_api_key: str
    gemini_api_key: str
    elevenlabs_stt_model: str
    elevenlabs_tts_model: str
    default_voice_id: str | None
    gemini_primary_model: str | None
    gemini_fallback_models: List[str] = field(default_factory=list)
    working_directory: Path = field(default_factory=lambda: Path("./.elevenLabs-cache").resolve())


_SETTINGS: Settings | None = None


def _load_env() -> None:
    """Load `.env` from the project root if present."""
    # Attempt to locate the project root by walking up until we find `.env`.
    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        candidate = parent / ".env"
        if candidate.exists():
            load_dotenv(dotenv_path=candidate, override=False)
            break
    else:
        # As a final fallback load from the environment without a file.  This
        # call is idempotent so it is safe even if no `.env` exists.
        load_dotenv(override=False)


def get_settings() -> Settings:
    """Return the cached :class:`Settings` instance (loading it if required)."""
    global _SETTINGS
    if _SETTINGS is not None:
        return _SETTINGS

    _load_env()

    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
    gemini_api_key = os.getenv("GOOGLE_AI_STUDIO_API_KEY") or os.getenv("GEMINI_API_KEY")

    if not elevenlabs_api_key:
        raise RuntimeError(
            "ELEVENLABS_API_KEY is not configured. Set it in your environment or .env file."
        )
    if not gemini_api_key:
        raise RuntimeError(
            "GOOGLE_AI_STUDIO_API_KEY (or GEMINI_API_KEY) is not configured. "
            "Set it in your environment or .env file."
        )

    settings = Settings(
        elevenlabs_api_key=elevenlabs_api_key,
        gemini_api_key=gemini_api_key,
        elevenlabs_stt_model=os.getenv("ELEVENLABS_STT_MODEL", "scribe_v1"),
        elevenlabs_tts_model=os.getenv("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2"),
        default_voice_id=os.getenv("ELEVENLABS_DEFAULT_VOICE_ID"),
        gemini_primary_model=os.getenv("GEMINI_MODEL_NAME", DEFAULT_GEMINI_PRIMARY),
        gemini_fallback_models=_resolve_gemini_fallbacks(),
        working_directory=_resolve_workdir(),
    )

    # Ensure working directory exists.
    settings.working_directory.mkdir(parents=True, exist_ok=True)

    _SETTINGS = settings
    return settings


def _resolve_gemini_fallbacks() -> List[str]:
    """Parse the optional GEMINI_FALLBACK_MODELS env var."""
    raw_value = os.getenv("GEMINI_FALLBACK_MODELS")
    if not raw_value:
        return list(DEFAULT_GEMINI_FALLBACKS)
    fallbacks = [model.strip() for model in raw_value.split(",") if model.strip()]
    return fallbacks or list(DEFAULT_GEMINI_FALLBACKS)


def _resolve_workdir() -> Path:
    raw = os.getenv("ELEVENLABS_WORKDIR", "./.elevenLabs-cache")
    return Path(raw).expanduser().resolve()


__all__ = ["Settings", "get_settings"]


