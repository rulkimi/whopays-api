from fastapi import APIRouter, HTTPException, Depends
from app.gemini.prompts import create_analysis_prompt
from app.gemini.services import get_ai_response
from app.api.dependencies.database import get_db
from sqlalchemy.orm import Session
from app.db.models.user import User
from app.api.dependencies.auth import get_current_user

router = APIRouter()

@router.post("/gemini")
def test_ai():
	"""
	Test the AI model with a static prompt.
	"""
	try:
		prompt = "HELLOOOO"
		response = get_ai_response(prompt)
		return {"prompt": prompt, "ai_response": response}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@router.post("/gemini/user")
def ai_with_user(user: User = Depends(get_current_user)):
	"""
	Test the AI model with authenticated user data.
	"""
	try:
		user_data = {
			"id": user.id,
			"email": user.email,
		}
		prompt = f"Respond with a summary of this user data: {user_data}. Format the response like this: {{ \"message\" : \"...\" }}"
		response = get_ai_response(prompt)
		return {"prompt": prompt, "ai_response": response, "user": user_data}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))