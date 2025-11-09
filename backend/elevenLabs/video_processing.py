"""Utilities for preparing media files for the ElevenLabs + Gemini pipeline."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Literal
from uuid import uuid4

from .config import get_settings
from .utils import ensure_executable_available


class VideoProcessingError(RuntimeError):
    """Raised when FFmpeg fails to process a video or audio file."""


SUPPORTED_AUDIO_FORMATS = {"wav", "mp3", "flac"}


def extract_audio(
    video_path: str | Path,
    *,
    output_format: Literal["wav", "mp3", "flac"] = "wav",
) -> Path:
    """
    Extract the audio track from ``video_path`` using FFmpeg.

    Args:
        video_path: Input video file path.
        output_format: Desired audio container. ElevenLabs STT supports WAV/MP3.

    Returns:
        Path to the extracted audio file.
    """
    settings = get_settings()
    src = Path(video_path).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"Video file not found: {src}")

    if output_format not in SUPPORTED_AUDIO_FORMATS:
        raise ValueError(f"Unsupported output format '{output_format}'.")

    ensure_executable_available("ffmpeg")
    dst = settings.working_directory / f"{src.stem}-{uuid4().hex}.{output_format}"

    audio_args = _ffmpeg_audio_args(output_format)
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        *audio_args,
        str(dst),
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:  # pragma: no cover - ffmpeg failure
        raise VideoProcessingError(f"FFmpeg failed to extract audio: {exc}") from exc

    return dst


def ensure_elevenlabs_compatible(
    audio_path: str | Path,
    *,
    preferred_format: Literal["wav", "mp3"] = "mp3",
) -> Path:
    """
    Convert ``audio_path`` to a format acceptable by ElevenLabs speech-to-text.

    ElevenLabs currently recommends WAV/MP3.  We attempt to convert using FFmpeg
    if the original audio extension differs from the requested one.
    """
    settings = get_settings()
    src = Path(audio_path).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"Audio file not found: {src}")

    if src.suffix.lower() == f".{preferred_format.lower()}":
        return src

    ensure_executable_available("ffmpeg")
    dst = settings.working_directory / f"{src.stem}-{uuid4().hex}.{preferred_format}"

    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        *_ffmpeg_audio_args(preferred_format),
        str(dst),
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:  # pragma: no cover - ffmpeg failure
        raise VideoProcessingError(f"FFmpeg failed to convert audio: {exc}") from exc

    return dst


def _ffmpeg_audio_args(output_format: str) -> list[str]:
    if output_format == "wav":
        return ["-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2"]
    if output_format == "mp3":
        return ["-vn", "-codec:a", "libmp3lame", "-ar", "44100", "-ac", "2", "-b:a", "192k"]
    if output_format == "flac":
        return ["-vn", "-codec:a", "flac", "-ar", "44100", "-ac", "2"]
    raise ValueError(f"Unhandled audio format '{output_format}'.")


__all__ = [
    "VideoProcessingError",
    "SUPPORTED_AUDIO_FORMATS",
    "ensure_elevenlabs_compatible",
    "extract_audio",
]


