"""Item repository for item-related database operations."""

from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from app.repositories.base import BaseRepository
from app.db.models.item import Item
from app.db.models.variation import Variation
from app.schemas.receipt import Item as ItemSchema


class ItemRepository(BaseRepository[Item]):
    """Repository for Item entity operations."""
    
    def __init__(self, db: Session, correlation_id: Optional[str] = None):
        super().__init__(db, Item, correlation_id)
    
    def get_by_receipt(self, receipt_id: int) -> List[Item]:
        """Get all items for a specific receipt.
        
        Args:
            receipt_id: Receipt ID to filter by
            
        Returns:
            List of Item instances for the receipt
        """
        return self.get_multi(filters={"receipt_id": receipt_id})
    
    def get_with_variations(self, item_id: int) -> Optional[Item]:
        """Get item with all variations loaded.
        
        Args:
            item_id: Item ID
            
        Returns:
            Item instance with variations loaded or None if not found
        """
        result = self.db.query(self.model).options(
            joinedload(self.model.variations)
        ).filter(
            self.model.id == item_id,
            self.model.is_deleted == False
        ).first()
        
        self._log_operation("get_with_variations", item_id=item_id, found=result is not None)
        return result
    
    def get_by_receipt_with_variations(self, receipt_id: int) -> List[Item]:
        """Get all items for a receipt with variations loaded.
        
        Args:
            receipt_id: Receipt ID
            
        Returns:
            List of Item instances with variations loaded
        """
        results = self.db.query(self.model).options(
            joinedload(self.model.variations)
        ).filter(
            self.model.receipt_id == receipt_id,
            self.model.is_deleted == False
        ).all()
        
        self._log_operation("get_by_receipt_with_variations", receipt_id=receipt_id, count=len(results))
        return results
    
    def create_item(self, item_data: ItemSchema, receipt_id: int) -> Item:
        """Create a new item for a receipt.
        
        Args:
            item_data: Item creation data
            receipt_id: Receipt ID to associate with
            
        Returns:
            Created Item instance
        """
        create_data = {
            "item_name": item_data.item_name,
            "quantity": item_data.quantity,
            "unit_price": item_data.unit_price,
            "receipt_id": receipt_id
        }
        
        return self.create(create_data)
    
    def create_item_with_variations(self, item_data: ItemSchema, receipt_id: int) -> Item:
        """Create item with variations in a single operation.
        
        Args:
            item_data: Item creation data including variations
            receipt_id: Receipt ID to associate with
            
        Returns:
            Created Item instance with variations
        """
        # Create the item first
        item = self.create_item(item_data, receipt_id)
        
        # Create variations if provided
        if item_data.variation:
            for variation_data in item_data.variation:
                db_variation = Variation(
                    variation_name=variation_data.variation_name,
                    price=variation_data.price,
                    item_id=item.id
                )
                self.db.add(db_variation)
            
            self.db.flush()
        
        self._log_operation("create_item_with_variations", item_id=item.id, variations_count=len(item_data.variation) if item_data.variation else 0)
        return item
    
    def update_item_quantity(self, item_id: int, quantity: int) -> Optional[Item]:
        """Update item quantity.
        
        Args:
            item_id: Item ID
            quantity: New quantity
            
        Returns:
            Updated Item instance or None if not found
        """
        return self.update(item_id, {"quantity": quantity})
    
    def update_item_price(self, item_id: int, unit_price: float) -> Optional[Item]:
        """Update item unit price.
        
        Args:
            item_id: Item ID
            unit_price: New unit price
            
        Returns:
            Updated Item instance or None if not found
        """
        return self.update(item_id, {"unit_price": unit_price})
    
    def get_receipt_items_count(self, receipt_id: int) -> int:
        """Get total number of items for a receipt.
        
        Args:
            receipt_id: Receipt ID
            
        Returns:
            Number of items for the receipt
        """
        return self.count(filters={"receipt_id": receipt_id})
