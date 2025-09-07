from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.api.dependencies.auth import get_current_user
from app.services import friend_services
from app.services import receipt_services
from app.schemas.friend import FriendRead

router = APIRouter()

@router.get("")
def get_dashboard(
	db: Session = Depends(get_db),
	current_user=Depends(get_current_user)
):
	friends = friend_services.get_friends(db, current_user.id)
	# Get only the latest 5 receipts
	receipts = receipt_services.get_user_receipts(db, current_user.id, skip=0, limit=5)

	return {
		"friends": friends,
		"receipts": receipts
	}
