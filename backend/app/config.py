import os
from pathlib import Path

# Project paths
BACKEND_DIR = Path(__file__).parent.parent
PROMPTS_DIR = BACKEND_DIR / "prompts"
UPLOADS_DIR = BACKEND_DIR / "uploads"

# Ensure directories exist
UPLOADS_DIR.mkdir(exist_ok=True)
PROMPTS_DIR.mkdir(exist_ok=True)

# API keys
GOOGLE_AI_STUDIO_API_KEY = os.getenv("GOOGLE_AI_STUDIO_API_KEY")
if not GOOGLE_AI_STUDIO_API_KEY:
    raise ValueError("GOOGLE_AI_STUDIO_API_KEY not set in environment")

# Model configuration
GEMINI_MODEL = "gemini-2.5-flash"
#GEMINI_MODEL = "gemini-2.5-pro" 
GENERATION_CONFIG = {
    "temperature": 0.4,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}
