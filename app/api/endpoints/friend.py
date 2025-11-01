from fastapi import Depends, HTTPException, status, UploadFile, File, Form
from app.api.router import create_router
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_friend_service
from app.services.friend_services import FriendService
from app.schemas.friend import FriendRead

router = create_router(name="friend")

@router.post("", status_code=201, response_model=FriendRead)
def add_friend(
	name: str = Form(...),
	photo: UploadFile = File(...),
	db: Session = Depends(get_db),
	current_user=Depends(get_current_user),
	friend_service: FriendService = Depends(get_friend_service)
):
	"""
	Add a friend for the current user with photo upload.
	"""	
	result = friend_service.create_friend(name, photo, current_user.id, db)
	if not result.success:
		if result.error_code == "FRIEND_NOT_FOUND":
			raise HTTPException(status_code=404, detail=result.message)
		elif result.error_code in ["VALIDATION_ERROR", "PHOTO_UPLOAD_FAILED"]:
			raise HTTPException(status_code=400, detail=result.message)
		else:
			raise HTTPException(status_code=500, detail=result.message)
	return result.data

@router.get("", response_model=list[FriendRead])
def get_friends(
	db: Session = Depends(get_db),
	current_user=Depends(get_current_user),
	friend_service: FriendService = Depends(get_friend_service)
):
	"""
	Get all friends for the current user.
	"""
	import logging
	logger = logging.getLogger(__name__)
	
	logger.info(f"get_friends endpoint called for user_id={current_user.id}")
	
	result = friend_service.get_friends(current_user.id, db)
	
	logger.info(f"get_friends service result: success={result.success}, message={result.message}, data_count={len(result.data) if result.data else 0}")
	
	if result.data:
		logger.info(f"get_friends data details: {[{'id': f.id, 'name': f.name, 'user_id': f.user_id} for f in result.data]}")
	
	if not result.success:
		logger.error(f"get_friends failed: {result.message}")
		raise HTTPException(status_code=500, detail=result.message)
	
	logger.info(f"get_friends returning {len(result.data) if result.data else 0} friends")
	return result.data

@router.delete("/{friend_id}", status_code=204)
def delete_friend(
	friend_id: int,
	db: Session = Depends(get_db),
	current_user=Depends(get_current_user),
	friend_service: FriendService = Depends(get_friend_service)
):
	"""
	Soft delete a friend by setting is_deleted to True.
	"""
	result = friend_service.delete_friend(friend_id, current_user.id, db)
	if not result.success:
		if result.error_code == "FRIEND_NOT_FOUND":
			raise HTTPException(status_code=404, detail=result.message)
		else:
			raise HTTPException(status_code=500, detail=result.message)
	return

@router.put("/{friend_id}", response_model=FriendRead)
def edit_friend(
	friend_id: int,
	name: str = Form(...),
	photo: UploadFile = File(...),
	db: Session = Depends(get_db),
	current_user=Depends(get_current_user),
	friend_service: FriendService = Depends(get_friend_service)
):
	"""
	Edit a friend's information with photo upload.
	"""
	result = friend_service.update_friend(friend_id, name, photo, current_user.id, db)
	if not result.success:
		if result.error_code == "FRIEND_NOT_FOUND":
			raise HTTPException(status_code=404, detail=result.message)
		elif result.error_code in ["VALIDATION_ERROR", "PHOTO_UPLOAD_FAILED"]:
			raise HTTPException(status_code=400, detail=result.message)
		else:
			raise HTTPException(status_code=500, detail=result.message)
	return result.data