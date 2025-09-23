from pydantic import BaseModel, Field, validator
from typing import Optional
from fastapi import UploadFile
import re


class FriendRead(BaseModel):
	id: int
	user_id: int
	name: str = Field(..., max_length=50)
	photo_url: str

	class Config:
		from_attributes = True


class CreateFriendInput(BaseModel):
	"""Input validation for creating a friend."""
	name: str = Field(..., min_length=1, max_length=50, description="Friend's name")
	
	@validator('name')
	def validate_name(cls, v):
		"""Validate and sanitize friend name."""
		if not v or not v.strip():
			raise ValueError("Name cannot be empty or only whitespace")
		
		# Sanitize name - remove excessive whitespace and special characters
		sanitized = re.sub(r'\s+', ' ', v.strip())
		
		if len(sanitized) < 1:
			raise ValueError("Name must contain at least one character")
		
		if len(sanitized) > 50:
			raise ValueError("Name cannot exceed 50 characters")
		
		return sanitized


class UpdateFriendInput(BaseModel):
	"""Input validation for updating a friend."""
	name: str = Field(..., min_length=1, max_length=50, description="Friend's name")
	
	@validator('name')
	def validate_name(cls, v):
		"""Validate and sanitize friend name."""
		if not v or not v.strip():
			raise ValueError("Name cannot be empty or only whitespace")
		
		# Sanitize name - remove excessive whitespace and special characters
		sanitized = re.sub(r'\s+', ' ', v.strip())
		
		if len(sanitized) < 1:
			raise ValueError("Name must contain at least one character")
		
		if len(sanitized) > 50:
			raise ValueError("Name cannot exceed 50 characters")
		
		return sanitized


class FriendResult(BaseModel):
	"""Result object for friend operations."""
	success: bool
	data: Optional[FriendRead] = None
	error_code: Optional[str] = None
	message: Optional[str] = None


class CreateFriendResult(BaseModel):
	"""Result object for friend creation."""
	success: bool
	data: Optional[FriendRead] = None
	error_code: Optional[str] = None
	message: Optional[str] = None


class UpdateFriendResult(BaseModel):
	"""Result object for friend updates."""
	success: bool
	data: Optional[FriendRead] = None
	error_code: Optional[str] = None
	message: Optional[str] = None


class DeleteFriendResult(BaseModel):
	"""Result object for friend deletion."""
	success: bool
	data: Optional[dict] = None
	error_code: Optional[str] = None
	message: Optional[str] = None


class GetFriendsResult(BaseModel):
	"""Result object for getting friends list."""
	success: bool
	data: Optional[list[FriendRead]] = None
	error_code: Optional[str] = None
	message: Optional[str] = None