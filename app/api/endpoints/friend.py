from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.api.dependencies.auth import get_current_user
from app.services import friend_services
from app.schemas.friend import FriendRead

router = APIRouter()

@router.post("", status_code=201, response_model=FriendRead)
def add_friend(
	name: str = Form(...),
	photo: UploadFile = File(...),
	db: Session = Depends(get_db),
	current_user=Depends(get_current_user)
):
	"""
	Add a friend for the current user with photo upload.
	"""	
	friend = friend_services.create_friend(db, name, photo, current_user.id)
	return friend

@router.get("", response_model=list[FriendRead])
def get_friends(
	db: Session = Depends(get_db),
	current_user=Depends(get_current_user)
):
	"""
	Get all friends for the current user.
	"""
	friends = friend_services.get_friends(db, current_user.id)
	return friends

@router.delete("/{friend_id}", status_code=204)
def delete_friend(
	friend_id: int,
	db: Session = Depends(get_db),
	current_user=Depends(get_current_user)
):
	"""
	Soft delete a friend by setting is_deleted to True.
	"""
	friend = friend_services.delete_friend(db, friend_id, current_user.id)
	if not friend:
		raise HTTPException(status_code=404, detail="Friend not found")
	return

@router.put("/{friend_id}", response_model=FriendRead)
def edit_friend(
	friend_id: int,
	name: str = Form(...),
	photo: UploadFile = File(...),
	db: Session = Depends(get_db),
	current_user=Depends(get_current_user)
):
	"""
	Edit a friend's information with photo upload.
	"""
	friend = friend_services.edit_friend(db, friend_id, name, photo, current_user.id)
	if not friend:
		raise HTTPException(status_code=404, detail="Friend not found")
	return friend