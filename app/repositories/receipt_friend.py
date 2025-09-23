"""Receipt-Friend association repository for managing receipt-friend relationships."""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository
from app.db.models.receipt_friend import ReceiptFriend
from app.db.models.friend import Friend


class ReceiptFriendRepository(BaseRepository[ReceiptFriend]):
    """Repository for ReceiptFriend association operations."""
    
    def __init__(self, db: Session, correlation_id: Optional[str] = None):
        super().__init__(db, ReceiptFriend, correlation_id)
    
    def add_friends_to_receipt(self, receipt_id: int, friend_ids: List[int]) -> List[ReceiptFriend]:
        """Add friends to a receipt.
        
        Args:
            receipt_id: Receipt ID
            friend_ids: List of Friend IDs to associate
            
        Returns:
            List of created ReceiptFriend associations
        """
        associations = []
        
        for friend_id in friend_ids:
            # Check if association already exists
            existing = self.db.query(self.model).filter(
                self.model.receipt_id == receipt_id,
                self.model.friend_id == friend_id
            ).first()
            
            if not existing:
                association = self.create({
                    "receipt_id": receipt_id,
                    "friend_id": friend_id
                })
                associations.append(association)
        
        self._log_operation("add_friends_to_receipt", receipt_id=receipt_id, friend_ids=friend_ids, created_count=len(associations))
        return associations
    
    def remove_friends_from_receipt(self, receipt_id: int, friend_ids: List[int]) -> bool:
        """Remove friends from a receipt.
        
        Args:
            receipt_id: Receipt ID
            friend_ids: List of Friend IDs to remove
            
        Returns:
            True if any associations were removed
        """
        removed_count = self.db.query(self.model).filter(
            self.model.receipt_id == receipt_id,
            self.model.friend_id.in_(friend_ids)
        ).delete(synchronize_session=False)
        
        if removed_count > 0:
            self.db.flush()
        
        self._log_operation("remove_friends_from_receipt", receipt_id=receipt_id, friend_ids=friend_ids, removed_count=removed_count)
        return removed_count > 0
    
    def get_receipt_friends(self, receipt_id: int) -> List[Friend]:
        """Get all friends associated with a receipt.
        
        Args:
            receipt_id: Receipt ID
            
        Returns:
            List of Friend instances associated with the receipt
        """
        results = self.db.query(Friend).join(
            self.model, Friend.id == self.model.friend_id
        ).filter(
            self.model.receipt_id == receipt_id,
            Friend.is_deleted == False
        ).all()
        
        self._log_operation("get_receipt_friends", receipt_id=receipt_id, count=len(results))
        return results
    
    def get_friend_receipts(self, friend_id: int) -> List[int]:
        """Get all receipt IDs associated with a friend.
        
        Args:
            friend_id: Friend ID
            
        Returns:
            List of receipt IDs associated with the friend
        """
        results = self.db.query(self.model.receipt_id).filter(
            self.model.friend_id == friend_id
        ).all()
        
        receipt_ids = [r[0] for r in results]
        self._log_operation("get_friend_receipts", friend_id=friend_id, count=len(receipt_ids))
        return receipt_ids
    
    def clear_receipt_friends(self, receipt_id: int) -> bool:
        """Remove all friends from a receipt.
        
        Args:
            receipt_id: Receipt ID
            
        Returns:
            True if any associations were removed
        """
        removed_count = self.db.query(self.model).filter(
            self.model.receipt_id == receipt_id
        ).delete(synchronize_session=False)
        
        if removed_count > 0:
            self.db.flush()
        
        self._log_operation("clear_receipt_friends", receipt_id=receipt_id, removed_count=removed_count)
        return removed_count > 0
    
    def is_friend_associated_with_receipt(self, receipt_id: int, friend_id: int) -> bool:
        """Check if a friend is associated with a receipt.
        
        Args:
            receipt_id: Receipt ID
            friend_id: Friend ID
            
        Returns:
            True if association exists
        """
        result = self.db.query(self.model).filter(
            self.model.receipt_id == receipt_id,
            self.model.friend_id == friend_id
        ).first() is not None
        
        self._log_operation("is_friend_associated_with_receipt", receipt_id=receipt_id, friend_id=friend_id, associated=result)
        return result
