from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.services.receipt_services import analyze_receipt, create_receipt_with_items, get_receipt_by_id, get_user_receipts, delete_receipt
from app.services.receipt_friend_services import add_friends_to_receipt, remove_friends_from_receipt, get_receipt_friends, update_receipt_friends
from app.services.file_services import upload_file
from app.schemas.receipt import ReceiptRead
from app.db.models.user import User
from PIL import Image
import io
from typing import List

router = APIRouter()

@router.post("/", status_code=201, response_model=ReceiptRead)
async def upload_and_analyze_receipt_image(
	file: UploadFile = File(...),
	friend_ids: List[int] = [],
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
	
	# Reset file pointer for upload
	file.file.seek(0)
	
	# Upload image to MinIO
	receipt_url = upload_file(file, "receipts")
	
	receipt_data = analyze_receipt(image)
	
	receipt_read = create_receipt_with_items(
		db=db,
		receipt_data=receipt_data,
		user_id=current_user.id,
		receipt_url=receipt_url,
		friend_ids=friend_ids
	)
	
	return receipt_read

@router.get("/{receipt_id}", response_model=ReceiptRead)
async def retrieve_receipt_by_id(
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
async def list_user_receipts(
	skip: int = 0,
	limit: int = 100,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""Get all receipts for the current user"""
	return get_user_receipts(db, current_user.id, skip, limit)

@router.delete("/{receipt_id}")
async def soft_delete_receipt_by_id(
	receipt_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""Delete a receipt"""
	success = delete_receipt(db, receipt_id, current_user.id)
	if not success:
		raise HTTPException(status_code=404, detail="Receipt not found")
	return {"message": "Receipt deleted successfully"}

@router.post("/{receipt_id}/friends")
async def add_friends_to_receipt_by_id(
	receipt_id: int,
	friend_ids: List[int],
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""Add friends to a receipt"""
	success = add_friends_to_receipt(db, receipt_id, friend_ids, current_user.id)
	if not success:
		raise HTTPException(status_code=400, detail="Failed to add friends to receipt")
	return {"message": "Friends added to receipt successfully"}

@router.delete("/{receipt_id}/friends")
async def remove_friends_from_receipt_by_id(
	receipt_id: int,
	friend_ids: List[int],
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""Remove friends from a receipt"""
	success = remove_friends_from_receipt(db, receipt_id, friend_ids, current_user.id)
	if not success:
		raise HTTPException(status_code=400, detail="Failed to remove friends from receipt")
	return {"message": "Friends removed from receipt successfully"}

@router.get("/{receipt_id}/friends")
async def list_friends_for_receipt(
	receipt_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""Get all friends associated with a receipt"""
	friends = get_receipt_friends(db, receipt_id, current_user.id)
	return friends

@router.put("/{receipt_id}/friends")
async def replace_receipt_friends_by_id(
	receipt_id: int,
	friend_ids: List[int],
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""Replace all friends associated with a receipt"""
	success = update_receipt_friends(db, receipt_id, friend_ids, current_user.id)
	if not success:
		raise HTTPException(status_code=400, detail="Failed to update receipt friends")
	return {"message": "Receipt friends updated successfully"}