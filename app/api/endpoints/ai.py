from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from app.gemini.prompts import create_analysis_prompt
from app.gemini.services import get_ai_response
from app.api.dependencies.database import get_db
from sqlalchemy.orm import Session
from app.db.models.user import User
from app.api.dependencies.auth import get_current_user
from app.schemas.receipt import ReceiptBase
from PIL import Image
import io

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

@router.post("/upload")
async def analysis_receipt(file: UploadFile = File(...)):
	if not file.content_type or not file.content_type.startswith("image/"):
		raise HTTPException(status_code=400, detail="Only image files are accepted.")
	image_data = await file.read()
	try:
		image = Image.open(io.BytesIO(image_data))
	except Exception:
		raise HTTPException(status_code=400, detail="Invalid image file.")
	prompt = create_analysis_prompt()
	ai_response = get_ai_response(contents=[prompt, image], response_schema=ReceiptBase)
	return {
		"filename": file.filename,
		"size": len(image_data),
		# "prompt": prompt,
		"ai_response": ai_response
	}