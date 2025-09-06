from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.api.dependencies.auth import get_current_user
from app.services.friend_services import create_friend
from app.schemas.friend import FriendCreate, FriendRead
from app.db.models.friend import Friend

router = APIRouter()

@router.post("/", status_code=201, response_model=FriendRead)
def add_friend(
	friend_data: FriendCreate,
	db: Session = Depends(get_db),
	current_user=Depends(get_current_user)
):
	"""
	Add a friend for the current user using FriendCreate schema.
	"""	
	friend = create_friend(db, friend_data, current_user.id)
	return friend

@router.get("/", response_model=list[FriendRead])
def get_friends(
	db: Session = Depends(get_db),
	current_user=Depends(get_current_user)
):
	"""
	Get all friends for the current user.
	"""
	friends = db.query(Friend).filter_by(user_id=current_user.id).filter(
		getattr(Friend, "is_deleted", False) == False
	).all()
	# Ensure photo_url is a string for each friend (avoid None)
	for friend in friends:
		if friend.photo_url is None:
			friend.photo_url = ""
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
	friend = db.query(Friend).filter_by(id=friend_id, user_id=current_user.id).first()
	if not friend:
		raise HTTPException(status_code=404, detail="Friend not found")
	# Add is_deleted attribute if not present
	if not hasattr(friend, "is_deleted"):
		setattr(friend, "is_deleted", True)
	else:
		friend.is_deleted = True
	db.commit()
	return

@router.put("/{friend_id}", response_model=FriendRead)
def edit_friend(
	friend_id: int,
	friend_data: FriendCreate,
	db: Session = Depends(get_db),
	current_user=Depends(get_current_user)
):
	"""
	Edit a friend's information.
	"""
	friend = db.query(Friend).filter_by(id=friend_id, user_id=current_user.id).first()
	if not friend:
		raise HTTPException(status_code=404, detail="Friend not found")
	friend.photo_url = friend_data.photo_url
	db.commit()
	db.refresh(friend)
	return friend