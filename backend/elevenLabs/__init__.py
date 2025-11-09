"""Public entry points for the ElevenLabs pipeline package."""

from .analysis import analyze_context_alignment
from .config import Settings, get_settings
from .pipeline import PipelineResult, run_pipeline
from .testing import SpeechDemoTester
from .transcription import transcribe_audio, transcribe_video
from .transcript_optimizer import OptimizationContext, optimize_transcript
from .voice_clone import clone_voice_from_sample, synthesize_speech

__all__ = [
    "Settings",
    "PipelineResult",
    "OptimizationContext",
    "SpeechDemoTester",
    "analyze_context_alignment",
    "clone_voice_from_sample",
    "get_settings",
    "optimize_transcript",
    "run_pipeline",
    "synthesize_speech",
    "transcribe_audio",
    "transcribe_video",
]


