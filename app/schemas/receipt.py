from pydantic import BaseModel
from typing import List

from app.db.models.friend import Friend
from app.schemas.friend import FriendRead

class Variation(BaseModel):
	variation_name: str
	price: float

class Item(BaseModel):
	item_name: str
	quantity: int
	unit_price: float
	variation: List[Variation] = None

class ReceiptBase(BaseModel):
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
	receipt_url: str
	friends: List[FriendRead]
	
	class Config:
		from_attributes = True