from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
	email: EmailStr
	name: str
	is_active: bool = True
	is_superuser: bool = False

class UserCreate(UserBase):
	password: str

class UserRead(UserBase):
	id: int

	class Config:
		from_attributes = True
