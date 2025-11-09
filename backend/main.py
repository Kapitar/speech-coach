from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path to import gesture_analyzer
sys.path.append(str(Path(__file__).parent.parent))

from gesture_analyzer import GestureAnalyzer

app = FastAPI(title="Speech Coach API", version="1.0.0")

# Initialize the gesture analyzer (will raise error if API key not set)
try:
    analyzer = GestureAnalyzer()
except ValueError as e:
    print(f"Warning: GestureAnalyzer initialization failed: {e}")
    analyzer = None


@app.get("/")
async def root():
    return {
        "message": "Speech Coach API v2.0",
        "endpoints": {
            "analyze": "/analyze/video - Upload video for comprehensive feedback",
            "chat": {
                "start": "/chat/start - Start Q&A session with feedback JSON",
                "message": "/chat/message - Ask questions about your feedback"
            }
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
