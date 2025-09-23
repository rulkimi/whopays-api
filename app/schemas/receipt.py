from pydantic import BaseModel, Field, validator
from .mixin import TimestampModel
from typing import List, Optional, Dict, Any
from decimal import Decimal

from app.db.models.friend import Friend
from app.schemas.friend import FriendRead

class Variation(BaseModel):
	variation_name: str
	price: float

class Item(BaseModel):
	item_id: int
	item_name: str
	quantity: int
	unit_price: float
	variation: Optional[List[Variation]] = None
	friends: List[FriendRead] = []

class ReceiptBase(TimestampModel):
	restaurant_name: str
	total_amount: float
	tax: float
	service_charge: float
	currency: str
	items: List[Item]

class ReceiptCreate(ReceiptBase):
	friend_ids: List[int]

class ReceiptRead(ReceiptBase):
	id: int
	user_id: int
	receipt_url: Optional[str]
	friends: List[FriendRead]
	
	class Config:
		from_attributes = True


# Input validation schemas
class AnalyzeReceiptInput(BaseModel):
	"""Input for receipt analysis operation."""
	image_data: bytes = Field(..., description="Receipt image data for AI analysis")
	content_type: Optional[str] = Field(default="image/jpeg", description="MIME type of the image")
	
	@validator('image_data')
	def validate_image_data(cls, v):
		"""Validate image data is not empty."""
		if not v:
			raise ValueError("Image data cannot be empty")
		if len(v) > 10 * 1024 * 1024:  # 10MB limit
			raise ValueError("Image data too large (max 10MB)")
		return v
	
	@validator('content_type')
	def validate_content_type(cls, v):
		"""Validate content type is an image type."""
		if v and not v.startswith("image/"):
			raise ValueError("Content type must be an image type")
		return v or "image/jpeg"


class CreateReceiptInput(BaseModel):
	"""Input for receipt creation operation."""
	receipt_data: ReceiptBase = Field(..., description="Receipt data from analysis")
	friend_ids: Optional[List[int]] = Field(default=None, description="Friend IDs to associate with receipt")
	receipt_url: Optional[str] = Field(default=None, description="Receipt image URL")
	
	@validator('friend_ids')
	def validate_friend_ids(cls, v):
		"""Validate friend IDs are unique and positive."""
		if v is not None:
			if not all(isinstance(id, int) and id > 0 for id in v):
				raise ValueError("All friend IDs must be positive integers")
			if len(v) != len(set(v)):
				raise ValueError("Friend IDs must be unique")
		return v


class GetReceiptInput(BaseModel):
	"""Input for get receipt operation."""
	receipt_id: int = Field(..., description="Receipt ID to retrieve")
	
	@validator('receipt_id')
	def validate_receipt_id(cls, v):
		"""Validate receipt ID is positive."""
		if v <= 0:
			raise ValueError("Receipt ID must be positive")
		return v


class GetReceiptsInput(BaseModel):
	"""Input for get receipts list operation."""
	skip: int = Field(default=0, ge=0, description="Number of records to skip")
	limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of records to return")


class DeleteReceiptInput(BaseModel):
	"""Input for delete receipt operation."""
	receipt_id: int = Field(..., description="Receipt ID to delete")
	
	@validator('receipt_id')
	def validate_receipt_id(cls, v):
		"""Validate receipt ID is positive."""
		if v <= 0:
			raise ValueError("Receipt ID must be positive")
		return v


class CalculateSplitsInput(BaseModel):
	"""Input for calculate receipt splits operation."""
	receipt_id: int = Field(..., description="Receipt ID to calculate splits for")
	
	@validator('receipt_id')
	def validate_receipt_id(cls, v):
		"""Validate receipt ID is positive."""
		if v <= 0:
			raise ValueError("Receipt ID must be positive")
		return v


# Result schemas
class AnalyzeReceiptResult(BaseModel):
	"""Result for receipt analysis operation."""
	success: bool
	data: Optional[ReceiptBase] = None
	error_code: Optional[str] = None
	message: Optional[str] = None


class CreateReceiptResult(BaseModel):
	"""Result for receipt creation operation."""
	success: bool
	data: Optional[Dict[str, Any]] = None  # Full receipt dict with items and friends
	error_code: Optional[str] = None
	message: Optional[str] = None


class GetReceiptResult(BaseModel):
	"""Result for get receipt operation."""
	success: bool
	data: Optional[ReceiptRead] = None
	error_code: Optional[str] = None
	message: Optional[str] = None


class GetReceiptsResult(BaseModel):
	"""Result for get receipts list operation."""
	success: bool
	data: Optional[List[ReceiptRead]] = None
	error_code: Optional[str] = None
	message: Optional[str] = None


class DeleteReceiptResult(BaseModel):
	"""Result for delete receipt operation."""
	success: bool
	data: Optional[bool] = None  # True if deleted successfully
	error_code: Optional[str] = None
	message: Optional[str] = None


class CalculateSplitsResult(BaseModel):
	"""Result for calculate receipt splits operation."""
	success: bool
	data: Optional[Dict[str, Any]] = None  # Split calculation results
	error_code: Optional[str] = None
	message: Optional[str] = None


# Receipt-Friend association schemas
class AddFriendsToReceiptInput(BaseModel):
	"""Input for adding friends to receipt operation."""
	receipt_id: int = Field(..., description="Receipt ID")
	friend_ids: List[int] = Field(..., description="Friend IDs to add to receipt")
	
	@validator('receipt_id')
	def validate_receipt_id(cls, v):
		"""Validate receipt ID is positive."""
		if v <= 0:
			raise ValueError("Receipt ID must be positive")
		return v
	
	@validator('friend_ids')
	def validate_friend_ids(cls, v):
		"""Validate friend IDs are unique and positive."""
		if not v:
			raise ValueError("At least one friend ID is required")
		if not all(isinstance(id, int) and id > 0 for id in v):
			raise ValueError("All friend IDs must be positive integers")
		if len(v) != len(set(v)):
			raise ValueError("Friend IDs must be unique")
		return v


class RemoveFriendsFromReceiptInput(BaseModel):
	"""Input for removing friends from receipt operation."""
	receipt_id: int = Field(..., description="Receipt ID")
	friend_ids: List[int] = Field(..., description="Friend IDs to remove from receipt")
	
	@validator('receipt_id')
	def validate_receipt_id(cls, v):
		"""Validate receipt ID is positive."""
		if v <= 0:
			raise ValueError("Receipt ID must be positive")
		return v
	
	@validator('friend_ids')
	def validate_friend_ids(cls, v):
		"""Validate friend IDs are unique and positive."""
		if not v:
			raise ValueError("At least one friend ID is required")
		if not all(isinstance(id, int) and id > 0 for id in v):
			raise ValueError("All friend IDs must be positive integers")
		if len(v) != len(set(v)):
			raise ValueError("Friend IDs must be unique")
		return v


class GetReceiptFriendsInput(BaseModel):
	"""Input for getting receipt friends operation."""
	receipt_id: int = Field(..., description="Receipt ID")
	
	@validator('receipt_id')
	def validate_receipt_id(cls, v):
		"""Validate receipt ID is positive."""
		if v <= 0:
			raise ValueError("Receipt ID must be positive")
		return v


class UpdateReceiptFriendsInput(BaseModel):
	"""Input for updating receipt friends operation."""
	receipt_id: int = Field(..., description="Receipt ID")
	friend_ids: List[int] = Field(..., description="Friend IDs to associate with receipt")
	
	@validator('receipt_id')
	def validate_receipt_id(cls, v):
		"""Validate receipt ID is positive."""
		if v <= 0:
			raise ValueError("Receipt ID must be positive")
		return v
	
	@validator('friend_ids')
	def validate_friend_ids(cls, v):
		"""Validate friend IDs are unique and positive."""
		if not all(isinstance(id, int) and id > 0 for id in v):
			raise ValueError("All friend IDs must be positive integers")
		if len(v) != len(set(v)):
			raise ValueError("Friend IDs must be unique")
		return v


class GetFriendReceiptsInput(BaseModel):
	"""Input for getting friend receipts operation."""
	friend_id: int = Field(..., description="Friend ID")
	
	@validator('friend_id')
	def validate_friend_id(cls, v):
		"""Validate friend ID is positive."""
		if v <= 0:
			raise ValueError("Friend ID must be positive")
		return v


class RemoveFriendFromAllReceiptsInput(BaseModel):
	"""Input for removing friend from all receipts operation."""
	friend_id: int = Field(..., description="Friend ID")
	
	@validator('friend_id')
	def validate_friend_id(cls, v):
		"""Validate friend ID is positive."""
		if v <= 0:
			raise ValueError("Friend ID must be positive")
		return v


# Receipt-Friend result schemas
class AddFriendsToReceiptResult(BaseModel):
	"""Result for adding friends to receipt operation."""
	success: bool
	data: Optional[bool] = None  # True if successful
	error_code: Optional[str] = None
	message: Optional[str] = None


class RemoveFriendsFromReceiptResult(BaseModel):
	"""Result for removing friends from receipt operation."""
	success: bool
	data: Optional[bool] = None  # True if successful
	error_code: Optional[str] = None
	message: Optional[str] = None


class GetReceiptFriendsResult(BaseModel):
	"""Result for getting receipt friends operation."""
	success: bool
	data: Optional[List[FriendRead]] = None
	error_code: Optional[str] = None
	message: Optional[str] = None


class UpdateReceiptFriendsResult(BaseModel):
	"""Result for updating receipt friends operation."""
	success: bool
	data: Optional[bool] = None  # True if successful
	error_code: Optional[str] = None
	message: Optional[str] = None


class GetFriendReceiptsResult(BaseModel):
	"""Result for getting friend receipts operation."""
	success: bool
	data: Optional[List[ReceiptRead]] = None
	error_code: Optional[str] = None
	message: Optional[str] = None


class RemoveFriendFromAllReceiptsResult(BaseModel):
	"""Result for removing friend from all receipts operation."""
	success: bool
	data: Optional[bool] = None  # True if successful
	error_code: Optional[str] = None
	message: Optional[str] = None