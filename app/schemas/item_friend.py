"""Item-Friend association schemas for input validation and result objects."""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from app.schemas.mixin import TimestampModel


class FriendBasic(BaseModel):
    """Basic friend information for item associations."""
    id: int
    name: str
    photo_url: Optional[str] = None
    user_id: int


class AddFriendsToItemInput(BaseModel):
    """Input for adding friends to an item."""
    item_id: int = Field(..., gt=0, description="Item ID to associate friends with")
    friend_ids: List[int] = Field(..., description="List of friend IDs to associate (empty list clears all friends)")
    
    @validator('friend_ids')
    def validate_friend_ids(cls, v):
        """Validate friend IDs."""
        # Allow empty list to clear all friends
        if not isinstance(v, list):
            raise ValueError("friend_ids must be a list")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_ids = []
        for friend_id in v:
            if friend_id not in seen:
                if friend_id <= 0:
                    raise ValueError(f"Friend ID must be positive: {friend_id}")
                seen.add(friend_id)
                unique_ids.append(friend_id)
        
        return unique_ids


class RemoveFriendsFromItemInput(BaseModel):
    """Input for removing friends from an item."""
    item_id: int = Field(..., gt=0, description="Item ID to remove friends from")
    friend_ids: List[int] = Field(..., min_items=1, description="List of friend IDs to remove")
    
    @validator('friend_ids')
    def validate_friend_ids(cls, v):
        """Validate friend IDs."""
        if not v:
            raise ValueError("At least one friend ID is required")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_ids = []
        for friend_id in v:
            if friend_id not in seen:
                if friend_id <= 0:
                    raise ValueError(f"Friend ID must be positive: {friend_id}")
                seen.add(friend_id)
                unique_ids.append(friend_id)
        
        return unique_ids


class UpdateItemFriendsInput(BaseModel):
    """Input for replacing all friends associated with an item."""
    item_id: int = Field(..., gt=0, description="Item ID to update friends for")
    friend_ids: List[int] = Field(..., description="List of friend IDs to associate (replaces all existing)")
    
    @validator('friend_ids')
    def validate_friend_ids(cls, v):
        """Validate friend IDs."""
        # Allow empty list to clear all friends
        if not isinstance(v, list):
            raise ValueError("friend_ids must be a list")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_ids = []
        for friend_id in v:
            if friend_id not in seen:
                if friend_id <= 0:
                    raise ValueError(f"Friend ID must be positive: {friend_id}")
                seen.add(friend_id)
                unique_ids.append(friend_id)
        
        return unique_ids


class GetItemFriendsInput(BaseModel):
    """Input for getting friends associated with an item."""
    item_id: int = Field(..., gt=0, description="Item ID to get friends for")


class AddFriendsToItemResult(BaseModel):
    """Result of adding friends to an item operation."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "item_id": 123,
                    "added_friend_ids": [1, 2, 3],
                    "friends_count": 3
                },
                "message": "Friends added to item successfully"
            }
        }


class RemoveFriendsFromItemResult(BaseModel):
    """Result of removing friends from an item operation."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "item_id": 123,
                    "removed_friend_ids": [1, 2],
                    "friends_count": 1
                },
                "message": "Friends removed from item successfully"
            }
        }


class UpdateItemFriendsResult(BaseModel):
    """Result of updating all friends for an item operation."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "item_id": 123,
                    "friend_ids": [1, 3, 4],
                    "friends_count": 3
                },
                "message": "Item friends updated successfully"
            }
        }


class GetItemFriendsResult(BaseModel):
    """Result of getting friends associated with an item operation."""
    success: bool
    data: Optional[List[FriendBasic]] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [
                    {
                        "id": 1,
                        "name": "John Doe",
                        "photo_url": "https://example.com/photo.jpg",
                        "user_id": 100
                    },
                    {
                        "id": 2,
                        "name": "Jane Smith",
                        "photo_url": None,
                        "user_id": 100
                    }
                ],
                "message": "Item friends retrieved successfully"
            }
        }
