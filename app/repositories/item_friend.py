"""Item-Friend association repository for managing item-friend relationships."""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.repositories.base import BaseRepository
from app.db.models.item_friend import ItemFriend
from app.db.models.friend import Friend


class ItemFriendRepository(BaseRepository[ItemFriend]):
    """Repository for ItemFriend association operations."""
    
    def __init__(self, db: Session, correlation_id: Optional[str] = None):
        super().__init__(db, ItemFriend, correlation_id)
    
    def add_friends_to_item(self, item_id: int, friend_ids: List[int]) -> List[ItemFriend]:
        """Add friends to an item.
        
        Args:
            item_id: Item ID
            friend_ids: List of Friend IDs to associate
            
        Returns:
            List of created ItemFriend associations
        """
        associations = []
        
        for friend_id in friend_ids:
            # Check if association already exists and is not deleted
            existing = self.db.query(self.model).filter(
                self.model.item_id == item_id,
                self.model.friend_id == friend_id,
                self.model.is_deleted == False
            ).first()
            
            if not existing:
                association = self.create({
                    "item_id": item_id,
                    "friend_id": friend_id
                })
                associations.append(association)
        
        self._log_operation("add_friends_to_item", item_id=item_id, friend_ids=friend_ids, created_count=len(associations))
        return associations
    
    def remove_friends_from_item(self, item_id: int, friend_ids: List[int]) -> bool:
        """Remove friends from an item (soft delete).
        
        Args:
            item_id: Item ID
            friend_ids: List of Friend IDs to remove
            
        Returns:
            True if any associations were removed
        """
        associations = self.db.query(self.model).filter(
            self.model.item_id == item_id,
            self.model.friend_id.in_(friend_ids),
            self.model.is_deleted == False
        ).all()
        
        removed_count = 0
        for association in associations:
            association.is_deleted = True
            if hasattr(association, 'deleted_at'):
                association.deleted_at = self.db.execute(text('SELECT NOW()')).scalar()
            removed_count += 1
        
        if removed_count > 0:
            self.db.flush()
        
        self._log_operation("remove_friends_from_item", item_id=item_id, friend_ids=friend_ids, removed_count=removed_count)
        return removed_count > 0
    
    def get_item_friends(self, item_id: int) -> List[Friend]:
        """Get all friends associated with an item.
        
        Args:
            item_id: Item ID
            
        Returns:
            List of Friend instances associated with the item
        """
        results = self.db.query(Friend).join(
            self.model, Friend.id == self.model.friend_id
        ).filter(
            self.model.item_id == item_id,
            self.model.is_deleted == False,
            Friend.is_deleted == False
        ).all()
        
        self._log_operation("get_item_friends", item_id=item_id, count=len(results))
        return results
    
    def get_friend_items(self, friend_id: int) -> List[int]:
        """Get all item IDs associated with a friend.
        
        Args:
            friend_id: Friend ID
            
        Returns:
            List of item IDs associated with the friend
        """
        results = self.db.query(self.model.item_id).filter(
            self.model.friend_id == friend_id,
            self.model.is_deleted == False
        ).all()
        
        item_ids = [r[0] for r in results]
        self._log_operation("get_friend_items", friend_id=friend_id, count=len(item_ids))
        return item_ids
    
    def clear_item_friends(self, item_id: int) -> bool:
        """Remove all friends from an item (soft delete).
        
        Args:
            item_id: Item ID
            
        Returns:
            True if any associations were removed
        """
        associations = self.db.query(self.model).filter(
            self.model.item_id == item_id,
            self.model.is_deleted == False
        ).all()
        
        removed_count = 0
        for association in associations:
            association.is_deleted = True
            if hasattr(association, 'deleted_at'):
                association.deleted_at = self.db.execute(text('SELECT NOW()')).scalar()
            removed_count += 1
        
        if removed_count > 0:
            self.db.flush()
        
        self._log_operation("clear_item_friends", item_id=item_id, removed_count=removed_count)
        return removed_count > 0
    
    def is_friend_associated_with_item(self, item_id: int, friend_id: int) -> bool:
        """Check if a friend is associated with an item.
        
        Args:
            item_id: Item ID
            friend_id: Friend ID
            
        Returns:
            True if association exists and is not deleted
        """
        result = self.db.query(self.model).filter(
            self.model.item_id == item_id,
            self.model.friend_id == friend_id,
            self.model.is_deleted == False
        ).first() is not None
        
        self._log_operation("is_friend_associated_with_item", item_id=item_id, friend_id=friend_id, associated=result)
        return result
    
    def replace_item_friends(self, item_id: int, friend_ids: List[int]) -> List[ItemFriend]:
        """Replace all friends for an item with new ones.
        
        Args:
            item_id: Item ID
            friend_ids: List of new Friend IDs to associate
            
        Returns:
            List of created ItemFriend associations
        """
        # First clear existing friends
        self.clear_item_friends(item_id)
        
        # Then add new friends
        return self.add_friends_to_item(item_id, friend_ids)
