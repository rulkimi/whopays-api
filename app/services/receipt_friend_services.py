from sqlalchemy.orm import Session
from app.db.models.receipt_friend import ReceiptFriend
from app.db.models.receipt import Receipt
from app.db.models.friend import Friend
from typing import List, Optional

def add_friends_to_receipt(db: Session, receipt_id: int, friend_ids: List[int], user_id: int) -> bool:
	"""Add friends to a receipt. Returns True if successful, False otherwise."""
	# Verify the receipt belongs to the user
	receipt = db.query(Receipt).filter(
		Receipt.id == receipt_id,
		Receipt.user_id == user_id,
		Receipt.is_deleted == False
	).first()
	
	if not receipt:
		return False
	
	# Verify all friends belong to the user
	friends = db.query(Friend).filter(
		Friend.id.in_(friend_ids),
		Friend.user_id == user_id,
		Friend.is_deleted == False
	).all()
	
	if len(friends) != len(friend_ids):
		return False
	
	# Add friend associations
	for friend_id in friend_ids:
		# Check if association already exists
		existing = db.query(ReceiptFriend).filter(
			ReceiptFriend.receipt_id == receipt_id,
			ReceiptFriend.friend_id == friend_id
		).first()
		
		if not existing:
			receipt_friend = ReceiptFriend(
				receipt_id=receipt_id,
				friend_id=friend_id
			)
			db.add(receipt_friend)
	
	db.commit()
	return True

def remove_friends_from_receipt(db: Session, receipt_id: int, friend_ids: List[int], user_id: int) -> bool:
	"""Remove friends from a receipt. Returns True if successful, False otherwise."""
	# Verify the receipt belongs to the user
	receipt = db.query(Receipt).filter(
		Receipt.id == receipt_id,
		Receipt.user_id == user_id,
		Receipt.is_deleted == False
	).first()
	
	if not receipt:
		return False
	
	# Remove friend associations
	db.query(ReceiptFriend).filter(
		ReceiptFriend.receipt_id == receipt_id,
		ReceiptFriend.friend_id.in_(friend_ids)
	).delete(synchronize_session=False)
	
	db.commit()
	return True

def get_receipt_friends(db: Session, receipt_id: int, user_id: int) -> List[Friend]:
	"""Get all friends associated with a receipt."""
	# Verify the receipt belongs to the user
	receipt = db.query(Receipt).filter(
		Receipt.id == receipt_id,
		Receipt.user_id == user_id,
		Receipt.is_deleted == False
	).first()
	
	if not receipt:
		return []
	
	# Get friends through the association table
	friends = db.query(Friend).join(ReceiptFriend).filter(
		ReceiptFriend.receipt_id == receipt_id,
		Friend.is_deleted == False
	).all()
	
	return friends

def update_receipt_friends(db: Session, receipt_id: int, friend_ids: List[int], user_id: int) -> bool:
	"""Replace all friends associated with a receipt with the new list."""
	# Verify the receipt belongs to the user
	receipt = db.query(Receipt).filter(
		Receipt.id == receipt_id,
		Receipt.user_id == user_id,
		Receipt.is_deleted == False
	).first()
	
	if not receipt:
		return False
	
	# Verify all friends belong to the user
	if friend_ids:
		friends = db.query(Friend).filter(
			Friend.id.in_(friend_ids),
			Friend.user_id == user_id,
			Friend.is_deleted == False
		).all()
		
		if len(friends) != len(friend_ids):
			return False
	
	# Remove all existing associations
	db.query(ReceiptFriend).filter(
		ReceiptFriend.receipt_id == receipt_id
	).delete(synchronize_session=False)
	
	# Add new associations
	for friend_id in friend_ids:
		receipt_friend = ReceiptFriend(
			receipt_id=receipt_id,
			friend_id=friend_id
		)
		db.add(receipt_friend)
	
	db.commit()
	return True

def get_friend_receipts(db: Session, friend_id: int, user_id: int) -> List[Receipt]:
	"""Get all receipts associated with a specific friend."""
	# Verify the friend belongs to the user
	friend = db.query(Friend).filter(
		Friend.id == friend_id,
		Friend.user_id == user_id,
		Friend.is_deleted == False
	).first()
	
	if not friend:
		return []
	
	# Get receipts through the association table
	receipts = db.query(Receipt).join(ReceiptFriend).filter(
		ReceiptFriend.friend_id == friend_id,
		Receipt.is_deleted == False
	).all()
	
	return receipts

def remove_friend_from_all_receipts(db: Session, friend_id: int, user_id: int) -> bool:
	"""Remove a friend from all receipts (useful when deleting a friend)."""
	# Verify the friend belongs to the user
	friend = db.query(Friend).filter(
		Friend.id == friend_id,
		Friend.user_id == user_id,
		Friend.is_deleted == False
	).first()
	
	if not friend:
		return False
	
	# Remove all associations for this friend
	db.query(ReceiptFriend).filter(
		ReceiptFriend.friend_id == friend_id
	).delete(synchronize_session=False)
	
	db.commit()
	return True
