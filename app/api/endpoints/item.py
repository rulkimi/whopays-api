from fastapi import Depends, HTTPException, status
from app.api.router import create_router
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.api.dependencies.database import get_db
from app.api.dependencies.auth import get_current_user
from app.services import item_friend_services

router = create_router(name="item")

class AddFriendsToItemRequest(BaseModel):
	item_id: int
	friend_ids: List[int]

class AddFriendsToMultipleItemsRequest(BaseModel):
	items: List[AddFriendsToItemRequest]

class AddFriendsResponse(BaseModel):
	success: bool
	item_id: Optional[int] = None
	error: Optional[str] = None

@router.post("/add-friends", response_model=AddFriendsResponse)
def add_friends_to_item(
	req: AddFriendsToItemRequest,
	db: Session = Depends(get_db),
	current_user=Depends(get_current_user)
):
	"""
	Add friends to a single item. If friend_ids is empty, all friends will be removed from the item.
	"""
	action = "clear friends from" if not req.friend_ids else "add friends"
	print(f"User {current_user.id} is attempting to {action} item {req.item_id}: {req.friend_ids}")
	
	success = item_friend_services.add_friends_to_item(
		db=db,
		item_id=req.item_id,
		friend_ids=req.friend_ids,
		user_id=current_user.id
	)
	if not success:
		print(f"Failed to {action} item {req.item_id} for user {current_user.id}")
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Failed to update item friends. Check item and friend ownership."
		)
	
	success_message = f"Successfully cleared friends from item {req.item_id}" if not req.friend_ids else f"Successfully added friends {req.friend_ids} to item {req.item_id}"
	print(f"{success_message} for user {current_user.id}")
	return AddFriendsResponse(success=True, item_id=req.item_id)

@router.post("/add-friends-multiple", response_model=List[AddFriendsResponse])
def add_friends_to_multiple_items(
	req: AddFriendsToMultipleItemsRequest,
	db: Session = Depends(get_db),
	current_user=Depends(get_current_user)
):
	"""
	Add friends to multiple items in one request.
	"""
	responses = []
	for item_req in req.items:
		try:
			success = item_friend_services.add_friends_to_item(
				db=db,
				item_id=item_req.item_id,
				friend_ids=item_req.friend_ids,
				user_id=current_user.id
			)
			if success:
				responses.append(AddFriendsResponse(success=True, item_id=item_req.item_id))
			else:
				responses.append(AddFriendsResponse(success=False, item_id=item_req.item_id, error="Failed to add friends to item. Check item and friend ownership."))
		except Exception as e:
			responses.append(AddFriendsResponse(success=False, item_id=item_req.item_id, error=str(e)))
	return responses
