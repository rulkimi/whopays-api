"""Receipt repository for receipt-related database operations."""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text

from app.repositories.base import BaseRepository
from app.db.models.receipt import Receipt
from app.db.models.item import Item
from app.db.models.variation import Variation
from app.schemas.receipt import ReceiptBase


class ReceiptRepository(BaseRepository[Receipt]):
    """Repository for Receipt entity operations."""
    
    def __init__(self, db: Session, correlation_id: Optional[str] = None):
        super().__init__(db, Receipt, correlation_id)
    
    def get_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Receipt]:
        """Get receipts for a specific user with pagination.
        
        Args:
            user_id: User ID to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Receipt instances for the user
        """
        return self.get_multi(
            skip=skip,
            limit=limit,
            filters={"user_id": user_id},
            order_by="created_at"
        )
    
    def get_by_user_with_relationships(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Receipt]:
        """Get receipts for a specific user with all relationships loaded.
        
        Args:
            user_id: User ID to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Receipt instances with items, variations, and friends loaded
        """
        from app.db.models.receipt_friend import ReceiptFriend
        from app.db.models.friend import Friend
        
        from app.db.models.item_friend import ItemFriend
        query = self.db.query(self.model).options(
            joinedload(self.model.items).joinedload(Item.variations),
            joinedload(self.model.items).joinedload(Item.item_friends).joinedload(ItemFriend.friend),
            joinedload(self.model.friends).joinedload(ReceiptFriend.friend)
        ).filter(
            self.model.user_id == user_id,
            self.model.is_deleted == False
        )
        
        # Apply ordering
        query = query.order_by(self.model.created_at.desc())
        
        results = query.offset(skip).limit(limit).all()
        self._log_operation("get_by_user_with_relationships", user_id=user_id, count=len(results), skip=skip, limit=limit)
        return results
    
    def get_by_id_and_user(self, receipt_id: int, user_id: int) -> Optional[Receipt]:
        """Get receipt by ID for a specific user with relationships loaded.
        
        Args:
            receipt_id: Receipt ID
            user_id: User ID to verify ownership
            
        Returns:
            Receipt instance with items, variations, and friends loaded or None if not found or not owned by user
        """
        from app.db.models.receipt_friend import ReceiptFriend
        from app.db.models.friend import Friend
        
        from app.db.models.item_friend import ItemFriend
        result = self.db.query(self.model).options(
            joinedload(self.model.items).joinedload(Item.variations),
            joinedload(self.model.items).joinedload(Item.item_friends).joinedload(ItemFriend.friend),
            joinedload(self.model.friends).joinedload(ReceiptFriend.friend)
        ).filter(
            self.model.id == receipt_id,
            self.model.user_id == user_id,
            self.model.is_deleted == False
        ).first()
        
        self._log_operation("get_by_id_and_user", receipt_id=receipt_id, user_id=user_id, found=result is not None)
        return result
    
    def get_multiple_by_ids_and_user(self, receipt_ids: List[int], user_id: int) -> List[Receipt]:
        """Get multiple receipts by IDs for a specific user.
        
        Args:
            receipt_ids: List of Receipt IDs
            user_id: User ID to verify ownership
            
        Returns:
            List of Receipt instances owned by the user
        """
        results = self.db.query(self.model).filter(
            self.model.id.in_(receipt_ids),
            self.model.user_id == user_id,
            self.model.is_deleted == False
        ).all()
        
        self._log_operation("get_multiple_by_ids_and_user", receipt_ids=receipt_ids, user_id=user_id, found_count=len(results))
        return results
    
    def get_with_items(self, receipt_id: int, user_id: int) -> Optional[Receipt]:
        """Get receipt with items, variations, and item-friends loaded.
        
        Args:
            receipt_id: Receipt ID
            user_id: User ID to verify ownership
            
        Returns:
            Receipt instance with items loaded or None if not found
        """
        from app.db.models.item_friend import ItemFriend
        result = self.db.query(self.model).options(
            joinedload(self.model.items).joinedload(Item.variations),
            joinedload(self.model.items).joinedload(Item.item_friends).joinedload(ItemFriend.friend)
        ).filter(
            self.model.id == receipt_id,
            self.model.user_id == user_id,
            self.model.is_deleted == False
        ).first()
        
        self._log_operation("get_with_items", receipt_id=receipt_id, user_id=user_id, found=result is not None)
        return result
    
    def create_receipt(self, receipt_data: ReceiptBase, user_id: int, receipt_url: Optional[str] = None) -> Receipt:
        """Create a new receipt.
        
        Args:
            receipt_data: Receipt creation data
            user_id: Owner user ID
            receipt_url: Optional receipt image URL
            
        Returns:
            Created Receipt instance
        """
        create_data = {
            "restaurant_name": receipt_data.restaurant_name,
            "total_amount": receipt_data.total_amount,
            "tax": receipt_data.tax,
            "service_charge": receipt_data.service_charge,
            "currency": receipt_data.currency,
            "receipt_url": receipt_url,
            "user_id": user_id
        }
        
        return self.create(create_data)
    
    def search_by_restaurant(self, user_id: int, restaurant_name: str, skip: int = 0, limit: int = 100) -> List[Receipt]:
        """Search receipts by restaurant name for a user.
        
        Args:
            user_id: User ID to filter by
            restaurant_name: Restaurant name to search for (case-insensitive)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching Receipt instances
        """
        results = self.db.query(self.model).filter(
            self.model.user_id == user_id,
            self.model.restaurant_name.ilike(f"%{restaurant_name}%"),
            self.model.is_deleted == False
        ).order_by(self.model.created_at.desc()).offset(skip).limit(limit).all()
        
        self._log_operation("search_by_restaurant", user_id=user_id, restaurant_name=restaurant_name, count=len(results))
        return results
    
    def get_user_receipt_count(self, user_id: int) -> int:
        """Get total number of receipts for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of receipts for the user
        """
        return self.count(filters={"user_id": user_id})
    
    def delete_with_items(self, receipt_id: int, user_id: int) -> bool:
        """Soft delete receipt and all related items and variations.
        
        Args:
            receipt_id: Receipt ID to delete
            user_id: User ID to verify ownership
            
        Returns:
            True if deleted, False if not found or not owned by user
        """
        receipt = self.get_by_id_and_user(receipt_id, user_id)
        if not receipt:
            return False
        
        # Soft delete the receipt
        receipt.is_deleted = True
        if hasattr(receipt, 'deleted_at'):
            receipt.deleted_at = self.db.execute(text('SELECT NOW()')).scalar()
        
        # Soft delete all items
        items = self.db.query(Item).filter(
            Item.receipt_id == receipt_id,
            Item.is_deleted == False
        ).all()
        
        for item in items:
            item.is_deleted = True
            if hasattr(item, 'deleted_at'):
                item.deleted_at = self.db.execute(text('SELECT NOW()')).scalar()
            
            # Soft delete all variations for this item
            variations = self.db.query(Variation).filter(
                Variation.item_id == item.id,
                Variation.is_deleted == False
            ).all()
            
            for variation in variations:
                variation.is_deleted = True
                if hasattr(variation, 'deleted_at'):
                    variation.deleted_at = self.db.execute(text('SELECT NOW()')).scalar()
        
        self.db.flush()
        self._log_operation("delete_with_items", receipt_id=receipt_id, user_id=user_id, items_count=len(items))
        return True
