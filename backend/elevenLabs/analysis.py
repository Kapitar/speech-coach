"""Context alignment analysis for transcripts."""

from __future__ import annotations

import json
from typing import Any, Dict

import google.generativeai as genai

from .config import get_settings
from .transcript_optimizer import OptimizationContext
from .utils import configure_gemini, resolve_gemini_model

_DEFAULT_RESPONSE = {
    "overall_summary": "No specific context provided to analyse.",
    "fields": {},
}


def analyze_context_alignment(
    transcript: str,
    context: OptimizationContext,
) -> Dict[str, Any]:
    """
    Use Gemini to evaluate how well ``transcript`` aligns with the provided context.
    """
    relevant = {
        "genre": context.genre,
        "purpose": context.purpose,
        "audience": context.audience,
        "extra_instructions": context.extra_instructions,
    }
    relevant = {k: v for k, v in relevant.items() if v}
    if not relevant:
        return dict(_DEFAULT_RESPONSE)

    settings = get_settings()
    model_name = resolve_gemini_model(
        settings.gemini_primary_model,
        settings.gemini_fallback_models,
    )
    configure_gemini(settings.gemini_api_key)
    model = genai.GenerativeModel(model_name)

    context_lines = "\n".join(f"- {key}: {value}" for key, value in relevant.items())

    prompt = f"""
You will receive a speech transcript and contextual information. Evaluate how well the speech aligns with each context attribute.

Return valid JSON using the schema:
{{
  "overall_summary": "string describing overall fit",
  "fields": {{
    "<context_key>": {{
      "matches_context": true/false,
      "score": 0-10,
      "justification": "short explanation"
    }}
  }}
}}

Context:
{context_lines}

Transcript:
{transcript}
""".strip()

    try:
        response = model.generate_content(
            [{"text": prompt}],
            request_options={"timeout": 600},
        )
    except Exception as exc:  # pragma: no cover - API failure
        return {
            "overall_summary": f"Gemini analysis failed: {exc}",
            "fields": {},
        }

    response_text = getattr(response, "text", None) or ""
    return _parse_json_response(response_text)


def _parse_json_response(response_text: str) -> Dict[str, Any]:
    if not response_text:
        return dict(_DEFAULT_RESPONSE)

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Attempt to extract JSON block if Gemini added commentary.
        start = response_text.find("{")
        end = response_text.rfind("}")
        if start != -1 and end != -1 and start < end:
            snippet = response_text[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                pass

    return {
        "overall_summary": "Unable to parse Gemini response.",
        "fields": {},
        "raw_response": response_text,
    }


__all__ = ["analyze_context_alignment"]


