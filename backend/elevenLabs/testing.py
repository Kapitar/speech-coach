"\"\"\"Interactive tester for the elevenLabs speech pipeline.\"\"\""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from .pipeline import run_pipeline
from .transcript_optimizer import OptimizationContext


class SpeechDemoTester:
    """Prompt-driven helper that runs the pipeline on a sample video."""

    def __init__(self, video_path: str | Path | None = None) -> None:
        if video_path is None:
            video_path = Path(__file__).resolve().parent / "sample.mp3"
        self.video_path = Path(video_path).expanduser().resolve()

    def prompt_for_metadata(self) -> Dict[str, str]:
        print("Enter contextual details (leave blank to skip):")
        genre = input("Genre: ").strip()
        purpose = input("Purpose: ").strip()
        audience = input("Audience: ").strip()
        extra = input("Extra instructions: ").strip()

        metadata = {
            "genre": genre or None,
            "purpose": purpose or None,
            "audience": audience or None,
            "extra_instructions": extra or None,
        }
        return {k: v for k, v in metadata.items() if v}

    def run(self, metadata: Optional[Dict[str, str]] = None) -> Dict[str, object]:
        if metadata is None:
            metadata = self.prompt_for_metadata()

        result = run_pipeline(self.video_path, metadata=metadata)
        return {
            "transcript": result.transcript,
            "optimized_transcript": result.optimized_transcript,
            "context_analysis": result.context_analysis,
            "metadata": metadata,
            "output_audio": str(result.synthesized_audio_path),
        }

    def display_summary(self, payload: Dict[str, object]) -> None:
        print("\n--- Speech Analysis Summary ---")
        print("\nOriginal Transcript Preview:\n", payload["transcript"][:500])
        print("\nOptimized Transcript Preview:\n", payload["optimized_transcript"][:500])
        analysis = payload["context_analysis"]
        print("\nContext Alignment Summary:\n", analysis.get("overall_summary", ""))
        for field, details in analysis.get("fields", {}).items():
            matches = "✅" if details.get("matches_context") else "⚠️"
            score = details.get("score")
            justification = details.get("justification", "")
            print(f"  {matches} {field} (score {score}): {justification}")
        print("\nSynthesized audio saved to:", payload["output_audio"])


def main() -> None:
    tester = SpeechDemoTester()
    payload = tester.run()
    tester.display_summary(payload)


if __name__ == "__main__":
    main()


