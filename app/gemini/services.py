from .client import client
import json


def get_ai_response(contents: str, response_schema: dict = None) -> str:
    config = {
        "response_mime_type": "application/json",
        **({"response_schema": response_schema} if response_schema else {})
    }
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=config,
    )
    response_json = json.loads(response.text)
    print(response.text)
    return response_json["message"]
