from fastapi import Depends, UploadFile, File, HTTPException, BackgroundTasks
from app.api.router import create_router
from sqlalchemy.orm import Session
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.api.dependencies.services import get_receipt_friend_service, get_receipt_service, get_file_service, get_job_service
from app.services.receipt_services import ReceiptService
from app.services.receipt_friend_services import ReceiptFriendService
from app.services.file_services import FileService
from app.services.job_services import JobService
from app.schemas.receipt import ReceiptRead, AddFriendsToReceiptInput, RemoveFriendsFromReceiptInput, GetReceiptFriendsInput, UpdateReceiptFriendsInput
from app.schemas.receipt import AnalyzeReceiptInput, CreateReceiptInput, GetReceiptInput, GetReceiptsInput, DeleteReceiptInput, CalculateSplitsInput, ReceiptSplitsResponse
from app.schemas.file import FileUploadInput
from app.db.models.user import User
from PIL import Image
import io
from typing import List

router = create_router(name="receipt")

def analyze_and_create_receipt(
    db: Session,
    receipt_url: str,
    image_data: bytes,
    friend_ids: List[int],
    user_id: int,
    receipt_service: ReceiptService,
    content_type: str = "image/jpeg",
    job_id: int | None = None,
    job_service: JobService | None = None,
    receipt_id: int | None = None,
):
    try:
        if job_id and job_service:
            job_service.start(job_id, db)
        # Use the service-based approach
        analyze_input = AnalyzeReceiptInput(
            image_data=image_data,
            content_type=content_type
        )
        result = receipt_service.analyze_receipt(analyze_input, db)
        
        if result.success:
            if job_id and job_service:
                job_service.progress(job_id, 70, db)
            
            if receipt_id:
                # Update existing receipt with items
                create_input = CreateReceiptInput(
                    receipt_data=result.data,
                    friend_ids=friend_ids,
                    receipt_url=receipt_url
                )
                update_result = receipt_service.update_receipt_with_items(receipt_id, create_input, user_id, db)
                
                if update_result.success:
                    if job_id and job_service:
                        job_service.succeed(job_id, update_result.data["receipt_id"], db)
                    return update_result.data
                else:
                    if job_id and job_service:
                        job_service.fail(job_id, update_result.error_code or "RECEIPT_UPDATE_FAILED", update_result.message or "Failed", db)
                    # Update receipt status to failed
                    from app.repositories.receipt import ReceiptRepository
                    receipt_repo = ReceiptRepository(db, correlation_id=None)
                    receipt_repo.update(receipt_id, {"status": "failed"})
                    return None
            else:
                # Fallback: create receipt with items (for backwards compatibility)
                create_input = CreateReceiptInput(
                    receipt_data=result.data,
                    friend_ids=friend_ids,
                    receipt_url=receipt_url
                )
                create_result = receipt_service.create_receipt_with_items(create_input, user_id, db)
                
                if create_result.success:
                    if job_id and job_service:
                        job_service.succeed(job_id, create_result.data["receipt_id"], db)
                    return create_result.data
                else:
                    if job_id and job_service:
                        job_service.fail(job_id, create_result.error_code or "RECEIPT_CREATION_FAILED", create_result.message or "Failed", db)
                    return None
        else:
            if job_id and job_service:
                job_service.fail(job_id, result.error_code or "RECEIPT_ANALYSIS_FAILED", result.message or "Failed", db)
            # Update receipt status to failed if it exists
            if receipt_id:
                from app.repositories.receipt import ReceiptRepository
                receipt_repo = ReceiptRepository(db)
                receipt_repo.update(receipt_id, {"status": "failed"})
            return None
            
    except Exception as e:
        # Optionally log the error here
        if job_id and job_service:
            job_service.fail(job_id, "UNEXPECTED_ERROR", str(e), db)
        # Update receipt status to failed if it exists
        if receipt_id:
            from app.repositories.receipt import ReceiptRepository
            receipt_repo = ReceiptRepository(db)
            receipt_repo.update(receipt_id, {"status": "failed"})
        return None

@router.post("", status_code=201)
async def upload_and_analyze_receipt_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    friend_ids: List[int] = [],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    receipt_service: ReceiptService = Depends(get_receipt_service),
    file_service: FileService = Depends(get_file_service),
    job_service: JobService = Depends(get_job_service),
    receipt_friend_service: ReceiptFriendService = Depends(get_receipt_friend_service)
):
    """Upload receipt image and start background analysis. Creates receipt immediately with processing status."""
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

    # Create receipt immediately with processing status
    from app.repositories.receipt import ReceiptRepository
    receipt_repo = ReceiptRepository(db, correlation_id=None)
    receipt = receipt_repo.create_minimal_receipt(
        user_id=current_user.id,
        receipt_url=receipt_url,
        restaurant_name="Processing...",
        status="processing"
    )
    
    # Associate friends with receipt if provided (before processing)
    if friend_ids:
        from app.schemas.receipt import AddFriendsToReceiptInput
        add_friends_input = AddFriendsToReceiptInput(receipt_id=receipt.id, friend_ids=friend_ids)
        receipt_friend_service.add_friends_to_receipt(add_friends_input, current_user.id, db)
        
        # Get friends for response
        from app.schemas.receipt import GetReceiptFriendsInput
        get_friends_input = GetReceiptFriendsInput(receipt_id=receipt.id)
        friends_result = receipt_friend_service.get_receipt_friends(get_friends_input, current_user.id, db)
        friends_data = friends_result.data if friends_result.success else []
    else:
        friends_data = []

    # Create job and start background task for analysis and receipt update
    from app.schemas.job import JobType
    job = job_service.create_job(current_user.id, job_type=JobType.RECEIPT_ANALYSIS, payload={
        "receipt_url": receipt_url,
        "receipt_id": receipt.id,
        "friend_ids": friend_ids,
        "content_type": file.content_type or "image/jpeg"
    }, db=db)
    
    background_tasks.add_task(
        analyze_and_create_receipt,
        db,
        receipt_url,
        image_data,
        friend_ids,
        current_user.id,
        receipt_service,
        file.content_type or "image/jpeg",
        job.id,
        job_service,
        receipt.id  # Pass receipt_id to background task
    )
    
    # Return 201 Created with receipt info
    from app.schemas.receipt import ReceiptRead
    receipt_data = ReceiptRead(
        id=receipt.id,
        user_id=receipt.user_id,
        restaurant_name=receipt.restaurant_name,
        subtotal=receipt.subtotal,
        total_amount=receipt.total_amount,
        tax=receipt.tax,
        service_charge=receipt.service_charge,
        currency=receipt.currency,
        receipt_url=receipt.receipt_url,
        status=receipt.status,
        items=[],
        friends=friends_data,
        created_at=receipt.created_at,
        updated_at=receipt.updated_at
    )
    return receipt_data

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

@router.get("/{receipt_id}/splits", response_model=ReceiptSplitsResponse)
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