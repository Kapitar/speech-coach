"""Command-line entry point for the ElevenLabs speech pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the ElevenLabs + Gemini pipeline on a local video file.",
    )
    parser.add_argument("video", help="Path to the input video file (.mov, .mp4, etc.)")
    parser.add_argument(
        "--genre",
        help="Speech genre, e.g. inspirational, academic, pitch.",
    )
    parser.add_argument("--purpose", help="Primary intent of the speech.")
    parser.add_argument("--audience", help="Describe the target audience.")
    parser.add_argument(
        "--extra-instructions",
        help="Additional guidance for Gemini when optimising the transcript.",
    )
    parser.add_argument(
        "--voice-id",
        help="Existing ElevenLabs voice ID to reuse. If omitted the original audio will be cloned.",
    )
    parser.add_argument(
        "--output-dir",
        help="Directory to store synthesized audio. Defaults to the working directory from config.",
    )
    parser.add_argument(
        "--output-format",
        default="mp3_44100",
        help="ElevenLabs output format, e.g. mp3_44100 or pcm_44100.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    metadata = {
        "genre": args.genre,
        "purpose": args.purpose,
        "audience": args.audience,
        "extra_instructions": args.extra_instructions,
        "voice_id": args.voice_id,
        "output_format": args.output_format,
    }

    result = run_pipeline(
        args.video,
        metadata={key: value for key, value in metadata.items() if value},
        output_dir=args.output_dir,
    )

    summary = {
        "transcript_preview": result.transcript[:200],
        "optimized_transcript_preview": result.optimized_transcript[:200],
        "synthesized_audio_path": str(result.synthesized_audio_path),
        "intermediate_audio_path": str(result.intermediate_audio_path),
        "optimization_model": result.optimization_details.get("model"),
        "context_analysis": result.context_analysis,
    }

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()


