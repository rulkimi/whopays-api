from sqlalchemy.orm import Session
from app.db.models.item_friend import ItemFriend
from app.db.models.item import Item
from app.db.models.friend import Friend
from typing import List, Optional

from app.services.file_services import generate_presigned_url

from sqlalchemy import func

def add_friends_to_item(db: Session, item_id: int, friend_ids: List[int], user_id: int) -> bool:
	"""Add friends to an item"""
	try:
		print(f"Attempting to add friends {friend_ids} to item {item_id} for user {user_id}")
		# Verify the item belongs to the user
		item = db.query(Item).join(Item.receipt).filter(
			Item.id == item_id,
			Item.receipt.has(user_id=user_id),
			Item.is_deleted == False
		).first()
		
		if not item:
			print(f"Item {item_id} not found or does not belong to user {user_id}")
			return False
		
		# Verify all friends belong to the user
		friends = db.query(Friend).filter(
			Friend.id.in_(friend_ids),
			Friend.user_id == user_id,
			Friend.is_deleted == False
		).all()
		
		if len(friends) != len(friend_ids):
			print(f"Some friend_ids {friend_ids} do not belong to user {user_id} or are deleted")
			return False
		
		# Remove existing item-friend relationships
		print(f"Removing existing item-friend relationships for item {item_id}")
		db.query(ItemFriend).filter(
			ItemFriend.item_id == item_id,
			ItemFriend.is_deleted == False
		).update({"is_deleted": True, "deleted_at": func.now()})
		
		# Add new item-friend relationships
		for friend_id in friend_ids:
			print(f"Adding friend {friend_id} to item {item_id}")
			item_friend = ItemFriend(
				item_id=item_id,
				friend_id=friend_id
			)
			db.add(item_friend)
		
		db.commit()
		print(f"Successfully added friends {friend_ids} to item {item_id} for user {user_id}")
		return True
	except Exception as e:
		print(f"Exception occurred while adding friends to item: {e}")
		db.rollback()
		return False

def remove_friends_from_item(db: Session, item_id: int, friend_ids: List[int], user_id: int) -> bool:
	"""Remove friends from an item"""
	try:
		# Verify the item belongs to the user
		item = db.query(Item).join(Item.receipt).filter(
			Item.id == item_id,
			Item.receipt.has(user_id=user_id),
			Item.is_deleted == False
		).first()
		
		if not item:
			return False
		
		# Soft delete the specified item-friend relationships
		db.query(ItemFriend).filter(
			ItemFriend.item_id == item_id,
			ItemFriend.friend_id.in_(friend_ids),
			ItemFriend.is_deleted == False
		).update({"is_deleted": True, "deleted_at": db.func.now()})
		
		db.commit()
		return True
	except Exception:
		db.rollback()
		return False

def get_item_friends(db: Session, item_id: int, user_id: int) -> List[dict]:
	"""Get all friends associated with an item"""
	item_friends = db.query(ItemFriend).join(ItemFriend.item).join(Item.receipt).filter(
		ItemFriend.item_id == item_id,
		Item.receipt.has(user_id=user_id),
		ItemFriend.is_deleted == False
	).all()
	
	friends = []
	for item_friend in item_friends:
		friend = item_friend.friend
		friends.append({
			"id": friend.id,
			"name": friend.name,
			"photo_url": generate_presigned_url(friend.photo_url),
			"user_id": friend.user_id
		})
	
	return friends

def update_item_friends(db: Session, item_id: int, friend_ids: List[int], user_id: int) -> bool:
	"""Replace all friends associated with an item"""
	return add_friends_to_item(db, item_id, friend_ids, user_id)
