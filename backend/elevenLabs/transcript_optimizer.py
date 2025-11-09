"""Use Gemini to refine transcripts with contextual guidance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import google.generativeai as genai

from .config import Settings, get_settings
from .utils import configure_gemini, resolve_gemini_model


@dataclass(slots=True)
class OptimizationContext:
    genre: Optional[str] = None
    purpose: Optional[str] = None
    audience: Optional[str] = None
    extra_instructions: Optional[str] = None

    def to_prompt_segment(self) -> str:
        parts = []
        if self.genre:
            parts.append(f"- Genre: {self.genre}")
        if self.purpose:
            parts.append(f"- Purpose: {self.purpose}")
        if self.audience:
            parts.append(f"- Audience: {self.audience}")
        if self.extra_instructions:
            parts.append(f"- Additional guidance: {self.extra_instructions}")
        if not parts:
            return "No additional context provided."
        return "Context for the optimization:\n" + "\n".join(parts)


def optimize_transcript(
    transcript: str,
    *,
    context: OptimizationContext | None = None,
    model_name: Optional[str] = None,
) -> Dict[str, str]:
    """
    Improve a transcript for clarity, tone, and structure using Gemini.

    Returns a dictionary with the optimised transcript and supporting metadata.
    """
    transcript = (transcript or "").strip()
    if not transcript:
        raise ValueError("Cannot optimise an empty transcript.")

    settings = get_settings()
    selected_model = model_name or resolve_gemini_model(
        settings.gemini_primary_model,
        settings.gemini_fallback_models,
    )
    configure_gemini(settings.gemini_api_key)
    model = genai.GenerativeModel(selected_model)

    ctx_segment = (context or OptimizationContext()).to_prompt_segment()

    prompt = (
        f"{ctx_segment}\n\n"
        "Rewrite the following transcript to maximise clarity, persuasive impact, "
        "and suitability for the described context. Preserve the speaker's voice "
        "and intent. Use accessible language and add gentle stage directions if "
        "they strengthen delivery.\n\n"
        "Return your answer as plain text with no additional commentary.\n\n"
        "Transcript:\n"
        f"{transcript}"
    )

    response = model.generate_content(
        [{"text": prompt}],
        request_options={"timeout": 600},
    )
    optimised = getattr(response, "text", "") or ""
    if not optimised:
        raise RuntimeError("Gemini did not return optimised transcript text.")

    return {
        "optimized_transcript": optimised.strip(),
        "model": selected_model,
        "context": {
            "genre": (context.genre if context else None),
            "purpose": (context.purpose if context else None),
            "audience": (context.audience if context else None),
            "extra_instructions": (context.extra_instructions if context else None),
        },
    }


__all__ = ["OptimizationContext", "optimize_transcript"]


