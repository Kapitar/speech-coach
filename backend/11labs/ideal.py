import os
from dotenv import load_dotenv
from google import genai
import json

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path=env_path)
GOOGLE_API_KEY = os.getenv("GOOGLE_AI_STUDIO_API_KEY")
AI_MODEL_NAME = os.getenv("GOOGLE_AI_STUDIO_NAME")  # e.g., "gemini-1.5-turbo"

client = genai.Client(api_key=GOOGLE_API_KEY)

def improve_transcript_with_structure(transcript, genre=None, purpose=None, audience=None):
    """
    Optimize a transcript while preserving sentence breaks and timing hints.
    Optional fields guide the style. Returns structured JSON:
    {
        "optimized_transcript": "...",
        "explanation": "..."
    }
    """
    prompt = (
        "You are an expert editor. Here is the original transcript:\n\n"
        f"{transcript}\n\n"
        "Please rewrite it to improve grammar, clarity, and style. "
        "Preserve the original sentence breaks, paragraphing, and any implied timing for speech delivery. "
    )

    if genre:
        prompt += f"Consider the genre: {genre}. "
    if purpose:
        prompt += f"Consider the purpose: {purpose}. "
    if audience:
        prompt += f"Consider the target audience: {audience}. "

    prompt += (
        "Keep the new transcript mostly similar to the original but improved. "
        "Return a JSON object exactly in the following format:\n"
        "{\n"
        "  \"optimized_transcript\": \"...\",\n"
        "  \"explanation\": \"Explain the main improvements made while preserving structure.\"\n"
        "}\n"
        "Only return valid JSON."
    )

    try:
        response = client.generate_text(
            model=AI_MODEL_NAME,
            prompt=prompt,
            max_output_tokens=600
        )

        content = response.text.strip()

        try:
            result_json = json.loads(content)
        except json.JSONDecodeError:
            # Fallback if Gemini didn't return proper JSON
            result_json = {"optimized_transcript": transcript, "explanation": content}

        return result_json

    except Exception as e:
        return {"optimized_transcript": transcript, "explanation": f"Error: {str(e)}"}


# Example usage
if __name__ == "__main__":
    original_transcript = (
        "Once upon a time, there was a small village where everyone loved storytelling.\n"
        "Children would gather every evening to hear tales of wonder and magic.\n"
        "One day, a mysterious traveler arrived, bringing new stories."
    )

    result = improve_transcript_with_structure(
        original_transcript,
        genre="fairy tale",
        purpose="entertain",
        audience="children"
    )

    print(json.dumps(result, indent=2))