from pydantic import BaseModel, Field

class FriendRead(BaseModel):
	id: int
	user_id: int
	name: str = Field(..., max_length=50)
	photo_url: str

	class Config:
		from_attributes = True