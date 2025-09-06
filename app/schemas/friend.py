from pydantic import BaseModel, Field

class FriendBase(BaseModel):
	name: str = Field(..., max_length=50)
	photo_url: str

class FriendCreate(FriendBase):
	pass

class FriendRead(FriendBase):
	id: int
	user_id: int

	class Config:
		from_attributes = True