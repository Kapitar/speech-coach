import json
from transcribe import transcribe_video
from analyze import analyze_transcript
from ideal import improve_transcript_with_structure
from processTranscript import process_transcript

def test_all(video_path, genre=None, purpose=None, audience=None):
    print("🚀 Testing backend with sample data...\n")

    # Step 1: Transcribe
    print("🎧 Transcribing video...")
    transcript = transcribe_video(video_path)
    print("Transcript:")
    print(transcript[:500], "...\n")  # print first few chars

    # Step 2: Analyze
    print("🔍 Analyzing transcript...")
    analysis = analyze_transcript(transcript, genre, purpose, audience)
    print(json.dumps(analysis, indent=2))

    # Step 3: Improve transcript
    print("\n✨ Improving transcript...")
    improved = improve_transcript_with_structure(transcript, genre, purpose, audience)
    print(json.dumps(improved, indent=2))

    # Step 4: Full pipeline (optional)
    print("\n🔁 Combined process:")
    result = process_transcript(transcript, genre, purpose, audience)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    video_path = "sample.MOV"
    genre = "funny skit"
    purpose = "entertain"
    audience = "college students"

    test_all(video_path, genre, purpose, audience)