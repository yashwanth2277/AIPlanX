import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def validate_api_keys():
    missing_keys = []

    if not GOOGLE_API_KEY:
        missing_keys.append("GOOGLE_API_KEY")

    if not GROQ_API_KEY:
        missing_keys.append("GROQ_API_KEY")

    if missing_keys:
        raise ValueError(
            f"Missing API keys in .env: {', '.join(missing_keys)}"
        )
