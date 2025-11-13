from .client import client
import json
import time
import random
from google.api_core import exceptions

def get_ai_response(contents: str, response_schema: dict = None, max_retries: int = 5) -> dict:
    config = {
        "response_mime_type": "application/json",
        **({"response_schema": response_schema} if response_schema else {}),
    }

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config,
            )
            return json.loads(response.text)

        except exceptions.ServiceUnavailable as e:
            # 503 — model overloaded
            wait = (2 ** attempt) + random.random()
            print(f"[Gemini] Model overloaded (503). Retrying in {wait:.1f}s... ({attempt+1}/{max_retries})")
            time.sleep(wait)

        except exceptions.ResourceExhausted as e:
            # Rate limit or quota exceeded
            wait = (2 ** attempt) + random.random()
            print(f"[Gemini] Quota or rate limit hit. Retrying in {wait:.1f}s...")
            time.sleep(wait)

        except Exception as e:
            print(f"[Gemini] Unexpected error: {e}")
            raise e

    raise RuntimeError("[Gemini] Max retries reached. Model still unavailable.")
