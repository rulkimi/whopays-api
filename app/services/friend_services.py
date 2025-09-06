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