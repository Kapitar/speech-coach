from __future__ import annotations

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from backend.elevenLabs.analysis import analyze_context_alignment
from backend.elevenLabs.transcript_optimizer import OptimizationContext


class AnalysisTests(TestCase):
    @patch("backend.elevenLabs.analysis.resolve_gemini_model", return_value="models/mock")
    @patch("backend.elevenLabs.analysis.configure_gemini")
    @patch("backend.elevenLabs.analysis.genai.GenerativeModel")
    def test_returns_parsed_json(
        self,
        mock_model,
        mock_configure,
        mock_resolve,
    ):
        generation = MagicMock()
        generation.generate_content.return_value = MagicMock(
            text=json.dumps(
                {
                    "overall_summary": "Great match",
                    "fields": {"genre": {"matches_context": True, "score": 9, "justification": "Uplifting"}},
                }
            )
        )
        mock_model.return_value = generation

        settings = MagicMock()
        settings.gemini_primary_model = None
        settings.gemini_fallback_models = ["models/mock"]

        with patch("backend.elevenLabs.analysis.get_settings", return_value=settings):
            context = OptimizationContext(genre="Motivational")
            result = analyze_context_alignment("Speech content", context)

        self.assertEqual(result["overall_summary"], "Great match")
        self.assertIn("genre", result["fields"])
        mock_configure.assert_called_once()
        mock_resolve.assert_called_once()

    def test_returns_default_when_no_context(self):
        result = analyze_context_alignment("Speech content", OptimizationContext())
        self.assertEqual(result["fields"], {})
        self.assertIn("No specific context", result["overall_summary"])


