from __future__ import annotations

from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from backend.elevenLabs.testing import SpeechDemoTester


class TestingHarnessTests(TestCase):
    @patch("backend.elevenLabs.testing.run_pipeline")
    def test_run_with_injected_metadata(self, mock_pipeline):
        mock_pipeline.return_value = MagicMock(
            transcript="Original",
            optimized_transcript="Optimized",
            context_analysis={"overall_summary": "OK", "fields": {}},
            synthesized_audio_path=Path("output.mp3"),
        )

        tester = SpeechDemoTester(video_path="sample.mp3")
        result = tester.run(metadata={"genre": "Keynote"})

        self.assertEqual(result["metadata"]["genre"], "Keynote")
        self.assertEqual(result["context_analysis"]["overall_summary"], "OK")
        mock_pipeline.assert_called_once()

    @patch("backend.elevenLabs.testing.run_pipeline")
    def test_prompt_flow_produces_expected_payload(self, mock_pipeline):
        mock_pipeline.return_value = MagicMock(
            transcript="Full transcript text.",
            optimized_transcript="Improved transcript text.",
            context_analysis={
                "overall_summary": "Strong alignment",
                "fields": {
                    "genre": {"matches_context": True, "score": 9, "justification": "Energetic and inspirational."},
                    "purpose": {"matches_context": False, "score": 4, "justification": "Needs clearer call to action."},
                },
            },
            synthesized_audio_path=Path("output.mp3"),
        )

        responses = iter(["ted talk", "entertain", "college students", "Add humour"])

        tester = SpeechDemoTester()
        with patch("builtins.input", side_effect=lambda _: next(responses)):
            payload = tester.run()

        self.assertEqual(payload["transcript"], "Full transcript text.")
        self.assertEqual(payload["optimized_transcript"], "Improved transcript text.")
        self.assertIn("genre", payload["context_analysis"]["fields"])
        self.assertEqual(payload["metadata"]["audience"], "college students")
        mock_pipeline.assert_called_once()


