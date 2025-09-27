from .client import client
import json
from google import genai
from app.core.observability import log_outbound_call


def get_ai_response(contents, response_schema: dict = None, content_type: str = "image/jpeg", correlation_id: str | None = None) -> str:
    """Generate AI response with proper content formatting.
    
    Args:
        contents: Can be a string, list of strings/bytes, or properly formatted content
        response_schema: Optional Pydantic model for response validation
        
    Returns:
        Parsed JSON response as dictionary
    """
    # Format contents properly for Gemini API
    formatted_contents = []
    
    if isinstance(contents, str):
        formatted_contents = [contents]
    elif isinstance(contents, list):
        for item in contents:
            if isinstance(item, str):
                formatted_contents.append(item)
            elif isinstance(item, bytes):
                # Format image bytes as Part with inline_data
                part = genai.types.Part(
                    inline_data={
                        'mime_type': content_type,
                        'data': item
                    }
                )
                formatted_contents.append(part)
            else:
                formatted_contents.append(item)
    else:
        formatted_contents = contents
    
    config = {
        "response_mime_type": "application/json",
        **({"response_schema": response_schema} if response_schema else {})
    }
    def _call():
        return client.models.generate_content(
            model="gemini-2.5-flash",
            contents=formatted_contents,
            config=config,
        )
    response = log_outbound_call(
        provider="gemini",
        target="gemini-2.5-flash",
        operation="generate_content",
        correlation_id=correlation_id,
        call=_call,
    )
    return json.loads(response.text)
