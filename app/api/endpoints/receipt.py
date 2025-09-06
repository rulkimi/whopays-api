from fastapi import APIRouter
from app.gemini.services import get_ai_response
from app.gemini.prompts import create_analysis_prompt

router = APIRouter()

