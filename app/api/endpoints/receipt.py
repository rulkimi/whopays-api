from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.services.receipt_services import analyze_receipt, create_receipt_with_items, get_receipt_by_id, get_user_receipts, delete_receipt
from app.schemas.receipt import ReceiptRead
from app.db.models.user import User
from PIL import Image
import io
from typing import List

router = APIRouter()

@router.post("/", status_code=201, response_model=ReceiptRead)
async def analyze_receipt_endpoint(
	file: UploadFile = File(...),
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""Analyze receipt image and save to database"""
	if not file.content_type or not file.content_type.startswith("image/"):
		raise HTTPException(status_code=400, detail="Only image files are accepted.")
	
	image_data = await file.read()
	try:
		image = Image.open(io.BytesIO(image_data))
	except Exception:
		raise HTTPException(status_code=400, detail="Invalid image file.")
	
	receipt_data = analyze_receipt(image)
	
	receipt_read = create_receipt_with_items(
		db=db,
		receipt_data=receipt_data,
		user_id=current_user.id,
		receipt_url=""  # TODO: store receipt url
	)
	
	return receipt_read

@router.get("/{receipt_id}", response_model=ReceiptRead)
async def get_receipt(
	receipt_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""Get a specific receipt by ID"""
	receipt = get_receipt_by_id(db, receipt_id, current_user.id)
	if not receipt:
		raise HTTPException(status_code=404, detail="Receipt not found")
	return receipt

@router.get("/", response_model=List[ReceiptRead])
async def get_receipts(
	skip: int = 0,
	limit: int = 100,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""Get all receipts for the current user"""
	return get_user_receipts(db, current_user.id, skip, limit)

@router.delete("/{receipt_id}")
async def delete_receipt_endpoint(
	receipt_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""Delete a receipt"""
	success = delete_receipt(db, receipt_id, current_user.id)
	if not success:
		raise HTTPException(status_code=404, detail="Receipt not found")
	return {"message": "Receipt deleted successfully"}