"""Friend service providing comprehensive friend management operations.

This service provides friend management capabilities with comprehensive error handling,
input validation, and structured logging. It follows the standard service
architecture pattern for friend operations.
"""

from typing import Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile

from app.services.base import BaseService
from app.services.exceptions import (
    FriendError,
    FriendNotFoundError,
    FriendCreationError,
    FriendUpdateError,
    FriendDeletionError,
    PhotoUploadError,
    ValidationError
)
from app.repositories.friend import FriendRepository
from app.db.models.friend import Friend
from app.schemas.friend import (
    CreateFriendInput,
    UpdateFriendInput,
    FriendRead,
    CreateFriendResult,
    UpdateFriendResult,
    DeleteFriendResult,
    GetFriendsResult
)
from app.services.file_services import upload_file


class FriendService(BaseService):
    """Service class for handling friend operations.
    
    This service demonstrates the standard architecture pattern:
    - Dependency injection through constructor or _set_repositories
    - Comprehensive error handling with domain exceptions
    - Input validation using Pydantic schemas
    - Structured logging with correlation IDs
    - Transaction management for data operations
    - Type-safe result objects instead of Optional returns
    
    Security Features:
    - Input sanitization and validation
    - Photo upload validation and security
    - Structured audit logging
    - Clear separation of friend concerns
    """
    
    def __init__(self, correlation_id: Optional[str] = None, **repositories):
        """Initialize friend service.
        
        Args:
            correlation_id: Optional request correlation ID for logging
            **repositories: Repository instances (friend_repo, etc.)
        """
        super().__init__(correlation_id)
        if repositories:
            self._set_repositories(**repositories)
        
        # Ensure required repositories are available
        if not hasattr(self, 'friend_repo'):
            raise ValidationError(
                field="friend_repo",
                message="FriendRepository is required for FriendService",
                correlation_id=correlation_id
            )
    
    def _sanitize_input(self, input_data):
        """Sanitize input data for security."""
        # Input sanitization is handled by Pydantic validators in schemas
        return input_data
    
    def create_friend(self, name: str, photo: UploadFile, user_id: int, db: Session) -> CreateFriendResult:
        """Create a new friend with photo upload.
        
        This method demonstrates the standard service pattern:
        - Input validation through parameters
        - Domain exception handling
        - Transaction management
        - Structured result objects
        - Security-focused logging
        
        Args:
            name: Friend's name (will be validated)
            photo: Photo file to upload
            user_id: Owner user ID
            db: Database session for transaction management
            
        Returns:
            CreateFriendResult with success status and data or error info
            
        Raises:
            FriendCreationError: If friend creation fails
            PhotoUploadError: If photo upload fails
            ValidationError: If input validation fails
        """
        # Validate input using schema
        try:
            input_data = CreateFriendInput(name=name)
            sanitized_input = self._sanitize_input(input_data)
        except Exception as e:
            raise ValidationError(
                field="name",
                message=str(e),
                correlation_id=self.correlation_id
            )
        
        self.log_operation(
            "create_friend_attempt", 
            user_id=user_id,
            name_length=len(sanitized_input.name)
        )
        
        try:
            def _create_friend() -> Friend:
                # Upload photo to MinIO and get the URL
                try:
                    photo_url = upload_file(photo, "friends")
                except Exception as e:
                    raise PhotoUploadError(
                        reason=str(e),
                        correlation_id=self.correlation_id
                    )
                
                # Create friend using repository
                try:
                    friend = self.friend_repo.create_friend(
                        name=sanitized_input.name,
                        user_id=user_id,
                        photo_url=photo_url
                    )
                except Exception as e:
                    raise FriendCreationError(
                        reason=str(e),
                        correlation_id=self.correlation_id
                    )
                
                self.log_operation(
                    "create_friend_success", 
                    friend_id=friend.id,
                    user_id=user_id
                )
                return friend
            
            result = self.run_in_transaction(db, _create_friend)
            friend_data = FriendRead.from_orm(result)
            return CreateFriendResult(
                success=True,
                data=friend_data,
                message="Friend created successfully"
            )
            
        except (FriendError, PhotoUploadError) as e:
            self.log_operation(
                "create_friend_failed",
                error_code=e.error_code,
                reason=e.error_code.lower(),
                user_id=user_id
            )
            return CreateFriendResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "create_friend_error",
                error_type=type(e).__name__,
                error_message=str(e),
                user_id=user_id
            )
            raise
    
    def get_friends(self, user_id: int, db: Session) -> GetFriendsResult:
        """Get all friends for a user.
        
        Args:
            user_id: User ID to get friends for
            db: Database session
            
        Returns:
            GetFriendsResult with friends list or error info
        """
        self.log_operation("get_friends_attempt", user_id=user_id)
        
        try:
            def _get_friends() -> list[Friend]:
                from app.db.models.friend import Friend
                
                # Update friends with null names to have default name
                friends_with_null_names = db.query(Friend).filter(
                    Friend.user_id == user_id,
                    Friend.name.is_(None),
                    Friend.is_deleted == False
                ).all()
                
                for friend in friends_with_null_names:
                    friend.name = "Friend"
                
                if friends_with_null_names:
                    db.flush()  # Ensure the updates are committed
                
                # Get all friends for user
                friends = self.friend_repo.get_by_user(user_id=user_id)
                
                self.log_operation(
                    "get_friends_success", 
                    user_id=user_id,
                    count=len(friends)
                )
                return friends
            
            result = self.run_in_transaction(db, _get_friends)
            friends_data = [FriendRead.from_orm(friend) for friend in result]
            return GetFriendsResult(
                success=True,
                data=friends_data,
                message="Friends retrieved successfully"
            )
            
        except Exception as e:
            self.log_operation(
                "get_friends_error",
                error_type=type(e).__name__,
                error_message=str(e),
                user_id=user_id
            )
            raise
    
    def delete_friend(self, friend_id: int, user_id: int, db: Session) -> DeleteFriendResult:
        """Soft delete a friend.
        
        Args:
            friend_id: Friend ID to delete
            user_id: Owner user ID
            db: Database session
            
        Returns:
            DeleteFriendResult with success status or error info
        """
        self.log_operation(
            "delete_friend_attempt", 
            friend_id=friend_id,
            user_id=user_id
        )
        
        try:
            def _delete_friend() -> dict:
                # Find friend
                friend = self.friend_repo.get_by_id_and_user(friend_id, user_id)
                if not friend:
                    raise FriendNotFoundError(
                        friend_id=friend_id,
                        user_id=user_id,
                        correlation_id=self.correlation_id
                    )
                
                # Soft delete
                try:
                    friend.is_deleted = True
                    db.add(friend)
                except Exception as e:
                    raise FriendDeletionError(
                        friend_id=friend_id,
                        reason=str(e),
                        correlation_id=self.correlation_id
                    )
                
                self.log_operation(
                    "delete_friend_success", 
                    friend_id=friend_id,
                    user_id=user_id
                )
                return {"deleted": True, "friend_id": friend_id}
            
            result = self.run_in_transaction(db, _delete_friend)
            return DeleteFriendResult(
                success=True,
                data=result,
                message="Friend deleted successfully"
            )
            
        except FriendError as e:
            self.log_operation(
                "delete_friend_failed",
                error_code=e.error_code,
                reason=e.error_code.lower(),
                friend_id=friend_id,
                user_id=user_id
            )
            return DeleteFriendResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "delete_friend_error",
                error_type=type(e).__name__,
                error_message=str(e),
                friend_id=friend_id,
                user_id=user_id
            )
            raise
    
    def update_friend(self, friend_id: int, name: str, photo: UploadFile, user_id: int, db: Session) -> UpdateFriendResult:
        """Update a friend's information with photo upload.
        
        Args:
            friend_id: Friend ID to update
            name: New friend name
            photo: New photo file
            user_id: Owner user ID
            db: Database session
            
        Returns:
            UpdateFriendResult with updated friend data or error info
        """
        # Validate input using schema
        try:
            input_data = UpdateFriendInput(name=name)
            sanitized_input = self._sanitize_input(input_data)
        except Exception as e:
            raise ValidationError(
                field="name",
                message=str(e),
                correlation_id=self.correlation_id
            )
        
        self.log_operation(
            "update_friend_attempt", 
            friend_id=friend_id,
            user_id=user_id
        )
        
        try:
            def _update_friend() -> Friend:
                # Find friend
                friend = self.friend_repo.get_by_id_and_user(friend_id, user_id)
                if not friend:
                    raise FriendNotFoundError(
                        friend_id=friend_id,
                        user_id=user_id,
                        correlation_id=self.correlation_id
                    )
                
                # Upload new photo
                try:
                    photo_url = upload_file(photo, "friends")
                except Exception as e:
                    raise PhotoUploadError(
                        reason=str(e),
                        correlation_id=self.correlation_id
                    )
                
                # Update friend
                try:
                    friend.name = sanitized_input.name
                    friend.photo_url = photo_url
                    db.add(friend)
                except Exception as e:
                    raise FriendUpdateError(
                        friend_id=friend_id,
                        reason=str(e),
                        correlation_id=self.correlation_id
                    )
                
                self.log_operation(
                    "update_friend_success", 
                    friend_id=friend_id,
                    user_id=user_id
                )
                return friend
            
            result = self.run_in_transaction(db, _update_friend)
            friend_data = FriendRead.from_orm(result)
            return UpdateFriendResult(
                success=True,
                data=friend_data,
                message="Friend updated successfully"
            )
            
        except (FriendError, PhotoUploadError) as e:
            self.log_operation(
                "update_friend_failed",
                error_code=e.error_code,
                reason=e.error_code.lower(),
                friend_id=friend_id,
                user_id=user_id
            )
            return UpdateFriendResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "update_friend_error",
                error_type=type(e).__name__,
                error_message=str(e),
                friend_id=friend_id,
                user_id=user_id
            )
            raise
