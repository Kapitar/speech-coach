from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import voice, cv, combined

app = FastAPI(title="Speech Coach API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(voice.router)
app.include_router(cv.router)
app.include_router(combined.router)


@app.get("/")
async def root():
    return {
        "message": "Speech Coach API",
        "version": "1.0.0",
        "endpoints": {
            "voice": "/voice/analyze",
            "cv": "/cv/analyze",
            "combined": "/analyze"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

