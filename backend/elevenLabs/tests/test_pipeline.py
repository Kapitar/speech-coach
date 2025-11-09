from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from backend.elevenLabs.pipeline import PipelineResult, run_pipeline


class PipelineTests(TestCase):
    @patch("backend.elevenLabs.pipeline.synthesize_speech", return_value=b"audio-bytes")
    @patch(
        "backend.elevenLabs.pipeline.analyze_context_alignment",
        return_value={"overall_summary": "fits well", "fields": {"genre": {"score": 8}}},
    )
    @patch(
        "backend.elevenLabs.pipeline.optimize_transcript",
        return_value={"optimized_transcript": "Optimised text", "model": "models/mock"},
    )
    @patch("backend.elevenLabs.pipeline.transcribe_audio", return_value="Original transcript")
    @patch(
        "backend.elevenLabs.pipeline.ensure_elevenlabs_compatible",
        return_value=Path("prepared.mp3"),
    )
    @patch("backend.elevenLabs.pipeline.extract_audio", return_value=Path("extracted.wav"))
    def test_run_pipeline_creates_audio_file(
        self,
        mock_extract,
        mock_prepare,
        mock_transcribe,
        mock_optimize,
        mock_analyse,
        mock_synth,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = MagicMock()
            settings.working_directory = Path(temp_dir)

            with patch("backend.elevenLabs.pipeline.get_settings", return_value=settings):
                result = run_pipeline(
                    "video.mov",
                    metadata={"genre": "keynote", "output_format": "mp3_44100"},
                    output_dir=None,
                )

                self.assertIsInstance(result, PipelineResult)
                self.assertEqual(result.optimized_transcript, "Optimised text")
                self.assertTrue(result.synthesized_audio_path.exists())
                self.assertEqual(result.context_analysis["overall_summary"], "fits well")

        mock_extract.assert_called_once()
        mock_transcribe.assert_called_once_with(Path("prepared.mp3"))
        mock_optimize.assert_called_once()
        mock_analyse.assert_called_once()
        mock_synth.assert_called_once()


