"""Voice cloning and synthesis helpers for ElevenLabs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

from elevenlabs import ElevenLabs

from .config import Settings, get_settings
from .video_processing import ensure_elevenlabs_compatible
from .utils import coerce_audio_stream

logger = logging.getLogger(__name__)


class VoiceCloneError(RuntimeError):
    """Raised when ElevenLabs voice cloning or synthesis fails."""


def clone_voice_from_sample(
    sample_audio: str | Path,
    *,
    voice_name: Optional[str] = None,
    remove_background_noise: bool = True,
    description: Optional[str] = None,
) -> str:
    """
    Clone a voice in ElevenLabs using the provided audio sample.

    Returns the new voice ID.
    """
    settings = get_settings()
    client = _get_elevenlabs_client(settings)

    voice_name = voice_name or f"VoiceClone-{uuid4().hex[:8]}"
    prepared_sample = ensure_elevenlabs_compatible(sample_audio, preferred_format="mp3")

    try:
        response = client.voices.ivc.create(
            name=voice_name,
            files=[prepared_sample.read_bytes()],
            remove_background_noise=remove_background_noise,
            description=description,
        )
    except Exception as exc:  # pragma: no cover - API errors
        raise VoiceCloneError(f"Failed to clone voice: {exc}") from exc

    voice_id = getattr(response, "voice_id", None)
    if not voice_id:
        raise VoiceCloneError("ElevenLabs did not return a voice ID for the cloned voice.")
    return voice_id


def synthesize_speech(
    text: str,
    *,
    voice_id: Optional[str] = None,
    sample_audio: Optional[str | Path] = None,
    output_format: str = "mp3_44100",
    tts_model: Optional[str] = None,
) -> bytes:
    """
    Convert text into speech using ElevenLabs.  If ``voice_id`` is not provided
    but ``sample_audio`` is, a temporary cloned voice will be created.
    """
    if not text.strip():
        raise ValueError("Cannot synthesise empty text.")

    settings = get_settings()
    client = _get_elevenlabs_client(settings)
    resolved_voice_id = voice_id or settings.default_voice_id

    if not resolved_voice_id and sample_audio is None:
        raise VoiceCloneError(
            "No voice specified. Provide `voice_id` or `sample_audio` for cloning."
        )

    if not resolved_voice_id and sample_audio is not None:
        resolved_voice_id = clone_voice_from_sample(sample_audio)
        logger.info("Cloned temporary voice %s from sample.", resolved_voice_id)

    try:
        stream = client.text_to_speech.convert(
            voice_id=resolved_voice_id,
            text=text,
            model_id=tts_model or settings.elevenlabs_tts_model,
            output_format=output_format,
        )
    except Exception as exc:  # pragma: no cover - API errors
        raise VoiceCloneError(f"Failed to synthesise speech: {exc}") from exc

    return b"".join(coerce_audio_stream(stream))


_ELEVENLABS_CLIENTS: Dict[str, ElevenLabs] = {}


def _get_elevenlabs_client(settings: Settings) -> ElevenLabs:
    api_key = settings.elevenlabs_api_key
    client = _ELEVENLABS_CLIENTS.get(api_key)
    if client is None:
        client = ElevenLabs(api_key=api_key)
        _ELEVENLABS_CLIENTS[api_key] = client
    return client


__all__ = ["VoiceCloneError", "clone_voice_from_sample", "synthesize_speech"]


