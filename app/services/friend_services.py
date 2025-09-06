from sqlalchemy.orm import Session
from app.db.models.friend import Friend
from app.schemas.friend import FriendCreate

def create_friend(db: Session, friend_data: FriendCreate, user_id: int):
  friend = Friend(
    user_id=user_id,
    photo_url=friend_data.photo_url
  )
  db.add(friend)
  db.commit()
  db.refresh(friend)
  return friend

def get_friends(db: Session, user_id: int):
	friends = db.query(Friend).filter_by(user_id=user_id).filter(
		getattr(Friend, "is_deleted", False) == False
	).all()
	for friend in friends:
		if friend.photo_url is None:
			friend.photo_url = ""
	return friends

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

def edit_friend(db: Session, friend_id: int, friend_data: FriendCreate, user_id: int):
	friend = db.query(Friend).filter_by(id=friend_id, user_id=user_id).first()
	if not friend:
		return None
	friend.photo_url = friend_data.photo_url
	db.commit()
	db.refresh(friend)
	return friend
