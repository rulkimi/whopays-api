"""Item-Friend association service with comprehensive error handling and validation.

This service provides item-friend association management with comprehensive error handling,
input validation, and structured logging. It follows the standard service
architecture pattern for item-friend operations.
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.services.base import BaseService
from app.services.exceptions import (
    ItemFriendError,
    ItemNotFoundError,
    ItemFriendsValidationError,
    ItemFriendAssociationError,
    ValidationError
)
from app.repositories.item_friend import ItemFriendRepository
from app.repositories.item import ItemRepository
from app.repositories.friend import FriendRepository
from app.db.models.item import Item
from app.schemas.item_friend import (
    AddFriendsToItemInput,
    RemoveFriendsFromItemInput,
    UpdateItemFriendsInput,
    GetItemFriendsInput,
    AddFriendsToItemResult,
    RemoveFriendsFromItemResult,
    UpdateItemFriendsResult,
    GetItemFriendsResult,
    FriendBasic
)


class ItemFriendService(BaseService):
    """Service class for handling item-friend association operations.
    
    This service demonstrates the standard architecture pattern:
    - Dependency injection through constructor or _set_repositories
    - Comprehensive error handling with domain exceptions
    - Input validation using Pydantic schemas
    - Structured logging with correlation IDs
    - Transaction management for data operations
    - Type-safe result objects instead of Optional returns
    
    Security Features:
    - Input sanitization and validation
    - User ownership verification for items and friends
    - Structured audit logging
    - Clear separation of item-friend association concerns
    """
    
    def __init__(self, correlation_id: Optional[str] = None, **repositories):
        """Initialize item-friend service.
        
        Args:
            correlation_id: Optional request correlation ID for logging
            **repositories: Repository instances (item_friend_repo, item_repo, friend_repo)
        """
        super().__init__(correlation_id)
        if repositories:
            self._set_repositories(**repositories)
        
        # Ensure required repositories are available
        required_repos = ['item_friend_repo', 'item_repo', 'friend_repo']
        for repo_name in required_repos:
            if not hasattr(self, repo_name):
                raise ValidationError(
                    field=repo_name,
                    message=f"{repo_name} is required for ItemFriendService",
                    correlation_id=correlation_id
                )
    
    def _sanitize_input(self, input_data):
        """Sanitize input data for security."""
        # Input is already validated by Pydantic schemas
        return input_data
    
    def _verify_item_ownership(self, item_id: int, user_id: int, db: Session) -> Item:
        """Verify item exists and belongs to the user.
        
        Args:
            item_id: Item ID to verify
            user_id: User ID to verify ownership
            db: Database session
            
        Returns:
            Item instance if found and owned by user
            
        Raises:
            ItemNotFoundError: If item not found or not owned by user
        """
        # Query item with receipt join to verify ownership
        item = db.query(Item).join(Item.receipt).filter(
            Item.id == item_id,
            Item.receipt.has(user_id=user_id),
            Item.is_deleted == False
        ).first()
        
        if not item:
            raise ItemNotFoundError(
                item_id=item_id,
                user_id=user_id,
                correlation_id=self.correlation_id
            )
        
        return item
    
    def _verify_friends_ownership(self, friend_ids: List[int], user_id: int, db: Session) -> List[int]:
        """Verify all friends exist and belong to the user.
        
        Args:
            friend_ids: List of friend IDs to verify
            user_id: User ID to verify ownership
            db: Database session
            
        Returns:
            List of valid friend IDs
            
        Raises:
            ItemFriendsValidationError: If any friends are invalid or not owned by user
        """
        if not friend_ids:
            return []
        
        friends = self.friend_repo.get_by_ids_and_user(friend_ids, user_id)
        found_ids = [f.id for f in friends]
        
        invalid_ids = [fid for fid in friend_ids if fid not in found_ids]
        if invalid_ids:
            raise ItemFriendsValidationError(
                invalid_friend_ids=invalid_ids,
                user_id=user_id,
                correlation_id=self.correlation_id
            )
        
        return found_ids
    
    def add_friends_to_item(self, input_data: AddFriendsToItemInput, user_id: int, db: Session) -> AddFriendsToItemResult:
        """Add friends to an item with comprehensive validation.
        
        This method demonstrates the standard service pattern:
        - Input validation through Pydantic schema
        - Domain exception handling
        - Transaction management
        - Structured result objects
        - Security-focused logging
        
        Args:
            input_data: Validated input data from AddFriendsToItemInput
            user_id: User ID for ownership verification
            db: Database session for transaction management
            
        Returns:
            AddFriendsToItemResult with success status and data or error info
            
        Raises:
            ItemNotFoundError: If item not found or not owned by user
            ItemFriendsValidationError: If friends are invalid or not owned by user
            ItemFriendAssociationError: If association operation fails
        """
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation(
            "add_friends_to_item_attempt",
            item_id=sanitized_input.item_id,
            friend_count=len(sanitized_input.friend_ids),
            user_id=user_id
        )
        
        try:
            def _add_friends_operation() -> dict:
                # Verify item ownership
                item = self._verify_item_ownership(sanitized_input.item_id, user_id, db)
                
                # Verify friends ownership
                valid_friend_ids = self._verify_friends_ownership(sanitized_input.friend_ids, user_id, db)
                
                # Replace all friends for the item (clear existing first)
                associations = self.item_friend_repo.replace_item_friends(
                    sanitized_input.item_id, 
                    valid_friend_ids
                )
                
                # Get current friends count
                current_friends = self.item_friend_repo.get_item_friends(sanitized_input.item_id)
                
                self.log_operation(
                    "add_friends_to_item_success",
                    item_id=sanitized_input.item_id,
                    added_friends=len(associations),
                    total_friends=len(current_friends)
                )
                
                return {
                    "item_id": sanitized_input.item_id,
                    "added_friend_ids": valid_friend_ids,
                    "friends_count": len(current_friends)
                }
            
            result = self.run_in_transaction(db, _add_friends_operation)
            return AddFriendsToItemResult(
                success=True,
                data=result,
                message="Friends added to item successfully"
            )
            
        except ItemFriendError as e:
            self.log_operation(
                "add_friends_to_item_failed",
                error_code=e.error_code,
                reason=e.error_code.lower(),
                item_id=sanitized_input.item_id
            )
            return AddFriendsToItemResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "add_friends_to_item_error",
                error_type=type(e).__name__,
                error_message=str(e),
                item_id=sanitized_input.item_id
            )
            raise
    
    def remove_friends_from_item(self, input_data: RemoveFriendsFromItemInput, user_id: int, db: Session) -> RemoveFriendsFromItemResult:
        """Remove specific friends from an item.
        
        Args:
            input_data: Validated input data from RemoveFriendsFromItemInput
            user_id: User ID for ownership verification
            db: Database session for transaction management
            
        Returns:
            RemoveFriendsFromItemResult with success status and data or error info
        """
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation(
            "remove_friends_from_item_attempt",
            item_id=sanitized_input.item_id,
            friend_count=len(sanitized_input.friend_ids),
            user_id=user_id
        )
        
        try:
            def _remove_friends_operation() -> dict:
                # Verify item ownership
                item = self._verify_item_ownership(sanitized_input.item_id, user_id, db)
                
                # Remove the specified friends
                removed = self.item_friend_repo.remove_friends_from_item(
                    sanitized_input.item_id,
                    sanitized_input.friend_ids
                )
                
                # Get current friends count
                current_friends = self.item_friend_repo.get_item_friends(sanitized_input.item_id)
                
                self.log_operation(
                    "remove_friends_from_item_success",
                    item_id=sanitized_input.item_id,
                    removed_friends=len(sanitized_input.friend_ids),
                    total_friends=len(current_friends)
                )
                
                return {
                    "item_id": sanitized_input.item_id,
                    "removed_friend_ids": sanitized_input.friend_ids,
                    "friends_count": len(current_friends)
                }
            
            result = self.run_in_transaction(db, _remove_friends_operation)
            return RemoveFriendsFromItemResult(
                success=True,
                data=result,
                message="Friends removed from item successfully"
            )
            
        except ItemFriendError as e:
            self.log_operation(
                "remove_friends_from_item_failed",
                error_code=e.error_code,
                reason=e.error_code.lower(),
                item_id=sanitized_input.item_id
            )
            return RemoveFriendsFromItemResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "remove_friends_from_item_error",
                error_type=type(e).__name__,
                error_message=str(e),
                item_id=sanitized_input.item_id
            )
            raise
    
    def update_item_friends(self, input_data: UpdateItemFriendsInput, user_id: int, db: Session) -> UpdateItemFriendsResult:
        """Replace all friends associated with an item.
        
        Args:
            input_data: Validated input data from UpdateItemFriendsInput
            user_id: User ID for ownership verification
            db: Database session for transaction management
            
        Returns:
            UpdateItemFriendsResult with success status and data or error info
        """
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation(
            "update_item_friends_attempt",
            item_id=sanitized_input.item_id,
            friend_count=len(sanitized_input.friend_ids),
            user_id=user_id
        )
        
        try:
            def _update_friends_operation() -> dict:
                # Verify item ownership
                item = self._verify_item_ownership(sanitized_input.item_id, user_id, db)
                
                # Verify friends ownership if any provided
                valid_friend_ids = self._verify_friends_ownership(sanitized_input.friend_ids, user_id, db)
                
                # Replace all friends for the item
                associations = self.item_friend_repo.replace_item_friends(
                    sanitized_input.item_id,
                    valid_friend_ids
                )
                
                # Get current friends count
                current_friends = self.item_friend_repo.get_item_friends(sanitized_input.item_id)
                
                self.log_operation(
                    "update_item_friends_success",
                    item_id=sanitized_input.item_id,
                    updated_friends=len(valid_friend_ids),
                    total_friends=len(current_friends)
                )
                
                return {
                    "item_id": sanitized_input.item_id,
                    "friend_ids": valid_friend_ids,
                    "friends_count": len(current_friends)
                }
            
            result = self.run_in_transaction(db, _update_friends_operation)
            return UpdateItemFriendsResult(
                success=True,
                data=result,
                message="Item friends updated successfully"
            )
            
        except ItemFriendError as e:
            self.log_operation(
                "update_item_friends_failed",
                error_code=e.error_code,
                reason=e.error_code.lower(),
                item_id=sanitized_input.item_id
            )
            return UpdateItemFriendsResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "update_item_friends_error",
                error_type=type(e).__name__,
                error_message=str(e),
                item_id=sanitized_input.item_id
            )
            raise
    
    def get_item_friends(self, input_data: GetItemFriendsInput, user_id: int, db: Session) -> GetItemFriendsResult:
        """Get all friends associated with an item.
        
        Args:
            input_data: Validated input data from GetItemFriendsInput
            user_id: User ID for ownership verification
            db: Database session for transaction management
            
        Returns:
            GetItemFriendsResult with success status and friends data or error info
        """
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation(
            "get_item_friends_attempt",
            item_id=sanitized_input.item_id,
            user_id=user_id
        )
        
        try:
            # Verify item ownership
            item = self._verify_item_ownership(sanitized_input.item_id, user_id, db)
            
            # Get friends associated with the item
            friends = self.item_friend_repo.get_item_friends(sanitized_input.item_id)
            
            # Convert to schema format
            friends_data = [
                FriendBasic(
                    id=friend.id,
                    name=friend.name,
                    photo_url=friend.photo_url,
                    user_id=friend.user_id
                )
                for friend in friends
            ]
            
            self.log_operation(
                "get_item_friends_success",
                item_id=sanitized_input.item_id,
                friends_count=len(friends_data)
            )
            
            return GetItemFriendsResult(
                success=True,
                data=friends_data,
                message="Item friends retrieved successfully"
            )
            
        except ItemFriendError as e:
            self.log_operation(
                "get_item_friends_failed",
                error_code=e.error_code,
                reason=e.error_code.lower(),
                item_id=sanitized_input.item_id
            )
            return GetItemFriendsResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "get_item_friends_error",
                error_type=type(e).__name__,
                error_message=str(e),
                item_id=sanitized_input.item_id
            )
            raise


# Legacy function wrappers for backward compatibility
def add_friends_to_item(db: Session, item_id: int, friend_ids: List[int], user_id: int) -> bool:
    """Legacy wrapper for add_friends_to_item functionality."""
    # This is kept for backward compatibility but should be migrated to use the service
    from app.repositories.item_friend import ItemFriendRepository
    from app.repositories.item import ItemRepository  
    from app.repositories.friend import FriendRepository
    
    service = ItemFriendService(
        item_friend_repo=ItemFriendRepository(db),
        item_repo=ItemRepository(db),
        friend_repo=FriendRepository(db)
    )
    
    input_data = AddFriendsToItemInput(item_id=item_id, friend_ids=friend_ids)
    result = service.add_friends_to_item(input_data, user_id, db)
    return result.success


def remove_friends_from_item(db: Session, item_id: int, friend_ids: List[int], user_id: int) -> bool:
    """Legacy wrapper for remove_friends_from_item functionality."""
    from app.repositories.item_friend import ItemFriendRepository
    from app.repositories.item import ItemRepository
    from app.repositories.friend import FriendRepository
    
    service = ItemFriendService(
        item_friend_repo=ItemFriendRepository(db),
        item_repo=ItemRepository(db),
        friend_repo=FriendRepository(db)
    )
    
    input_data = RemoveFriendsFromItemInput(item_id=item_id, friend_ids=friend_ids)
    result = service.remove_friends_from_item(input_data, user_id, db)
    return result.success


def get_item_friends(db: Session, item_id: int, user_id: int) -> List[dict]:
    """Legacy wrapper for get_item_friends functionality."""
    from app.repositories.item_friend import ItemFriendRepository
    from app.repositories.item import ItemRepository
    from app.repositories.friend import FriendRepository
    
    service = ItemFriendService(
        item_friend_repo=ItemFriendRepository(db),
        item_repo=ItemRepository(db),
        friend_repo=FriendRepository(db)
    )
    
    input_data = GetItemFriendsInput(item_id=item_id)
    result = service.get_item_friends(input_data, user_id, db)
    
    if result.success and result.data:
        return [friend.dict() for friend in result.data]
    return []


def update_item_friends(db: Session, item_id: int, friend_ids: List[int], user_id: int) -> bool:
    """Legacy wrapper for update_item_friends functionality."""
    from app.repositories.item_friend import ItemFriendRepository
    from app.repositories.item import ItemRepository
    from app.repositories.friend import FriendRepository
    
    service = ItemFriendService(
        item_friend_repo=ItemFriendRepository(db),
        item_repo=ItemRepository(db),
        friend_repo=FriendRepository(db)
    )
    
    input_data = UpdateItemFriendsInput(item_id=item_id, friend_ids=friend_ids)
    result = service.update_item_friends(input_data, user_id, db)
    return result.success
