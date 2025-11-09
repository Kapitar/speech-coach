# Speech Coach Backend

AI-powered speech analysis and interactive coaching chat, built with FastAPI and Google's Gemini. The analysis is grounded in `prompts/general_prompt.txt` and returns a strict JSON schema covering non-verbal, delivery, and content categories.

## Features
- **Video analysis** → structured feedback JSON (eye contact, gestures, posture, clarity/enunciation, intonation, filler words, organization/flow, persuasiveness/impact, clarity of message, overall summary)
- **Interactive chat** → ask questions about your feedback; responses stay grounded in the feedback JSON
- **🆕 Speech transcription** → convert audio to text using ElevenLabs
- **🆕 Content improvement** → AI-powered speech enhancement with Gemini
- **🆕 Voice cloning** → generate improved speech in user's own voice
- **🆕 Full workflow** → transcribe → improve → clone → generate in one call
- Simple REST API with OpenAPI docs at `/docs`

## Tech Stack
- FastAPI, Uvicorn
- google-generativeai (Gemini)
- **🆕 ElevenLabs** (transcription & voice cloning)
- **🆕 pydub** (audio processing)
- Pydantic (validation)
- Python 3.10+ recommended

## Project Structure
```
backend/
├── .env                         # Local environment (not committed)
├── .env.example                 # Template env file
├── main.py                      # FastAPI app entrypoint
├── requirements.txt             # Python dependencies
├── test_structure.py            # Simple structure sanity check
├── app/
│   ├── __init__.py
│   ├── config.py                # Paths, API key/model config
│   ├── models.py                # Pydantic schemas for requests/responses
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── analyze.py           # /analyze/video endpoint
│   │   └── chat.py              # /chat/start and /chat/message endpoints
│   └── services/
│       ├── __init__.py
│       ├── analyzer.py          # Gemini-based analyzer using general_prompt.txt
│       └── chat.py              # Gemini-powered interactive chat
├── prompts/
│   └── general_prompt.txt       # Master prompt and output schema
└── uploads/                     # Temp storage for uploaded files (auto-cleaned per request)
```

## Prerequisites
- Python 3.10+
- **FFmpeg** (required for video/audio processing)
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get install ffmpeg`
  - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
- A Google AI Studio API key (Gemini)
  - Set in `.env` as `GOOGLE_AI_STUDIO_API_KEY`
- **🆕 An ElevenLabs API key** (for speech improvement features)
  - Set in `.env` as `ELEVENLABS_API_KEY`
  - Voice cloning requires paid plan (Starter $5/month+)

## Setup (macOS)
1) Install FFmpeg (if not already installed)
```bash
brew install ffmpeg
```

2) Create and activate a virtual environment
```bash
cd /Users/jasonoh/Desktop/Coding/GitHub/speech-coach/backend
python3 -m venv .venv
source .venv/bin/activate
```

3) Install Python dependencies
```bash
pip install -r requirements.txt
```

4) Configure environment
```bash
cp .env.example .env
# Edit .env and set:
# GOOGLE_AI_STUDIO_API_KEY=your_key_here
# ELEVENLABS_API_KEY=your_elevenlabs_key_here
```

4) Run the API
```bash
uvicorn main:app --reload
```

5) Open API docs
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## API Reference

### POST /analyze/video
Upload a video (and optional separate audio) for analysis. Returns structured feedback JSON following `prompts/general_prompt.txt`.

- Form fields:
  - video: file (required)
  - audio: file (optional)

Example (curl):
```bash
curl -X POST "http://127.0.0.1:8000/analyze/video" \
  -H "Accept: application/json" \
  -F "video=@/path/to/video.mp4"
```

Response: JSON with
- non_verbal.eye_contact|gestures|posture
- delivery.clarity_enunciation|intonation|eloquence_filler_words (+filler_word_counts)
- content.organization_flow|persuasiveness_impact|clarity_of_message
- overall_feedback.summary|strengths|areas_to_improve|prioritized_actions

### POST /chat/start
Start an interactive chat tied to a specific feedback JSON.

Body:
```json
{
  "feedback_json": { ...feedback returned by /analyze/video... }
}
```

Response:
```json
{
  "conversation_id": "uuid",
  "message": "Conversation started. Ask me anything about your feedback!"
}
```

Example (curl):
```bash
curl -X POST "http://127.0.0.1:8000/chat/start" \
  -H "Content-Type: application/json" \
  -d '{"feedback_json": {"non_verbal": {...}, "delivery": {...}, "content": {...}, "overall_feedback": {...}}}'
```

### POST /chat/message
Ask a question within an existing conversation.

Body:
```json
{
  "conversation_id": "uuid",
  "user_message": "How can I improve my intonation?"
}
```

Response:
```json
{
  "assistant_reply": "..."
}
```

Example (curl):
```bash
curl -X POST "http://127.0.0.1:8000/chat/message" \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"<from /chat/start>","user_message":"What timestamps show weak eye contact?"}'
```

### 🆕 POST /speech/transcribe
Transcribe audio to text using ElevenLabs.

Request (form-data):
- `audio`: file (MP3, WAV, M4A, etc.) - Required
- `language_code`: string (optional) - e.g., "eng", "spa", or empty/null for auto-detect
- `diarize`: boolean (optional, default: false) - Annotate who is speaking
- `tag_audio_events`: boolean (optional, default: false) - Tag laughter, applause, etc.

Example:
```bash
curl -X POST "http://127.0.0.1:8000/speech/transcribe" \
  -F "audio=@speech.mp3" \
  -F "language_code=eng"
```

Response:
```json
{
  "original_transcription": "The transcribed text..."
}
```

### 🆕 POST /speech/improve
Transcribe and improve speech content with AI.

Request (form-data):
- `audio`: file - Required
- `improvement_focus`: string (optional, e.g., "clarity and persuasiveness")
- `language_code`: string (optional)
- `diarize`: boolean (optional)
- `tag_audio_events`: boolean (optional)

Example:
```bash
curl -X POST "http://127.0.0.1:8000/speech/improve" \
  -F "audio=@speech.mp3" \
  -F "improvement_focus=clarity"
```

Response:
```json
{
  "original_transcription": "...",
  "improved_content": {
    "improved_speech": "...",
    "suggestions": ["..."],
    "key_changes": [{"change": "...", "reason": "..."}],
    "summary": "..."
  }
}
```

### 🆕 POST /speech/clone-and-improve
Complete workflow: transcribe → improve → clone voice → generate improved audio.

**Requirements:**
- ⚠️ Requires ElevenLabs paid plan for IVC (Instant Voice Cloning)
- Minimum 30 seconds of clear audio recommended
- Best results with 1-3 minutes of varied speech

Request (form-data):
- `audio`: file - Required
- `improvement_focus`: string (optional)
- `language_code`: string (optional)
- `diarize`: boolean (optional)
- `tag_audio_events`: boolean (optional)

Example:
```bash
curl -X POST "http://127.0.0.1:8000/speech/clone-and-improve" \
  -F "audio=@speech.mp3" \
  --output improved_speech.mp3
```

Response:
- Audio file (audio/mpeg) with improved speech in user's voice

### 🆕 POST /speech/clone-and-improve-detailed
Same as above but returns JSON with base64-encoded audio and full metadata.

**Testing:** Use `python test_transcribe.py <audio_file>` to test transcription functionality.

## End-to-End Example

1) Analyze a video:
```bash
ANALYSIS=$(curl -s -X POST "http://127.0.0.1:8000/analyze/video" \
  -F "video=@/path/to/video.mp4")
echo "$ANALYSIS" | head -c 400
```

2) Start chat:
```bash
CONV=$(curl -s -X POST "http://127.0.0.1:8000/chat/start" \
  -H "Content-Type: application/json" \
  -d "{\"feedback_json\": $ANALYSIS }")
CID=$(echo "$CONV" | python3 -c 'import sys,json; print(json.load(sys.stdin)["conversation_id"])')
echo "$CID"
```

3) Ask a question:
```bash
curl -s -X POST "http://127.0.0.1:8000/chat/message" \
  -H "Content-Type: application/json" \
  -d "{\"conversation_id\":\"$CID\",\"user_message\":\"Top 3 fixes for filler words? Cite timestamps.\"}" | jq
```

## Testing

### 1) Structure sanity check
```bash
python test_structure.py
```

### 2) Verify API is running
```bash
curl http://127.0.0.1:8000/health
# Expect: {"status":"healthy"}
```

### 3) Try the docs
Open http://127.0.0.1:8000/docs and exercise each endpoint interactively.

### 4) Minimal Python script (requests)
```python
import json, requests

base = "http://127.0.0.1:8000"

# Analyze
with open("/path/to/video.mp4","rb") as f:
    r = requests.post(f"{base}/analyze/video", files={"video": f})
r.raise_for_status()
feedback = r.json()

# Chat start
r = requests.post(f"{base}/chat/start", json={"feedback_json": feedback})
r.raise_for_status()
cid = r.json()["conversation_id"]

# Chat message
r = requests.post(f"{base}/chat/message", json={"conversation_id": cid, "user_message": "How do I improve intonation?"})
r.raise_for_status()
print(r.json())
```

## Configuration

- Environment
  - `GOOGLE_AI_STUDIO_API_KEY` (required)
- Prompt
  - Edit `prompts/general_prompt.txt` to refine schema/scoring or guidance.
- Model and generation settings
  - See `app/config.py` for defaults (model name, temperature, etc.). Adjust as needed.

## How It Works (High Level)

- Analysis (`app/services/analyzer.py`)
  - Loads `prompts/general_prompt.txt`
  - Uploads the provided video (and optional audio) to Gemini
  - Requests a JSON-only response adhering to the schema
  - Returns the parsed JSON

- Interactive Chat (`app/services/chat.py`)
  - Starts a Gemini chat session with a strict system instruction
  - Stores `feedback_json` in-memory and injects it into each turn
  - Responds concisely and cites timestamps when present

Note: The in-memory conversation store is for development. Use a persistent store (e.g., Redis/DB) in production.

## Troubleshooting

### General Issues

- **Missing API key**
  - Error: `ValueError: GOOGLE_AI_STUDIO_API_KEY not set` or `ELEVENLABS_API_KEY not set`
  - Fix: Set keys in `.env` and restart the server

- **Gemini file not ACTIVE**
  - Error: `400 The File <id> is not in an ACTIVE state and usage is not allowed.`
  - Cause: Uploaded files may take time to process before they're usable.
  - Fix: Retry after a few seconds. If you still hit this, consider adding polling to wait for the file to become ACTIVE before generating content, or re-encode your video to a standard format/bitrate and re-upload.

- **JSON parse errors from analysis**
  - Ensure the model returns valid JSON (no code fences/markdown). The prompt enforces this but models can still emit fences; strip them before parsing if needed.

- **413 Payload too large**
  - Reduce video size/bitrate or configure a reverse proxy (Nginx) with larger body limits.

- **CORS blocked in browser**
  - Adjust `CORSMiddleware` in `main.py` to restrict or allow your frontend origin.

- **Apple Silicon build issues**
  - Upgrade pip (`python -m pip install --upgrade pip`) and reinstall.

### Speech Improvement Issues

- **Invalid language code error**
  - Error: `Invalid language code received: ''`
  - Cause: Empty string passed for language_code instead of null
  - Fix: Use `None` in Python or omit the parameter; empty strings are automatically converted to `None`
  - Valid codes: eng, spa, fra, deu, ita, jpn, kor, zho, etc. (see error message for full list)

- **Transcription failed**
  - Verify audio file is not corrupted
  - Check audio format is supported (MP3, WAV, M4A, OGG, FLAC, WEBM)
  - Ensure audio contains clear speech
  - Check ElevenLabs API key is valid

- **Voice cloning failed**
  - Error: `'VoicesClient' object has no attribute 'add'`
  - Fix: Already fixed in current version (uses `voices.ivc.create()`)
  - Requires paid ElevenLabs plan with IVC (Instant Voice Cloning) access
  - Provide at least 30 seconds of clear audio (1-3 minutes recommended)
  - Ensure consistent audio quality throughout
  - Check your ElevenLabs account has voice cloning permissions
  - Verify you're using the latest `elevenlabs` package version

- **Test transcription**
  ```bash
  python test_transcribe.py path/to/audio.mp3
  ```

- **Update ElevenLabs SDK**
  ```bash
  pip install --upgrade elevenlabs
  ```

## Production Notes
- Restrict CORS to known origins
- Add auth and rate limiting
- Persist conversations in a database
- Log to a centralized sink (and scrub PII)
- Add retries/polling for Gemini file activation
- Validate model responses against `app/models.py` before returning to clients

## License
Proprietary — internal use for the Speech Coach project unless stated otherwise.