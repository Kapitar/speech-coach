"""High-level orchestration of the full ElevenLabs + Gemini workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from .analysis import analyze_context_alignment
from .config import get_settings
from .transcription import transcribe_audio
from .transcript_optimizer import OptimizationContext, optimize_transcript
from .video_processing import ensure_elevenlabs_compatible, extract_audio
from .voice_clone import synthesize_speech


@dataclass
class PipelineResult:
    transcript: str
    optimized_transcript: str
    optimization_details: Dict[str, Any]
    context_analysis: Dict[str, Any]
    synthesized_audio_path: Path
    intermediate_audio_path: Path


def run_pipeline(
    video_path: str | Path,
    *,
    metadata: Optional[Dict[str, Optional[str]]] = None,
    output_dir: Optional[str | Path] = None,
) -> PipelineResult:
    """
    Execute the full pipeline: video → transcript → optimisation → voice synthesis.
    """
    metadata = metadata or {}
    settings = get_settings()

    working_audio = extract_audio(video_path, output_format="wav")
    prepared_audio = ensure_elevenlabs_compatible(working_audio, preferred_format="mp3")

    transcript = transcribe_audio(prepared_audio)

    context = OptimizationContext(
        genre=metadata.get("genre"),
        purpose=metadata.get("purpose"),
        audience=metadata.get("audience"),
        extra_instructions=metadata.get("extra_instructions"),
    )
    optimisation_payload = optimize_transcript(transcript, context=context)
    optimised_text = optimisation_payload["optimized_transcript"]
    analysis = analyze_context_alignment(transcript, context)

    voice_id = metadata.get("voice_id")
    output_format = metadata.get("output_format", "mp3_44100")
    synthesised_bytes = synthesize_speech(
        optimised_text,
        voice_id=voice_id,
        sample_audio=prepared_audio if voice_id is None else None,
        output_format=output_format,
    )

    destination_dir = (
        Path(output_dir).expanduser().resolve()
        if output_dir
        else settings.working_directory
    )
    destination_dir.mkdir(parents=True, exist_ok=True)

    video_stem = Path(video_path).stem
    output_suffix = "mp3" if output_format.startswith("mp3") else "wav"
    audio_filename = f"{video_stem}-speech-{uuid4().hex[:8]}.{output_suffix}"
    audio_path = destination_dir / audio_filename
    audio_path.write_bytes(synthesised_bytes)

    return PipelineResult(
        transcript=transcript,
        optimized_transcript=optimised_text,
        optimization_details=optimisation_payload,
        context_analysis=analysis,
        synthesized_audio_path=audio_path,
        intermediate_audio_path=prepared_audio,
    )


__all__ = ["PipelineResult", "run_pipeline"]


