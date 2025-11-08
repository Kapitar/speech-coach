import json
from analyze import analyze_transcript
from ideal import improve_transcript_with_structure

def process_transcript(transcript, genre=None, purpose=None, audience=None):
    """
    Process a transcript in two steps:
    1. Analyze if it matches optional criteria
    2. Generate an improved version preserving sentence structure

    Returns a structured dictionary:
    {
        "analysis": {...},
        "optimized": {...}
    }
    """
    # Step 1: Analyze transcript
    analysis = analyze_transcript(transcript, genre, purpose, audience)

    # Step 2: Generate improved transcript
    optimized = improve_transcript_with_structure(transcript, genre, purpose, audience)

    # Combine results
    result = {
        "analysis": analysis,
        "optimized": optimized
    }

    return result

# Example usage
if __name__ == "__main__":
    original_transcript = (
        "Once upon a time, there was a small village where everyone loved storytelling.\n"
        "Children would gather every evening to hear tales of wonder and magic.\n"
        "One day, a mysterious traveler arrived, bringing new stories."
    )

    genre = "fairy tale"
    purpose = "entertain"
    audience = "children"

    result = process_transcript(original_transcript, genre, purpose, audience)
    print(json.dumps(result, indent=2))