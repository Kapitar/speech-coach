from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from backend.elevenLabs.transcript_optimizer import OptimizationContext, optimize_transcript


class TranscriptOptimizerTests(TestCase):
    def test_context_prompt_segment(self):
        context = OptimizationContext(
            genre="Motivational",
            purpose="Inspire action",
            audience="Graduates",
            extra_instructions="Keep sentences short.",
        )
        prompt = context.to_prompt_segment()
        self.assertIn("Genre: Motivational", prompt)
        self.assertIn("Extra guidance", prompt)

    @patch("backend.elevenLabs.transcript_optimizer.resolve_gemini_model", return_value="models/mock")
    @patch("backend.elevenLabs.transcript_optimizer.configure_gemini")
    @patch("backend.elevenLabs.transcript_optimizer.genai.GenerativeModel")
    def test_optimize_transcript_returns_payload(
        self,
        mock_model,
        mock_configure,
        mock_resolve,
    ):
        generation = MagicMock()
        generation.generate_content.return_value = MagicMock(text="Optimised speech")
        mock_model.return_value = generation

        settings = SimpleNamespace(
            gemini_primary_model=None,
            gemini_fallback_models=["models/mock"],
        )

        with patch("backend.elevenLabs.transcript_optimizer.get_settings", return_value=settings):
            result = optimize_transcript("Raw speech text.")

        self.assertEqual(result["optimized_transcript"], "Optimised speech")
        mock_resolve.assert_called_once()
        mock_configure.assert_called_once()


