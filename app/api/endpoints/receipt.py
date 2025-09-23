from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.api.dependencies.services import get_receipt_friend_service, get_receipt_service, get_file_service
from app.services.receipt_services import ReceiptService
from app.services.receipt_friend_services import ReceiptFriendService
from app.services.file_services import FileService
from app.schemas.receipt import ReceiptRead, AddFriendsToReceiptInput, RemoveFriendsFromReceiptInput, GetReceiptFriendsInput, UpdateReceiptFriendsInput
from app.schemas.receipt import AnalyzeReceiptInput, CreateReceiptInput, GetReceiptInput, GetReceiptsInput, DeleteReceiptInput, CalculateSplitsInput
from app.schemas.file import FileUploadInput
from app.db.models.user import User
from PIL import Image
import io
from typing import List

router = APIRouter()

def analyze_and_create_receipt(
    db: Session,
    receipt_url: str,
    image_data: bytes,
    friend_ids: List[int],
    user_id: int,
    receipt_service: ReceiptService,
    content_type: str = "image/jpeg"
):
    try:
        # Use the service-based approach
        analyze_input = AnalyzeReceiptInput(
            image_data=image_data,
            content_type=content_type
        )
        result = receipt_service.analyze_receipt(analyze_input, db)
        
        if result.success:
            # Create receipt with items using the new method
            create_input = CreateReceiptInput(
                receipt_data=result.data,
                friend_ids=friend_ids,
                receipt_url=receipt_url
            )
            create_result = receipt_service.create_receipt_with_items(create_input, user_id, db)
            
            if create_result.success:
                return create_result.data
            else:
                raise HTTPException(status_code=400, detail=create_result.message)
        else:
            raise HTTPException(status_code=400, detail=result.message)
            
    except Exception as e:
        # Optionally log the error here
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", status_code=201)
async def upload_and_analyze_receipt_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    friend_ids: List[int] = [],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    receipt_service: ReceiptService = Depends(get_receipt_service),
    file_service: FileService = Depends(get_file_service)
):
    """Upload receipt image and start background analysis"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are accepted.")

    image_data = await file.read()
    try:
        Image.open(io.BytesIO(image_data))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    # Reset file pointer for upload
    file.file.seek(0)
    
    # Upload image to MinIO using the service
    upload_input = FileUploadInput(
        folder="receipts",
        content_type=file.content_type or "image/jpeg"
    )
    upload_result = file_service.upload_file(file, upload_input)
    
    if not upload_result.success:
        raise HTTPException(status_code=500, detail=upload_result.message)
    
    receipt_url = upload_result.data  # file_id can be used as URL reference

    # Start background task for analysis and DB creation
    background_tasks.add_task(
        analyze_and_create_receipt,
        db,
        receipt_url,
        image_data,
        friend_ids,
        current_user.id,
        receipt_service,
        file.content_type or "image/jpeg"
    )

    return {"message": "Receipt image uploaded successfully. Analysis is in progress.", "receipt_url": receipt_url}

@router.get("/{receipt_id}", response_model=ReceiptRead)
async def retrieve_receipt_by_id(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    receipt_service: ReceiptService = Depends(get_receipt_service)
):
    """Get a specific receipt by ID"""
    input_data = GetReceiptInput(receipt_id=receipt_id)
    result = receipt_service.get_receipt_by_id(input_data, current_user.id, db)
    
    if not result.success:
        if result.error_code == "RECEIPT_NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.message)
        else:
            raise HTTPException(status_code=400, detail=result.message)
    
    return result.data

@router.get("", response_model=List[ReceiptRead])
async def list_user_receipts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    receipt_service: ReceiptService = Depends(get_receipt_service)
):
    """Get all receipts for the current user"""
    input_data = GetReceiptsInput(skip=skip, limit=limit)
    result = receipt_service.get_user_receipts(input_data, current_user.id, db)
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result.data

@router.delete("/{receipt_id}")
async def soft_delete_receipt_by_id(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    receipt_service: ReceiptService = Depends(get_receipt_service)
):
    """Delete a receipt"""
    input_data = DeleteReceiptInput(receipt_id=receipt_id)
    result = receipt_service.delete_receipt(input_data, current_user.id, db)
    
    if not result.success:
        if result.error_code == "RECEIPT_NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.message)
        else:
            raise HTTPException(status_code=400, detail=result.message)
    
    return {"message": result.message}

@router.post("/{receipt_id}/friends")
async def add_friends_to_receipt_by_id(
	receipt_id: int,
	friend_ids: List[int],
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
	receipt_friend_service: ReceiptFriendService = Depends(get_receipt_friend_service)
):
	"""Add friends to a receipt"""
	input_data = AddFriendsToReceiptInput(receipt_id=receipt_id, friend_ids=friend_ids)
	result = receipt_friend_service.add_friends_to_receipt(input_data, current_user.id, db)
	
	if not result.success:
		raise HTTPException(status_code=400, detail=result.message or "Failed to add friends to receipt")
	
	return {"message": result.message}

@router.delete("/{receipt_id}/friends")
async def remove_friends_from_receipt_by_id(
	receipt_id: int,
	friend_ids: List[int],
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
	receipt_friend_service: ReceiptFriendService = Depends(get_receipt_friend_service)
):
	"""Remove friends from a receipt"""
	input_data = RemoveFriendsFromReceiptInput(receipt_id=receipt_id, friend_ids=friend_ids)
	result = receipt_friend_service.remove_friends_from_receipt(input_data, current_user.id, db)
	
	if not result.success:
		raise HTTPException(status_code=400, detail=result.message or "Failed to remove friends from receipt")
	
	return {"message": result.message}

@router.get("/{receipt_id}/friends")
async def list_friends_for_receipt(
	receipt_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
	receipt_friend_service: ReceiptFriendService = Depends(get_receipt_friend_service)
):
	"""Get all friends associated with a receipt"""
	input_data = GetReceiptFriendsInput(receipt_id=receipt_id)
	result = receipt_friend_service.get_receipt_friends(input_data, current_user.id, db)
	
	if not result.success:
		raise HTTPException(status_code=400, detail=result.message or "Failed to get receipt friends")
	
	return result.data

@router.put("/{receipt_id}/friends")
async def replace_receipt_friends_by_id(
	receipt_id: int,
	friend_ids: List[int],
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
	receipt_friend_service: ReceiptFriendService = Depends(get_receipt_friend_service)
):
	"""Replace all friends associated with a receipt"""
	input_data = UpdateReceiptFriendsInput(receipt_id=receipt_id, friend_ids=friend_ids)
	result = receipt_friend_service.update_receipt_friends(input_data, current_user.id, db)
	
	if not result.success:
		raise HTTPException(status_code=400, detail=result.message or "Failed to update receipt friends")
	
	return {"message": result.message}

@router.get("/{receipt_id}/splits")
def get_receipt_splits(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    receipt_service: ReceiptService = Depends(get_receipt_service)
):
    """Calculate receipt splits"""
    input_data = CalculateSplitsInput(receipt_id=receipt_id)
    result = receipt_service.calculate_receipt_splits(input_data, current_user.id, db)
    
    if not result.success:
        if result.error_code == "RECEIPT_NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.message)
        else:
            raise HTTPException(status_code=400, detail=result.message)
    
    return result.data