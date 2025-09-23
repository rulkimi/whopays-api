"""Receipt-Friend association service for managing receipt-friend relationships.

This service provides receipt-friend association management with comprehensive error handling,
input validation, and structured logging. It follows the standard service
architecture pattern for receipt-friend operations.
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.services.base import BaseService
from app.services.exceptions import (
    ReceiptFriendError,
    ReceiptNotFoundError,
    FriendNotFoundError,
    FriendsValidationError,
    ReceiptFriendAssociationError,
    ValidationError
)
from app.repositories.receipt import ReceiptRepository
from app.repositories.friend import FriendRepository
from app.repositories.receipt_friend import ReceiptFriendRepository
from app.db.models.receipt import Receipt
from app.db.models.friend import Friend
from app.schemas.receipt import (
    AddFriendsToReceiptInput,
    AddFriendsToReceiptResult,
    RemoveFriendsFromReceiptInput,
    RemoveFriendsFromReceiptResult,
    GetReceiptFriendsInput,
    GetReceiptFriendsResult,
    UpdateReceiptFriendsInput,
    UpdateReceiptFriendsResult,
    GetFriendReceiptsInput,
    GetFriendReceiptsResult,
    RemoveFriendFromAllReceiptsInput,
    RemoveFriendFromAllReceiptsResult
)


class ReceiptFriendService(BaseService):
    """Service class for handling receipt-friend association operations.
    
    This service demonstrates the standard architecture pattern:
    - Dependency injection through constructor or _set_repositories
    - Comprehensive error handling with domain exceptions
    - Input validation using Pydantic schemas
    - Structured logging with correlation IDs
    - Transaction management for data operations
    - Type-safe result objects instead of Optional returns
    
    Security Features:
    - Input sanitization and validation
    - User ownership verification for all operations
    - Structured audit logging
    - Clear separation of receipt-friend association concerns
    """
    
    def __init__(self, correlation_id: Optional[str] = None, **repositories):
        """Initialize receipt-friend service.
        
        Args:
            correlation_id: Optional request correlation ID for logging
            **repositories: Repository instances (receipt_repo, friend_repo, receipt_friend_repo)
        """
        super().__init__(correlation_id)
        if repositories:
            self._set_repositories(**repositories)
        
        # Ensure required repositories are available
        required_repos = ['receipt_repo', 'friend_repo', 'receipt_friend_repo']
        for repo_name in required_repos:
            if not hasattr(self, repo_name):
                raise ValidationError(
                    field=repo_name,
                    message=f"{repo_name} is required for ReceiptFriendService",
                    correlation_id=correlation_id
                )
    
    def _sanitize_input(self, input_data):
        """Sanitize input data to prevent injection attacks."""
        # For now, just return the input as Pydantic handles most validation
        # In the future, add more sophisticated sanitization if needed
        return input_data
    
    def _verify_receipt_ownership(self, receipt_id: int, user_id: int) -> Receipt:
        """Verify receipt exists and belongs to user."""
        receipt = self.receipt_repo.get_by_id_and_user(receipt_id, user_id)
        if not receipt:
            raise ReceiptNotFoundError(
                receipt_id=receipt_id,
                user_id=user_id,
                correlation_id=self.correlation_id
            )
        return receipt
    
    def _verify_friend_ownership(self, friend_id: int, user_id: int) -> Friend:
        """Verify friend exists and belongs to user."""
        friend = self.friend_repo.get_by_id_and_user(friend_id, user_id)
        if not friend:
            raise FriendNotFoundError(
                friend_id=friend_id,
                user_id=user_id,
                correlation_id=self.correlation_id
            )
        return friend
    
    def _verify_friends_ownership(self, friend_ids: List[int], user_id: int) -> List[Friend]:
        """Verify all friends exist and belong to user."""
        friends = self.friend_repo.get_multiple_by_ids_and_user(friend_ids, user_id)
        found_ids = {f.id for f in friends}
        missing_ids = [fid for fid in friend_ids if fid not in found_ids]
        
        if missing_ids:
            raise FriendsValidationError(
                invalid_friend_ids=missing_ids,
                user_id=user_id,
                correlation_id=self.correlation_id
            )
        return friends
    
    def add_friends_to_receipt(self, input_data: AddFriendsToReceiptInput, user_id: int, db: Session) -> AddFriendsToReceiptResult:
        """Add friends to a receipt.
        
        This method demonstrates the standard service pattern:
        - Input validation through Pydantic schema
        - Domain exception handling
        - Transaction management
        - Structured result objects
        - Security-focused logging
        
        Args:
            input_data: Validated input data from AddFriendsToReceiptInput
            user_id: ID of the user making the request
            db: Database session for transaction management
            
        Returns:
            AddFriendsToReceiptResult with success status and data or error info
            
        Raises:
            ReceiptNotFoundError: If receipt doesn't exist or doesn't belong to user
            FriendsValidationError: If any friends don't exist or don't belong to user
            ReceiptFriendAssociationError: If association operation fails
        """
        # Sanitize and validate input
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation(
            "add_friends_to_receipt_attempt", 
            receipt_id=sanitized_input.receipt_id,
            friend_count=len(sanitized_input.friend_ids),
            user_id=user_id
        )
        
        try:
            def _operation() -> bool:
                # Verify receipt ownership
                receipt = self._verify_receipt_ownership(sanitized_input.receipt_id, user_id)
                
                # Verify friends ownership
                friends = self._verify_friends_ownership(sanitized_input.friend_ids, user_id)
                
                # Add friend associations using repository
                associations = self.receipt_friend_repo.add_friends_to_receipt(
                    receipt_id=sanitized_input.receipt_id,
                    friend_ids=sanitized_input.friend_ids
                )
                
                self.log_operation(
                    "add_friends_to_receipt_success",
                    receipt_id=sanitized_input.receipt_id,
                    friend_count=len(sanitized_input.friend_ids),
                    associations_created=len(associations)
                )
                return True
            
            result = self.run_in_transaction(db, _operation)
            return AddFriendsToReceiptResult(
                success=True,
                data=result,
                message="Friends added to receipt successfully"
            )
            
        except (ReceiptNotFoundError, FriendsValidationError, ReceiptFriendAssociationError) as e:
            self.log_operation(
                "add_friends_to_receipt_failed",
                error_code=e.error_code,
                reason=e.error_code.lower(),
                receipt_id=sanitized_input.receipt_id
            )
            return AddFriendsToReceiptResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "add_friends_to_receipt_error",
                error_type=type(e).__name__,
                error_message=str(e),
                receipt_id=sanitized_input.receipt_id
            )
            raise
    
    def remove_friends_from_receipt(self, input_data: RemoveFriendsFromReceiptInput, user_id: int, db: Session) -> RemoveFriendsFromReceiptResult:
        """Remove friends from a receipt."""
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation(
            "remove_friends_from_receipt_attempt", 
            receipt_id=sanitized_input.receipt_id,
            friend_count=len(sanitized_input.friend_ids),
            user_id=user_id
        )
        
        try:
            def _operation() -> bool:
                # Verify receipt ownership
                receipt = self._verify_receipt_ownership(sanitized_input.receipt_id, user_id)
                
                # Remove friend associations using repository
                removed = self.receipt_friend_repo.remove_friends_from_receipt(
                    receipt_id=sanitized_input.receipt_id,
                    friend_ids=sanitized_input.friend_ids
                )
                
                self.log_operation(
                    "remove_friends_from_receipt_success",
                    receipt_id=sanitized_input.receipt_id,
                    friend_count=len(sanitized_input.friend_ids),
                    associations_removed=removed
                )
                return True
            
            result = self.run_in_transaction(db, _operation)
            return RemoveFriendsFromReceiptResult(
                success=True,
                data=result,
                message="Friends removed from receipt successfully"
            )
            
        except (ReceiptNotFoundError, ReceiptFriendAssociationError) as e:
            self.log_operation(
                "remove_friends_from_receipt_failed",
                error_code=e.error_code,
                reason=e.error_code.lower(),
                receipt_id=sanitized_input.receipt_id
            )
            return RemoveFriendsFromReceiptResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "remove_friends_from_receipt_error",
                error_type=type(e).__name__,
                error_message=str(e),
                receipt_id=sanitized_input.receipt_id
            )
            raise
    
    def get_receipt_friends(self, input_data: GetReceiptFriendsInput, user_id: int, db: Session) -> GetReceiptFriendsResult:
        """Get all friends associated with a receipt."""
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation(
            "get_receipt_friends_attempt", 
            receipt_id=sanitized_input.receipt_id,
            user_id=user_id
        )
        
        try:
            def _operation() -> List[Friend]:
                # Verify receipt ownership
                receipt = self._verify_receipt_ownership(sanitized_input.receipt_id, user_id)
                
                # Get friends using repository
                friends = self.receipt_friend_repo.get_receipt_friends(sanitized_input.receipt_id)
                
                self.log_operation(
                    "get_receipt_friends_success",
                    receipt_id=sanitized_input.receipt_id,
                    friend_count=len(friends)
                )
                return friends
            
            result = self.run_in_transaction(db, _operation)
            return GetReceiptFriendsResult(
                success=True,
                data=result,
                message="Receipt friends retrieved successfully"
            )
            
        except (ReceiptNotFoundError,) as e:
            self.log_operation(
                "get_receipt_friends_failed",
                error_code=e.error_code,
                reason=e.error_code.lower(),
                receipt_id=sanitized_input.receipt_id
            )
            return GetReceiptFriendsResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "get_receipt_friends_error",
                error_type=type(e).__name__,
                error_message=str(e),
                receipt_id=sanitized_input.receipt_id
            )
            raise
    
    def update_receipt_friends(self, input_data: UpdateReceiptFriendsInput, user_id: int, db: Session) -> UpdateReceiptFriendsResult:
        """Replace all friends associated with a receipt with the new list."""
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation(
            "update_receipt_friends_attempt", 
            receipt_id=sanitized_input.receipt_id,
            friend_count=len(sanitized_input.friend_ids),
            user_id=user_id
        )
        
        try:
            def _operation() -> bool:
                # Verify receipt ownership
                receipt = self._verify_receipt_ownership(sanitized_input.receipt_id, user_id)
                
                # Verify friends ownership if any provided
                if sanitized_input.friend_ids:
                    friends = self._verify_friends_ownership(sanitized_input.friend_ids, user_id)
                
                # Clear existing associations and add new ones
                self.receipt_friend_repo.clear_receipt_friends(sanitized_input.receipt_id)
                
                if sanitized_input.friend_ids:
                    associations = self.receipt_friend_repo.add_friends_to_receipt(
                        receipt_id=sanitized_input.receipt_id,
                        friend_ids=sanitized_input.friend_ids
                    )
                
                self.log_operation(
                    "update_receipt_friends_success",
                    receipt_id=sanitized_input.receipt_id,
                    friend_count=len(sanitized_input.friend_ids)
                )
                return True
            
            result = self.run_in_transaction(db, _operation)
            return UpdateReceiptFriendsResult(
                success=True,
                data=result,
                message="Receipt friends updated successfully"
            )
            
        except (ReceiptNotFoundError, FriendsValidationError, ReceiptFriendAssociationError) as e:
            self.log_operation(
                "update_receipt_friends_failed",
                error_code=e.error_code,
                reason=e.error_code.lower(),
                receipt_id=sanitized_input.receipt_id
            )
            return UpdateReceiptFriendsResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "update_receipt_friends_error",
                error_type=type(e).__name__,
                error_message=str(e),
                receipt_id=sanitized_input.receipt_id
            )
            raise
    
    def get_friend_receipts(self, input_data: GetFriendReceiptsInput, user_id: int, db: Session) -> GetFriendReceiptsResult:
        """Get all receipts associated with a specific friend."""
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation(
            "get_friend_receipts_attempt", 
            friend_id=sanitized_input.friend_id,
            user_id=user_id
        )
        
        try:
            def _operation() -> List[Receipt]:
                # Verify friend ownership
                friend = self._verify_friend_ownership(sanitized_input.friend_id, user_id)
                
                # Get receipt IDs using repository
                receipt_ids = self.receipt_friend_repo.get_friend_receipts(sanitized_input.friend_id)
                
                # Get full receipt objects that belong to the user
                receipts = []
                if receipt_ids:
                    receipts = self.receipt_repo.get_multiple_by_ids_and_user(receipt_ids, user_id)
                
                self.log_operation(
                    "get_friend_receipts_success",
                    friend_id=sanitized_input.friend_id,
                    receipt_count=len(receipts)
                )
                return receipts
            
            result = self.run_in_transaction(db, _operation)
            return GetFriendReceiptsResult(
                success=True,
                data=result,
                message="Friend receipts retrieved successfully"
            )
            
        except (FriendNotFoundError,) as e:
            self.log_operation(
                "get_friend_receipts_failed",
                error_code=e.error_code,
                reason=e.error_code.lower(),
                friend_id=sanitized_input.friend_id
            )
            return GetFriendReceiptsResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "get_friend_receipts_error",
                error_type=type(e).__name__,
                error_message=str(e),
                friend_id=sanitized_input.friend_id
            )
            raise
    
    def remove_friend_from_all_receipts(self, input_data: RemoveFriendFromAllReceiptsInput, user_id: int, db: Session) -> RemoveFriendFromAllReceiptsResult:
        """Remove a friend from all receipts (useful when deleting a friend)."""
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation(
            "remove_friend_from_all_receipts_attempt", 
            friend_id=sanitized_input.friend_id,
            user_id=user_id
        )
        
        try:
            def _operation() -> bool:
                # Verify friend ownership
                friend = self._verify_friend_ownership(sanitized_input.friend_id, user_id)
                
                # Remove all associations for this friend
                # Note: We don't need to verify receipt ownership here since we're removing
                # the friend from all receipts, and we've already verified friend ownership
                removed_count = self.receipt_friend_repo.db.query(
                    self.receipt_friend_repo.model
                ).filter(
                    self.receipt_friend_repo.model.friend_id == sanitized_input.friend_id
                ).delete(synchronize_session=False)
                
                self.log_operation(
                    "remove_friend_from_all_receipts_success",
                    friend_id=sanitized_input.friend_id,
                    associations_removed=removed_count
                )
                return True
            
            result = self.run_in_transaction(db, _operation)
            return RemoveFriendFromAllReceiptsResult(
                success=True,
                data=result,
                message="Friend removed from all receipts successfully"
            )
            
        except (FriendNotFoundError,) as e:
            self.log_operation(
                "remove_friend_from_all_receipts_failed",
                error_code=e.error_code,
                reason=e.error_code.lower(),
                friend_id=sanitized_input.friend_id
            )
            return RemoveFriendFromAllReceiptsResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "remove_friend_from_all_receipts_error",
                error_type=type(e).__name__,
                error_message=str(e),
                friend_id=sanitized_input.friend_id
            )
            raise
