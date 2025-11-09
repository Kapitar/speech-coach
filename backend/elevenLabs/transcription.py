"""Speech-to-text helpers combining ElevenLabs and Gemini."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

import google.generativeai as genai
from elevenlabs import ElevenLabs

from .config import Settings, get_settings
from .video_processing import ensure_elevenlabs_compatible, extract_audio
from .utils import configure_gemini, resolve_gemini_model

logger = logging.getLogger(__name__)


class TranscriptionError(RuntimeError):
    """Raised when both ElevenLabs and Gemini fail to produce a transcript."""


def transcribe_video(
    video_path: str | Path,
    *,
    preferred_audio_format: str = "mp3",
    stt_model: Optional[str] = None,
) -> str:
    """
    High-level helper that extracts the audio track from a video and transcribes it.
    """
    audio_path = extract_audio(video_path, output_format="wav")
    prepared_audio = ensure_elevenlabs_compatible(audio_path, preferred_format=preferred_audio_format)
    return transcribe_audio(prepared_audio, model_id=stt_model)


def transcribe_audio(audio_path: str | Path, *, model_id: Optional[str] = None) -> str:
    """
    Transcribe a local audio file using ElevenLabs Speech-to-Text with a Gemini fallback.
    """
    settings = get_settings()
    client = _get_elevenlabs_client(settings)

    prepared_audio = ensure_elevenlabs_compatible(audio_path, preferred_format="mp3")
    stt_model_id = model_id or settings.elevenlabs_stt_model

    try:
        response = client.speech_to_text.convert(file=str(prepared_audio), model_id=stt_model_id)
        text = getattr(response, "text", "")
        if not text:
            raise ValueError("ElevenLabs returned an empty transcription response.")
        return text
    except Exception as exc:
        logger.warning("ElevenLabs transcription failed (%s). Falling back to Gemini.", exc)

    fallback = _summarise_with_gemini(prepared_audio)
    if not fallback:
        raise TranscriptionError(
            "Unable to transcribe the audio file using ElevenLabs or Gemini fallback."
        )
    return fallback


_ELEVENLABS_CLIENTS: Dict[str, ElevenLabs] = {}


def _get_elevenlabs_client(settings: Settings) -> ElevenLabs:
    api_key = settings.elevenlabs_api_key
    client = _ELEVENLABS_CLIENTS.get(api_key)
    if client is None:
        client = ElevenLabs(api_key=api_key)
        _ELEVENLABS_CLIENTS[api_key] = client
    return client


def _summarise_with_gemini(audio_path: Path) -> str:
    settings = get_settings()
    try:
        model_name = resolve_gemini_model(
            settings.gemini_primary_model,
            settings.gemini_fallback_models,
        )
        configure_gemini(settings.gemini_api_key)
        model = genai.GenerativeModel(model_name)
    except Exception as exc:  # pragma: no cover - configuration failures
        logger.error("Gemini fallback failed during configuration: %s", exc)
        return ""

    prompt = (
        "Provide a concise transcript-style summary of the attached audio. "
        "Focus on capturing the spoken content. If the audio is unintelligible "
        "or unavailable, explain why."
    )

    try:
        upload = genai.upload_file(path=str(audio_path))
    except Exception:  # pragma: no cover - upload optional
        upload = None

    contents = []
    if upload is not None:
        contents.append(upload)
    contents.append({"text": prompt})

    try:
        response = model.generate_content(contents, request_options={"timeout": 600})
        return getattr(response, "text", "") or ""
    except Exception as exc:  # pragma: no cover - API errors
        logger.error("Gemini fallback generate_content failed: %s", exc)
        return ""


__all__ = ["TranscriptionError", "transcribe_audio", "transcribe_video"]


