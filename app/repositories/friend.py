"""Friend repository for friend-related database operations."""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository
from app.db.models.friend import Friend


class FriendRepository(BaseRepository[Friend]):
    """Repository for Friend entity operations."""
    
    def __init__(self, db: Session, correlation_id: Optional[str] = None):
        super().__init__(db, Friend, correlation_id)
    
    def get_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Friend]:
        """Get friends for a specific user with pagination.
        
        Args:
            user_id: User ID to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Friend instances for the user
        """
        self._log_operation("get_by_user_start", user_id=user_id, skip=skip, limit=limit)
        
        # Direct query for debugging
        direct_query = self.db.query(self.model).filter(
            self.model.user_id == user_id,
            self.model.is_deleted == False
        )
        
        direct_count = direct_query.count()
        self._log_operation("get_by_user_direct_query_count", user_id=user_id, count=direct_count)
        
        # Also check with is_deleted check disabled temporarily for debugging
        all_friends_count = self.db.query(self.model).filter(
            self.model.user_id == user_id
        ).count()
        self._log_operation("get_by_user_all_friends_count", user_id=user_id, count=all_friends_count)
        
        result = self.get_multi(
            skip=skip,
            limit=limit,
            filters={"user_id": user_id},
            order_by="name"
        )
        
        self._log_operation(
            "get_by_user_result",
            user_id=user_id,
            result_count=len(result),
            friend_ids=[f.id for f in result] if result else []
        )
        
        return result
    
    def get_by_id_and_user(self, friend_id: int, user_id: int) -> Optional[Friend]:
        """Get friend by ID for a specific user.
        
        Args:
            friend_id: Friend ID
            user_id: User ID to verify ownership
            
        Returns:
            Friend instance or None if not found or not owned by user
        """
        result = self.db.query(self.model).filter(
            self.model.id == friend_id,
            self.model.user_id == user_id,
            self.model.is_deleted == False
        ).first()
        
        self._log_operation("get_by_id_and_user", friend_id=friend_id, user_id=user_id, found=result is not None)
        return result
    
    def get_multiple_by_ids_and_user(self, friend_ids: List[int], user_id: int) -> List[Friend]:
        """Get multiple friends by IDs for a specific user.
        
        Args:
            friend_ids: List of Friend IDs
            user_id: User ID to verify ownership
            
        Returns:
            List of Friend instances owned by the user
        """
        results = self.db.query(self.model).filter(
            self.model.id.in_(friend_ids),
            self.model.user_id == user_id,
            self.model.is_deleted == False
        ).all()
        
        self._log_operation("get_multiple_by_ids_and_user", friend_ids=friend_ids, user_id=user_id, found_count=len(results))
        return results
    
    def get_by_ids_and_user(self, friend_ids: List[int], user_id: int) -> List[Friend]:
        """Get multiple friends by IDs for a specific user.
        
        Args:
            friend_ids: List of Friend IDs
            user_id: User ID to verify ownership
            
        Returns:
            List of Friend instances owned by the user
        """
        if not friend_ids:
            return []
        
        results = self.db.query(self.model).filter(
            self.model.id.in_(friend_ids),
            self.model.user_id == user_id,
            self.model.is_deleted == False
        ).all()
        
        self._log_operation("get_by_ids_and_user", friend_ids=friend_ids, user_id=user_id, count=len(results))
        return results
    
    def create_friend(self, name: str, user_id: int, photo_url: Optional[str] = None) -> Friend:
        """Create a new friend for a user.
        
        Args:
            name: Friend's name
            user_id: Owner user ID
            photo_url: Optional photo URL
            
        Returns:
            Created Friend instance
        """
        create_data = {
            "name": name,
            "user_id": user_id,
            "photo_url": photo_url
        }
        
        return self.create(create_data)
    
    def search_by_name(self, user_id: int, name: str, skip: int = 0, limit: int = 100) -> List[Friend]:
        """Search friends by name for a user.
        
        Args:
            user_id: User ID to filter by
            name: Name to search for (case-insensitive)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching Friend instances
        """
        results = self.db.query(self.model).filter(
            self.model.user_id == user_id,
            self.model.name.ilike(f"%{name}%"),
            self.model.is_deleted == False
        ).order_by(self.model.name).offset(skip).limit(limit).all()
        
        self._log_operation("search_by_name", user_id=user_id, name=name, count=len(results))
        return results
    
    def update_friend_name(self, friend_id: int, name: str) -> Optional[Friend]:
        """Update friend's name.
        
        Args:
            friend_id: Friend ID
            name: New name
            
        Returns:
            Updated Friend instance or None if not found
        """
        return self.update(friend_id, {"name": name})
    
    def update_friend_photo(self, friend_id: int, photo_url: str) -> Optional[Friend]:
        """Update friend's photo URL.
        
        Args:
            friend_id: Friend ID
            photo_url: New photo URL
            
        Returns:
            Updated Friend instance or None if not found
        """
        return self.update(friend_id, {"photo_url": photo_url})
    
    def get_user_friends_count(self, user_id: int) -> int:
        """Get total number of friends for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of friends for the user
        """
        return self.count(filters={"user_id": user_id})
