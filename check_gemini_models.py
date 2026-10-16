import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("ERROR: GOOGLE_API_KEY not found in .env")
    raise SystemExit(1)

try:
    client = genai.Client(api_key=api_key)

    print("\nGemini models available to your API key:\n")
    count = 0

    for model in client.models.list():
        supported_actions = model.supported_actions or []

        if "generateContent" in supported_actions:
            print(f"Model: {model.name}")
            print(f"Display name: {model.display_name}")
            print(f"Description: {model.description or 'N/A'}")
            print("-" * 55)
            count += 1

    print(f"\nTotal models supporting generateContent: {count}")

except Exception as error:
    print(f"\nCould not retrieve models: {type(error).__name__}: {error}")
