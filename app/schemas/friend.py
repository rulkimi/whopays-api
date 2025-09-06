from pydantic import BaseModel

class FriendBase(BaseModel):
	photo_url: str

class FriendCreate(FriendBase):
	pass

class FriendRead(FriendBase):
	id: int
	user_id: int

	class Config:
		from_attributes = True