from sqlalchemy.orm import Session
from app.gemini.prompts import create_analysis_prompt
from app.gemini.services import get_ai_response
from app.schemas.receipt import ReceiptBase, ReceiptRead
from app.db.models.receipt import Receipt
from app.db.models.item import Item
from app.db.models.variation import Variation
from typing import List, Optional

def analyze_receipt(image_data: bytes) -> ReceiptBase:
	"""Analyze receipt image and return AI response as ReceiptBase model"""
	prompt = create_analysis_prompt()
	ai_response_dict = get_ai_response(contents=[prompt, image_data], response_schema=ReceiptBase)
	
	# Convert the dictionary response to ReceiptBase model
	return ReceiptBase(**ai_response_dict)

def create_receipt_with_items(db: Session, receipt_data: ReceiptBase, user_id: int, receipt_url: str = "") -> ReceiptRead:
	"""Create a receipt with all its items and variations in the database"""
	
	db_receipt = Receipt(
		restaurant_name=receipt_data.restaurant_name,
		total_amount=receipt_data.total_amount,
		tax=receipt_data.tax,
		service_charge=receipt_data.service_charge,
		currency=receipt_data.currency,
		user_id=user_id
	)
	
	db.add(db_receipt)
	db.flush()  # Flush to get the receipt ID
	
	for item_data in receipt_data.items:
		db_item = Item(
			item_name=item_data.item_name,
			quantity=item_data.quantity,
			unit_price=item_data.unit_price,
			receipt_id=db_receipt.id
		)
		db.add(db_item)
		db.flush()  # Flush to get the item ID
		
		if item_data.variation:
			for variation_data in item_data.variation:
				db_variation = Variation(
					variation_name=variation_data.variation_name,
					price=variation_data.price,
					item_id=db_item.id
				)
				db.add(db_variation)
	
	db.commit()
	db.refresh(db_receipt)
	
	return ReceiptRead(
		id=db_receipt.id,
		user_id=db_receipt.user_id,
		receipt_url=receipt_url,
		restaurant_name=db_receipt.restaurant_name,
		total_amount=db_receipt.total_amount,
		tax=db_receipt.tax,
		service_charge=db_receipt.service_charge,
		currency=db_receipt.currency,
		items=receipt_data.items  
	)

def get_receipt_by_id(db: Session, receipt_id: int, user_id: int) -> Optional[ReceiptRead]:
	"""Get a receipt by ID for a specific user"""
	receipt = db.query(Receipt).filter(
		Receipt.id == receipt_id,
		Receipt.user_id == user_id,
		Receipt.is_deleted == False
	).first()
	
	if not receipt:
		return None
	
	items = db.query(Item).filter(
		Item.receipt_id == receipt_id,
		Item.is_deleted == False
	).all()
	
	items_data = []
	for item in items:
		variations = db.query(Variation).filter(
			Variation.item_id == item.id,
			Variation.is_deleted == False
		).all()
		
		item_data = {
			"item_name": item.item_name,
			"quantity": item.quantity,
			"unit_price": item.unit_price,
			"variation": [
				{
					"variation_name": var.variation_name,
					"price": var.price
				} for var in variations
			] if variations else None
		}
		items_data.append(item_data)
	
	return ReceiptRead(
		id=receipt.id,
		user_id=receipt.user_id,
		receipt_url="",  # TODO: store receipt_url
		restaurant_name=receipt.restaurant_name,
		total_amount=receipt.total_amount,
		tax=receipt.tax,
		service_charge=receipt.service_charge,
		currency=receipt.currency,
		items=items_data
	)

def get_user_receipts(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[ReceiptRead]:
	"""Get all receipts for a user with pagination"""
	receipts = db.query(Receipt).filter(
		Receipt.user_id == user_id,
		Receipt.is_deleted == False
	).offset(skip).limit(limit).all()
	
	receipt_reads = []
	for receipt in receipts:
		receipt_read = get_receipt_by_id(db, receipt.id, user_id)
		if receipt_read:
			receipt_reads.append(receipt_read)
	
	return receipt_reads

def delete_receipt(db: Session, receipt_id: int, user_id: int) -> bool:
	"""Soft delete a receipt and all its related items and variations"""
	receipt = db.query(Receipt).filter(
		Receipt.id == receipt_id,
		Receipt.user_id == user_id,
		Receipt.is_deleted == False
	).first()
	
	if not receipt:
		return False
	
	# Soft delete the receipt
	receipt.is_deleted = True
	receipt.deleted_at = db.func.now()
	
	# Soft delete all items
	items = db.query(Item).filter(
		Item.receipt_id == receipt_id,
		Item.is_deleted == False
	).all()
	
	for item in items:
		item.is_deleted = True
		item.deleted_at = db.func.now()
		
		# Soft delete all variations for this item
		variations = db.query(Variation).filter(
			Variation.item_id == item.id,
			Variation.is_deleted == False
		).all()
		
		for variation in variations:
			variation.is_deleted = True
			variation.deleted_at = db.func.now()
	
	db.commit()
	return True