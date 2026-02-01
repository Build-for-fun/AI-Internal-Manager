import asyncio
import os
import sys

# Add src to path
sys.path.append(os.getcwd())

from src.agents.orchestrator.intents import intent_classifier
from src.config import settings

async def main():
    print(f"Testing Keywords AI integration...")
    print(f"Provider: {settings.llm_provider}")
    print(f"Base URL: {settings.keywords_ai_base_url}")
    print(f"Model: {settings.keywords_ai_default_model}")
    
    # Check if API key is set (don't print it)
    api_key = settings.keywords_ai_api_key.get_secret_value()
    if not api_key:
        print("ERROR: KEYWORDS_AI_API_KEY is not set in .env or environment variables.")
        return

    print("API Key is present. Attempting to classify a query...")
    
    try:
        intent, confidence = await intent_classifier.classify("How do I deploy to production?")
        print(f"Success! Result: {intent} (Confidence: {confidence})")
    except Exception as e:
        print(f"Error calling Keywords AI: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
