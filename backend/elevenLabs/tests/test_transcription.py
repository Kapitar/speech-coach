from __future__ import annotations

from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from backend.elevenLabs.transcription import TranscriptionError, transcribe_audio


class TranscriptionTests(TestCase):
    @patch("backend.elevenLabs.transcription.resolve_gemini_model", return_value="models/mock")
    @patch("backend.elevenLabs.transcription.configure_gemini")
    @patch("backend.elevenLabs.transcription.genai.GenerativeModel")
    @patch("backend.elevenLabs.transcription.ensure_elevenlabs_compatible", return_value=Path("prepared.mp3"))
    @patch("backend.elevenLabs.transcription._get_elevenlabs_client")
    def test_transcription_falls_back_to_gemini(
        self,
        mock_client,
        mock_prepare,
        mock_model,
        mock_configure,
        mock_resolve,
    ):
        client = mock_client.return_value
        client.speech_to_text.convert.side_effect = RuntimeError("boom")

        generation = MagicMock()
        generation.generate_content.return_value = MagicMock(text="Gemini transcript")
        mock_model.return_value = generation

        settings = MagicMock()
        settings.elevenlabs_stt_model = "scribe_v1"
        settings.gemini_primary_model = None
        settings.gemini_fallback_models = ["models/mock"]

        with patch("backend.elevenLabs.transcription.get_settings", return_value=settings):
            transcript = transcribe_audio("audio.mp3")

        self.assertEqual(transcript, "Gemini transcript")
        mock_resolve.assert_called_once()
        mock_configure.assert_called_once()

    @patch("backend.elevenLabs.transcription.resolve_gemini_model", side_effect=RuntimeError("fail"))
    @patch("backend.elevenLabs.transcription.configure_gemini")
    @patch("backend.elevenLabs.transcription.ensure_elevenlabs_compatible", return_value=Path("prepared.mp3"))
    @patch("backend.elevenLabs.transcription._get_elevenlabs_client")
    def test_transcription_error_when_all_backends_fail(
        self,
        mock_client,
        mock_prepare,
        mock_configure,
        mock_resolve,
    ):
        client = mock_client.return_value
        client.speech_to_text.convert.side_effect = RuntimeError("boom")

        settings = MagicMock()
        settings.elevenlabs_stt_model = "scribe_v1"
        settings.gemini_primary_model = None
        settings.gemini_fallback_models = ["models/mock"]

        with patch("backend.elevenLabs.transcription.get_settings", return_value=settings):
            with self.assertRaises(TranscriptionError):
                transcribe_audio("audio.mp3")


