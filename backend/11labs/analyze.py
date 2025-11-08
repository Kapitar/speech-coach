import os
import json
from dotenv import load_dotenv
from google import genai

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path=env_path)
GOOGLE_API_KEY = os.getenv("GOOGLE_AI_STUDIO_API_KEY")
AI_MODEL_NAME = os.getenv("GOOGLE_AI_STUDIO_NAME")  # e.g., "gemini-1.5-turbo"

# Initialize Gemini client
client = genai.Client(api_key=GOOGLE_API_KEY)

def analyze_transcript(transcript, genre=None, purpose=None, audience=None):
    """
    Analyze a transcript using Google Gemini.
    Returns structured JSON: {"matches": bool, "explanation": str}
    """
    # Construct prompt
    prompt = f"Analyze the following transcript:\n\n{transcript}\n\n"
    if genre:
        prompt += f"Genre: {genre}\n"
    if purpose:
        prompt += f"Purpose: {purpose}\n"
    if audience:
        prompt += f"Audience: {audience}\n"

    prompt += (
        "Determine whether the transcript matches the given criteria. "
        "Return a JSON object in the following format:\n"
        "{\n"
        "  \"matches\": true or false,\n"
        "  \"explanation\": \"Explain why it matches or does not match.\"\n"
        "}\n"
        "Only return valid JSON."
    )

    try:
        response = client.generate_text(
            model=AI_MODEL_NAME,
            prompt=prompt,
            max_output_tokens=300
        )

        content = response.text.strip()

        # Parse JSON
        try:
            result_json = json.loads(content)
        except json.JSONDecodeError:
            result_json = {"matches": None, "explanation": content}

        return result_json

    except Exception as e:
        return {"matches": None, "explanation": f"Error during analysis: {str(e)}"}

# Example usage
if __name__ == "__main__":
    transcript = "Once upon a time, there was a small village where everyone loved storytelling."
    analysis = analyze_transcript(transcript, genre="fairy tale", purpose="entertain", audience="children")
    print(json.dumps(analysis, indent=2))