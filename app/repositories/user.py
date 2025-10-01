"""User repository for user-related database operations."""

from typing import Optional
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository
from app.db.models.user import User
from app.schemas.user import UserCreate


class UserRepository(BaseRepository[User]):
    """Repository for User entity operations."""
    
    def __init__(self, db: Session, correlation_id: Optional[str] = None):
        super().__init__(db, User, correlation_id)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address.
        
        Args:
            email: User's email address
            
        Returns:
            User instance or None if not found
        """
        result = self.db.query(self.model).filter(
            self.model.email == email,
            self.model.is_deleted == False
        ).first()
        
        self._log_operation("get_by_email", email=email, found=result is not None)
        return result
    
    def email_exists(self, email: str, exclude_id: Optional[int] = None) -> bool:
        """Check if email is already registered.
        
        Args:
            email: Email address to check
            exclude_id: Optional user ID to exclude from check (for updates)
            
        Returns:
            True if email exists, False otherwise
        """
        query = self.db.query(self.model.id).filter(
            self.model.email == email,
            self.model.is_deleted == False
        )
        
        if exclude_id:
            query = query.filter(self.model.id != exclude_id)
        
        result = query.first() is not None
        self._log_operation("email_exists", email=email, exists=result, exclude_id=exclude_id)
        return result
    
    def get_active_users(self, skip: int = 0, limit: int = 100):
        """Get active users with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of active User instances
        """
        return self.get_multi(
            skip=skip, 
            limit=limit, 
            filters={"is_active": True}
        )
    
    def create_user(self, user_in: UserCreate, hashed_password: str) -> User:
        user_data = user_in.model_dump(exclude={"password"})
        user_data["hashed_password"] = hashed_password
        return self.create(user_data)

    
    def deactivate_user(self, user_id: int) -> Optional[User]:
        """Deactivate a user account.
        
        Args:
            user_id: User ID to deactivate
            
        Returns:
            Updated User instance or None if not found
        """
        return self.update(user_id, {"is_active": False})
    
    def activate_user(self, user_id: int) -> Optional[User]:
        """Activate a user account.
        
        Args:
            user_id: User ID to activate
            
        Returns:
            Updated User instance or None if not found
        """
        return self.update(user_id, {"is_active": True})
