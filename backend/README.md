# Speech Coach Backend

AI-powered public speaking coach backend that analyzes video recordings for various speech metrics.

## Features

The backend analyzes the following aspects of public speaking:

1. **Posture Analysis**
   - Shoulder alignment
   - Back straightness
   - Stability and movement
   - Confidence indicators

2. **Eye Contact Detection**
   - Percentage of time looking at camera
   - Average eye contact duration
   - Gaze shift frequency
   - Direct eye contact score

3. **Voice Quality**
   - Average volume and consistency
   - Clarity score
   - Pitch range and stability
   - Voice projection

4. **Speech Disfluencies**
   - Stutter detection
   - Filler word count ("um", "uh", "like", etc.)
   - Pause analysis
   - Speech rate (words per minute)

5. **Intonation & Prosody**
   - Pitch variation
   - Stress patterns
   - Monotone detection
   - Energy variation
   - Overall prosody score

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install system dependencies:
   - **ffmpeg** (required for video/audio processing):
     - macOS: `brew install ffmpeg`
     - Linux: `sudo apt-get install ffmpeg`
     - Windows: Download from https://ffmpeg.org/
   - **PortAudio** (for speech recognition):
     - macOS: `brew install portaudio`
     - Linux: `sudo apt-get install portaudio19-dev python3-pyaudio`
     - Windows: Usually included with Python

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app configuration
│   ├── models.py            # Pydantic models for requests/responses
│   ├── video_processor.py   # Video and audio processing utilities
│   ├── routers/
│   │   ├── voice.py         # Voice analysis endpoints
│   │   ├── cv.py            # Computer vision analysis endpoints
│   │   └── combined.py      # Combined analysis endpoints
│   └── analyzers/
│       ├── voice/           # Voice analysis modules
│       │   ├── voice_analyzer.py
│       │   ├── speech_analyzer.py
│       │   └── intonation_analyzer.py
│       └── cv/              # Computer vision analysis modules
│           ├── posture_analyzer.py
│           └── eye_contact_analyzer.py
├── main.py                  # Entry point
└── requirements.txt
```

## Running the Server

```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check
```
GET /health
```

### Voice Analysis
Analyze voice-related metrics only (voice quality, disfluencies, intonation):
```
POST /voice/analyze
Content-Type: multipart/form-data

Body: video file
```

**Response:**
```json
{
  "success": true,
  "metrics": {
    "voice_quality": { ... },
    "speech_disfluencies": { ... },
    "intonation": { ... }
  },
  "score": 82.5,
  "feedback": [
    "Your voice quality is excellent!",
    "Work on reducing filler words."
  ]
}
```

### Computer Vision Analysis
Analyze visual metrics only (posture, eye contact):
```
POST /cv/analyze
Content-Type: multipart/form-data

Body: video file
```

**Response:**
```json
{
  "success": true,
  "metrics": {
    "posture": { ... },
    "eye_contact": { ... }
  },
  "score": 88.0,
  "feedback": [
    "Your posture is good!",
    "Work on maintaining eye contact longer."
  ]
}
```

### Combined Analysis
Analyze all metrics (both voice and CV):
```
POST /analyze
Content-Type: multipart/form-data

Body: video file
```

**Response:**
```json
{
  "success": true,
  "metrics": {
    "posture": { ... },
    "eye_contact": { ... },
    "voice_quality": { ... },
    "speech_disfluencies": { ... },
    "intonation": { ... }
  },
  "overall_score": 85.5,
  "feedback": [
    "Your posture is good!",
    "Work on maintaining eye contact longer."
  ]
}
```

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Usage Examples

### Voice Analysis Only
```python
import requests

url = "http://localhost:8000/voice/analyze"
with open("speech_video.mp4", "rb") as video_file:
    files = {"video": video_file}
    response = requests.post(url, files=files)
    result = response.json()
    print(f"Voice Score: {result['score']}")
    print("Feedback:", result['feedback'])
```

### CV Analysis Only
```python
import requests

url = "http://localhost:8000/cv/analyze"
with open("speech_video.mp4", "rb") as video_file:
    files = {"video": video_file}
    response = requests.post(url, files=files)
    result = response.json()
    print(f"CV Score: {result['score']}")
    print("Feedback:", result['feedback'])
```

### Combined Analysis
```python
import requests

url = "http://localhost:8000/analyze"
with open("speech_video.mp4", "rb") as video_file:
    files = {"video": video_file}
    response = requests.post(url, files=files)
    result = response.json()
    print(f"Overall Score: {result['overall_score']}")
    print("Feedback:", result['feedback'])
```

## Notes

- Video processing may take some time depending on video length
- The analysis uses MediaPipe for pose and face detection
- Speech recognition requires internet connection (uses Google Speech Recognition API)
- For production, consider:
  - Adding authentication
  - Implementing rate limiting
  - Using a proper file storage solution
  - Adding caching for repeated analyses
  - Setting up proper CORS origins

