import requests
from dotenv import load_dotenv
import os

env_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path=env_path)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_TRANSCRIPTION_URL = "https://api.elevenlabs.io/v1/speech-to-text"
print("API key loaded:", ELEVENLABS_API_KEY)

def transcribe_video(file_path):
    url = "https://api.elevenlabs.io/v1/speech-to-text"
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    files = {"file": open(file_path, "rb")}
    data = {"model_id": "eleven_multilingual_v2", "language": "en"}

    response = requests.post(url, headers=headers, files=files, data=data)
    print("Status:", response.status_code)
    print("Response text:", response.text)  # 👈 print error details

    response.raise_for_status()
    return response.json().get("text", "")