from google import genai
from app.core.config import settings

client = genai.Client(api_key=settings.GOOGLE_GEMINI_API_KEY)
