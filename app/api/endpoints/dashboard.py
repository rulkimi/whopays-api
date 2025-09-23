from fastapi import Depends, HTTPException
from app.api.router import create_router
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_friend_service, get_receipt_service
from app.services.friend_services import FriendService
from app.services.receipt_services import ReceiptService
from app.schemas.friend import FriendRead
from app.schemas.receipt import GetReceiptsInput

router = create_router(name="dashboard")

@router.get("")
def get_dashboard(
	db: Session = Depends(get_db),
	current_user=Depends(get_current_user),
	friend_service: FriendService = Depends(get_friend_service),
	receipt_service: ReceiptService = Depends(get_receipt_service)
):
	# Get friends using the new service architecture
	friends_result = friend_service.get_friends(current_user.id, db)
	if not friends_result.success:
		raise HTTPException(status_code=500, detail=friends_result.message)
	
	# Get only the latest 5 receipts using the new service architecture
	receipts_input = GetReceiptsInput(skip=0, limit=5)
	receipts_result = receipt_service.get_user_receipts(receipts_input, current_user.id, db)
	if not receipts_result.success:
		raise HTTPException(status_code=500, detail=receipts_result.message)

	return {
		"friends": friends_result.data,
		"receipts": receipts_result.data
	}
