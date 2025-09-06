from pydantic import BaseModel
from typing import List

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
	pass

class ReceiptRead(ReceiptBase):
	id: int
	user_id: int
	receipt_url: str
	
	class Config:
		from_attributes = True