from sqlalchemy.orm import Session
from app.gemini.prompts import create_analysis_prompt
from app.gemini.services import get_ai_response
from app.schemas.receipt import ReceiptBase, ReceiptRead
from app.db.models.receipt import Receipt
from app.db.models.item import Item
from app.db.models.variation import Variation
from app.services.receipt_friend_services import add_friends_to_receipt
from app.services.item_friend_services import get_item_friends
from typing import Dict, List, Optional
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from app.db.models.item_friend import ItemFriend
from app.db.models.friend import Friend

def _round2(x: Decimal) -> Decimal:
	return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def calculate_receipt_splits(db: Session, receipt_id: int, user_id: int) -> Optional[dict]:
	receipt = db.query(Receipt).filter(
		Receipt.id == receipt_id,
		Receipt.user_id == user_id,
		Receipt.is_deleted == False
	).first()
	if not receipt:
		return None

	items: List[Item] = db.query(Item).filter(
		Item.receipt_id == receipt_id,
		Item.is_deleted == False
	).all()

	# Preload item → friends map
	item_friend_map: Dict[int, List[Friend]] = {}
	if items:
		item_ids = [it.id for it in items]
		item_friend_links: List[ItemFriend] = db.query(ItemFriend).filter(
			ItemFriend.item_id.in_(item_ids),
			ItemFriend.is_deleted == False
		).all()
		for link in item_friend_links:
			item_friend_map.setdefault(link.item_id, []).append(link.friend)

	friend_totals: Dict[int, Dict[str, Decimal]] = {}
	# Will collect detailed item breakdowns for the whole receipt
	items_out: List[dict] = []
	subtotal_all = Decimal("0.00")

	for item in items:
		# Load variations from DB to be consistent
		vars: List[Variation] = db.query(Variation).filter(
			Variation.item_id == item.id,
			Variation.is_deleted == False
		).all()
		unit_base = Decimal(str(item.unit_price))
		unit_addons = sum(Decimal(str(v.price)) for v in vars) if vars else Decimal("0.00")
		unit_total = unit_base + unit_addons
		line_total = unit_total * Decimal(str(item.quantity))

		friends = item_friend_map.get(item.id, [])
		if not friends:
			# If item has no assigned friends, skip splitting it.
			continue

		split_count = len(friends)
		share = (line_total / split_count)

		# Record item-level breakdown for top-level items list
		item_entry = {
			"item_id": item.id,
			"item_name": item.item_name,
			"quantity": item.quantity,
			"unit_price": float(_round2(unit_base)),
			"variations": [
				{
					"variation_name": v.variation_name,
					"price": float(_round2(Decimal(str(v.price))))
				} for v in vars
			],
			"unit_total": float(_round2(unit_total)),
			"line_total": float(_round2(line_total)),
			"friends": [
				{
					"id": f.id,
					"name": f.name,
					"photo_url": getattr(f, "photo_url", None),
					"share": float(_round2(share))
				} for f in friends
			]
		}
		items_out.append(item_entry)

		for f in friends:
			fd = friend_totals.setdefault(
				f.id,
				{
					"name": f.name,
					"photo_url": getattr(f, "photo_url", None),
					"subtotal": Decimal("0.00"),
					"items": []
				}
			)
			fd["subtotal"] += share
			fd["items"].append({
				"item_id": item.id,
				"item_name": item.item_name,
				"quantity": item.quantity,
				"unit_total": float(_round2(unit_total)),
				"line_total": float(_round2(line_total)),
				"share": float(_round2(share))
			})

		subtotal_all += line_total

	if subtotal_all == 0:
		return {
			"receipt_id": receipt.id,
			"currency": receipt.currency,
			"totals": [],
			"summary": {"subtotal": 0.0, "tax": 0.0, "service_charge": 0.0, "total": 0.0}
		}

	# Allocate tax and service charge proportional to subtotals
	tax_total = Decimal(str(receipt.tax))
	svc_total = Decimal(str(receipt.service_charge))
	receipt_total_from_db = Decimal(str(receipt.total_amount))

	# First pass rounding
	per_friend = []
	acc_tax = Decimal("0.00")
	acc_svc = Decimal("0.00")
	for fid, data in friend_totals.items():
		share_ratio = (data["subtotal"] / subtotal_all)
		ftax = _round2(tax_total * share_ratio)
		fsvc = _round2(svc_total * share_ratio)
		acc_tax += ftax
		acc_svc += fsvc
		per_friend.append({
			"id": fid,
			"name": data["name"],
			"photo_url": data.get("photo_url"),
			"subtotal": data["subtotal"],
			"tax": ftax,
			"service_charge": fsvc
		})

	# Distribute rounding residuals to the friend(s) with largest subtotal
	tax_residual = tax_total - acc_tax
	svc_residual = svc_total - acc_svc
	per_friend.sort(key=lambda x: x["subtotal"], reverse=True)
	if per_friend:
		if tax_residual != 0:
			per_friend[0]["tax"] += tax_residual
		if svc_residual != 0:
			per_friend[0]["service_charge"] += svc_residual

	# Prepare list of all friend raw totals
	friend_ids_ordered = [f["id"] for f in per_friend]
	raw_totals = [f["subtotal"] + f["tax"] + f["service_charge"] for f in per_friend]
	raw_total_sum = sum(raw_totals)
	db_total = receipt_total_from_db

	final_totals = []
	if per_friend:
		# Distribute receipt total from DB proportionally according to each friend's share of the calculated overall sum
		if raw_total_sum > 0:
			adjusted_totals = []
			accum_adj = Decimal("0.00")
			# Calculate each friend's share proportional to the sum, discard rounding
			for idx, raw_total in enumerate(raw_totals):
				if idx < len(per_friend)-1:
					adj_total = _round2(db_total * (raw_total / raw_total_sum))
					adjusted_totals.append(adj_total)
					accum_adj += adj_total
				else:
					adj_total = db_total - accum_adj
					adj_total = _round2(adj_total)
					adjusted_totals.append(adj_total)
			# Now populate final friend dicts, still preserve item/tax/svc breakdowns
			for f, adjusted in zip(per_friend, adjusted_totals):
				final_totals.append({
					"id": f["id"],
					"name": f["name"],
					"photo_url": f.get("photo_url"),
					"subtotal": float(_round2(f["subtotal"])),
					"tax": float(_round2(f["tax"])),
					"service_charge": float(_round2(f["service_charge"])),
					"total": float(_round2(adjusted)),
					"items": friend_totals[f["id"]].get("items", [])
				})
		else:
			for f in per_friend:
				final_totals.append({
					"id": f["id"],
					"name": f["name"],
					"photo_url": f.get("photo_url"),
					"subtotal": float(_round2(f["subtotal"])),
					"tax": float(_round2(f["tax"])),
					"service_charge": float(_round2(f["service_charge"])),
					"total": 0.0,
					"items": friend_totals[f["id"]].get("items", [])
				})

	return {
		"receipt_id": receipt.id,
		"currency": receipt.currency,
		"totals": final_totals,
		"items": items_out,
		"summary": {
			"subtotal": float(_round2(subtotal_all)),
			"tax": float(_round2(tax_total)),
			"service_charge": float(_round2(svc_total)),
			"total": float(_round2(receipt_total_from_db))
		},
		"note": "Items without assigned friends are excluded from splits. Assign item friends to include them."
	}

def analyze_receipt(image_data: bytes) -> ReceiptBase:
	"""Analyze receipt image and return AI response as ReceiptBase model"""
	prompt = create_analysis_prompt()
	ai_response_dict = get_ai_response(contents=[prompt, image_data], response_schema=ReceiptBase)
	
	# Convert the dictionary response to ReceiptBase model
	return ReceiptBase(**ai_response_dict)

def create_receipt_with_items(db: Session, receipt_data: ReceiptBase, user_id: int, receipt_url: str = None, friend_ids: List[int] = None) -> dict:
	"""Create a receipt with all its items and variations in the database, and return the receipt info including friend objects"""
	
	db_receipt = Receipt(
		restaurant_name=receipt_data.restaurant_name,
		subtotal=receipt_data.subtotal,
		total_amount=receipt_data.total_amount,
		tax=receipt_data.tax,
		service_charge=receipt_data.service_charge,
		currency=receipt_data.currency,
		receipt_url=receipt_url,
		user_id=user_id
	)
	
	db.add(db_receipt)
	db.flush()  # Flush to get the receipt ID
	
	item_objs = []
	for item_data in receipt_data.items:
		db_item = Item(
			item_name=item_data.item_name,
			quantity=item_data.quantity,
			unit_price=item_data.unit_price,
			receipt_id=db_receipt.id
		)
		db.add(db_item)
		db.flush()  # Flush to get the item ID
		item_objs.append((db_item, item_data))
		
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
	
	# Associate friends with the receipt if provided
	if friend_ids:
		add_friends_to_receipt(db, db_receipt.id, friend_ids, user_id)
	else:
		friend_ids = []

	# Get the full friend objects associated with this receipt
	friends = []
	if friend_ids:
		from app.db.models.friend import Friend
		friends = db.query(Friend).filter(Friend.id.in_(friend_ids)).all()
		# Convert SQLAlchemy objects to dicts
		friends = [
			{
				"id": friend.id,
				"name": friend.name,
				"photo_url": friend.photo_url,
				"user_id": friend.user_id
			}
			for friend in friends
		]

	# Build items with item_id, created_at, updated_at
	items = []
	for db_item, item_data in item_objs:
		item_dict = {
			"item_id": db_item.id,
			"item_name": db_item.item_name,
			"quantity": db_item.quantity,
			"unit_price": db_item.unit_price,
			"variation": [
				{
					"variation_name": v.variation_name,
					"price": v.price
				}
				for v in db_item.variation if not getattr(v, "is_deleted", False)
			] if hasattr(db_item, "variation") and db_item.variation else [],
			"friends": [],  # No friends at creation
			"created_at": db_item.created_at,
			"updated_at": db_item.updated_at
		}
		items.append(item_dict)

	return {
		"id": db_receipt.id,
		"user_id": db_receipt.user_id,
		"receipt_url": db_receipt.receipt_url,
		"restaurant_name": db_receipt.restaurant_name,
		"subtotal": db_receipt.subtotal,
		"total_amount": db_receipt.total_amount,
		"tax": db_receipt.tax,
		"service_charge": db_receipt.service_charge,
		"currency": db_receipt.currency,
		"created_at": db_receipt.created_at,
		"updated_at": db_receipt.updated_at,
		"items": receipt_data.items,
		"friends": friends
	}

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
		
		# Get friends for this item
		item_friends = get_item_friends(db, item.id, user_id)
		
		item_data = {
			"item_id": item.id,
			"item_name": item.item_name,
			"quantity": item.quantity,
			"unit_price": item.unit_price,
			"variation": [
				{
					"variation_name": var.variation_name,
					"price": var.price
				} for var in variations
			] if variations else [],
			"friends": item_friends,
			"created_at": item.created_at,
			"updated_at": item.updated_at
		}
		items_data.append(item_data)

	# Get friends associated with this receipt
	from app.db.models.receipt_friend import ReceiptFriend
	from app.db.models.friend import Friend
	
	receipt_friends = db.query(ReceiptFriend).filter(
		ReceiptFriend.receipt_id == receipt_id
	).all()
	
	friend_ids = [rf.friend_id for rf in receipt_friends]
	friends = []
	if friend_ids:
		friends = db.query(Friend).filter(Friend.id.in_(friend_ids)).all()
		friends = [
			{
				"id": friend.id,
				"name": friend.name,
				"photo_url": friend.photo_url,
				"user_id": friend.user_id
			}
			for friend in friends
		]
    
	return ReceiptRead(
		id=receipt.id,
		user_id=receipt.user_id,
		receipt_url=receipt.receipt_url,
		restaurant_name=receipt.restaurant_name,
    subtotal=receipt.subtotal,
		total_amount=receipt.total_amount,
		tax=receipt.tax,
		service_charge=receipt.service_charge,
		currency=receipt.currency,
		created_at=receipt.created_at,
		updated_at=receipt.updated_at,
		items=items_data,
		friends=friends
	)


def get_user_receipts(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[ReceiptRead]:
	"""Get all receipts for a user with pagination, sorted by latest first"""
	receipts = db.query(Receipt).filter(
		Receipt.user_id == user_id,
		Receipt.is_deleted == False
	).order_by(Receipt.created_at.desc()).offset(skip).limit(limit).all()
	
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