from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from dotenv import load_dotenv

load_dotenv()

from app.routers import analyze, chat, speech_improvement

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Speech Coach API",
    description="AI-powered speech analysis and coaching centered on comprehensive feedback",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analyze.router)
app.include_router(chat.router)
app.include_router(speech_improvement.router)

@app.get("/")
async def root():
    return {
        "message": "Speech Coach API v2.0",
        "endpoints": {
            "analyze": "/analyze/video - Upload video for comprehensive feedback",
            "chat": {
                "start": "/chat/start - Start Q&A session with feedback JSON",
                "message": "/chat/message - Ask questions about your feedback"
            },
            "speech_improvement": {
                "transcribe": "/speech/transcribe - Transcribe audio to text",
                "improve": "/speech/improve - Transcribe and improve speech content",
                "clone_and_improve": "/speech/clone-and-improve - Full workflow: transcribe, improve, clone voice, generate audio",
                "clone_and_improve_detailed": "/speech/clone-and-improve-detailed - Same as above with detailed JSON response",
                "generate_from_video": "/speech/generate-from-video - Accept video, extract audio, then run full improvement workflow"
            }
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
