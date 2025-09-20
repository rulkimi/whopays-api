from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.db.models.friend import Friend
from app.services.file_services import upload_file

def create_friend(db: Session, name: str, photo: UploadFile, user_id: int):
	# Upload photo to MinIO and get the URL
	photo_url = upload_file(photo, "friends")
	
	friend = Friend(
		user_id=user_id,
		name=name,
		photo_url=photo_url
	)
	db.add(friend)
	db.commit()
	db.refresh(friend)
	return friend

def get_friends(db: Session, user_id: int):
	db.query(Friend).filter_by(user_id=user_id).filter(
		Friend.name.is_(None)
	).update({"name": "Friend"})
	db.commit()
	
	friends = db.query(Friend).filter_by(user_id=user_id).filter(
		Friend.is_deleted == False
	).all()
	
	friend_list = []
	for friend in friends:
		friend_list.append(
			{
				"id": friend.id,
				"name": friend.name,
				"photo_url": friend.photo_url,
				"user_id": friend.user_id
			}
		)
	
	return friend_list

def delete_friend(db: Session, friend_id: int, user_id: int):
	friend = db.query(Friend).filter_by(id=friend_id, user_id=user_id).first()
	if not friend:
		return None
	if not hasattr(friend, "is_deleted"):
		setattr(friend, "is_deleted", True)
	else:
		friend.is_deleted = True
	db.commit()
	return friend

def edit_friend(db: Session, friend_id: int, name: str, photo: UploadFile, user_id: int):
	friend = db.query(Friend).filter_by(id=friend_id, user_id=user_id).first()
	if not friend:
		return None
	
	# Upload new photo to MinIO and get the URL
	photo_url = upload_file(photo, "friends")
	
	friend.name = name
	friend.photo_url = photo_url
	db.commit()
	db.refresh(friend)
	return friend
