"""Shared helpers for the ElevenLabs / Gemini integrations."""

from __future__ import annotations

import logging
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import google.generativeai as genai

from .config import get_settings

logger = logging.getLogger(__name__)

_CONFIGURED_GEMINI_KEY: Optional[str] = None


def ensure_directory(path: str | Path) -> Path:
    """Create ``path`` if it does not exist and return it as a :class:`Path`."""
    target = Path(path).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target


def ensure_executable_available(executable: str, *, install_hint: Optional[str] = None) -> None:
    """Ensure a given executable exists on PATH, otherwise raise an error."""
    if shutil.which(executable):
        return

    hint = f" Install it via: {install_hint}" if install_hint else ""
    raise EnvironmentError(f"Required executable '{executable}' was not found on PATH.{hint}")


def configure_gemini(api_key: Optional[str] = None) -> None:
    """Idempotently configure the Gemini client."""
    global _CONFIGURED_GEMINI_KEY
    settings = get_settings()
    api_key = api_key or settings.gemini_api_key
    if _CONFIGURED_GEMINI_KEY == api_key:
        return
    genai.configure(api_key=api_key)
    _CONFIGURED_GEMINI_KEY = api_key


def resolve_gemini_model(
    primary_model: Optional[str],
    fallbacks: Sequence[str],
    *,
    capability: str = "generateContent",
) -> str:
    """Return a Gemini model that supports the requested capability."""
    configure_gemini()
    available = list_supported_gemini_models(capability=capability)

    candidates: List[str] = []
    if primary_model:
        candidates.append(primary_model)
    candidates.extend(fallbacks)

    for candidate in candidates:
        if candidate in available:
            return candidate

    if not available:
        raise RuntimeError(f"No Gemini models support {capability}.")
    return available[0]


@lru_cache(maxsize=1)
def list_supported_gemini_models(*, capability: str = "generateContent") -> List[str]:
    models: List[str] = []
    for model in genai.list_models():
        methods = _supported_methods(model)
        if methods and capability in methods:
            models.append(model.name)
    return models


def _supported_methods(model: object):
    methods = getattr(model, "supported_generation_methods", None)
    if methods:
        return methods
    if hasattr(model, "to_dict"):
        data = model.to_dict()
        if isinstance(data, dict):
            methods = data.get("supportedGenerationMethods")
            if methods:
                return methods
            capabilities = data.get("modelCapabilities") or {}
            return capabilities.get("generationMethods")
    return None


def coerce_audio_stream(stream: Iterable[bytes] | bytes) -> Iterable[bytes]:
    """Return an iterable of audio bytes from the ElevenLabs streaming response."""
    if isinstance(stream, (bytes, bytearray)):
        return [bytes(stream)]
    return stream


__all__ = [
    "configure_gemini",
    "coerce_audio_stream",
    "ensure_directory",
    "ensure_executable_available",
    "list_supported_gemini_models",
    "resolve_gemini_model",
]


