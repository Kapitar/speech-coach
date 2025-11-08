"""Minimal gesture analysis orchestration."""

import os
from typing import Any, Dict

import cv2

from .gemini_client import GeminiAnalysisClient


class GestureAnalyzer:
    """Simplified analyzer that sends the whole video to Gemini and returns feedback."""

    _ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"}

    def __init__(self, model_name: str = "gemini-2.5-pro"):
        self.gemini_client = GeminiAnalysisClient(model_name)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _validate_video_file(self, video_path: str) -> None:
        if not os.path.exists(video_path):
            raise ValueError(f"Video file not found: {video_path}")

        extension = os.path.splitext(video_path)[1].lower()
        if extension not in self._ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported video format: {extension}. "
                f"Supported formats: {', '.join(sorted(self._ALLOWED_EXTENSIONS))}"
            )

        capture = cv2.VideoCapture(video_path)
        if not capture.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        capture.release()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def analyze_gestures(self, video_path: str) -> Dict[str, Any]:
        try:
            self._validate_video_file(video_path)

            if not os.getenv("GOOGLE_AI_STUDIO_API_KEY"):
                raise ValueError("GOOGLE_AI_STUDIO_API_KEY environment variable is not set")

            # Minimal flow: analyze the entire video as a single segment.
            analysis = self.gemini_client.analyze_entire_video(video_path)

            overall_feedback = analysis.get("overall_feedback", {})
            action_items = overall_feedback.get("action_items") if isinstance(overall_feedback, dict) else None

            if action_items:
                analysis["recommendations"] = action_items
            else:
                analysis.setdefault(
                    "recommendations",
                    [
                        "Review the feedback above and practice refining your gestures and posture "
                        "based on the highlighted observations."
                    ],
                )

            return analysis

        except (ValueError, RuntimeError):
            raise
        except Exception as exc:
            raise RuntimeError(f"Unexpected error during gesture analysis: {exc}") from exc

