"""Receipt service providing comprehensive receipt management operations.

This service provides receipt management capabilities with comprehensive error handling,
input validation, and structured logging. It follows the standard service
architecture pattern for receipt operations including:
- Receipt image analysis using AI
- Receipt creation with items and variations
- Receipt retrieval and listing
- Receipt deletion with cascading
- Receipt split calculations
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from decimal import Decimal, ROUND_HALF_UP

from app.services.base import BaseService
from app.services.exceptions import (
    ReceiptError,
    ReceiptNotFoundError,
    ReceiptAnalysisError,
    ReceiptCreationError,
    ReceiptDeletionError,
    ReceiptSplitCalculationError,
    ValidationError
)
from app.repositories.receipt import ReceiptRepository
from app.repositories.item import ItemRepository
from app.repositories.friend import FriendRepository
from app.repositories.receipt_friend import ReceiptFriendRepository
from app.repositories.item_friend import ItemFriendRepository
from app.db.models.receipt import Receipt
from app.db.models.item import Item
from app.db.models.variation import Variation
from app.db.models.item_friend import ItemFriend
from app.db.models.friend import Friend
from app.schemas.receipt import (
    ReceiptBase,
    ReceiptRead,
    AnalyzeReceiptInput,
    CreateReceiptInput,
    GetReceiptInput,
    GetReceiptsInput,
    DeleteReceiptInput,
    CalculateSplitsInput,
    AnalyzeReceiptResult,
    CreateReceiptResult,
    GetReceiptResult,
    GetReceiptsResult,
    DeleteReceiptResult,
    CalculateSplitsResult
)
from app.gemini.prompts import create_analysis_prompt
from app.gemini.services import get_ai_response


def _round2(x: Decimal) -> Decimal:
    """Round decimal to 2 decimal places using ROUND_HALF_UP."""
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ReceiptService(BaseService):
    """Service class for handling receipt operations.
    
    This service demonstrates the standard architecture pattern:
    - Dependency injection through constructor
    - Comprehensive error handling with domain exceptions
    - Input validation using Pydantic schemas
    - Structured logging with correlation IDs
    - Transaction management for data operations
    - Type-safe result objects instead of Optional returns
    
    Security Features:
    - Input sanitization and validation
    - User ownership verification for all operations
    - Structured audit logging
    - Clear separation of receipt concerns
    """
    
    def __init__(self, correlation_id: Optional[str] = None, **repositories):
        """Initialize receipt service.
        
        Args:
            correlation_id: Optional request correlation ID for logging
            **repositories: Repository instances (receipt_repo, item_repo, etc.)
        """
        super().__init__(correlation_id)
        if repositories:
            self._set_repositories(**repositories)
        
        # Ensure required repositories are available
        required_repos = ['receipt_repo', 'item_repo', 'friend_repo', 'receipt_friend_repo', 'item_friend_repo']
        for repo_name in required_repos:
            if not hasattr(self, repo_name):
                raise ValidationError(
                    field=repo_name,
                    message=f"{repo_name} is required for ReceiptService",
                    correlation_id=correlation_id
                )

    def _sanitize_input(self, input_data: Any) -> Any:
        """Sanitize input data for security."""
        # For now, return as-is since Pydantic handles validation
        # Can be extended for additional sanitization if needed
        return input_data

    def analyze_receipt(self, input_data: AnalyzeReceiptInput, db: Session) -> AnalyzeReceiptResult:
        """Analyze receipt image and return AI response as ReceiptBase model."""
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation("analyze_receipt_attempt")
        
        try:
            def _operation() -> ReceiptBase:
                try:
                    prompt = create_analysis_prompt()
                    ai_response_dict = get_ai_response(
                        contents=[prompt, sanitized_input.image_data], 
                        response_schema=ReceiptBase,
                        content_type=sanitized_input.content_type
                    )
                    
                    # Convert the dictionary response to ReceiptBase model
                    # Ensure subtotal is present: use from AI if available, otherwise calculate it
                    if "subtotal" not in ai_response_dict or ai_response_dict.get("subtotal") is None:
                        # Calculate subtotal as fallback: total_amount - tax - service_charge
                        total = float(ai_response_dict.get("total_amount", 0))
                        tax = float(ai_response_dict.get("tax", 0))
                        service_charge = float(ai_response_dict.get("service_charge", 0))
                        ai_response_dict["subtotal"] = total - tax - service_charge
                    
                    result = ReceiptBase(**ai_response_dict)
                    
                    self.log_operation(
                        "analyze_receipt_success",
                        restaurant_name=result.restaurant_name,
                        items_count=len(result.items),
                        subtotal=result.subtotal
                    )
                    return result
                    
                except Exception as e:
                    raise ReceiptAnalysisError(
                        reason=str(e),
                        correlation_id=self.correlation_id
                    )
            
            result = _operation()  # No transaction needed for analysis
            return AnalyzeReceiptResult(
                success=True,
                data=result,
                message="Receipt analysis completed successfully"
            )
            
        except ReceiptAnalysisError as e:
            self.log_operation(
                "analyze_receipt_failed",
                error_code=e.error_code,
                reason=e.error_code.lower()
            )
            return AnalyzeReceiptResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "analyze_receipt_error",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise

    def update_receipt_with_items(self, receipt_id: int, input_data: CreateReceiptInput, user_id: int, db: Session) -> CreateReceiptResult:
        """Update receipt with items and friend associations."""
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation("update_receipt_with_items_attempt", receipt_id=receipt_id, user_id=user_id)
        
        try:
            def _operation() -> Dict[str, Any]:
                # Verify receipt exists and is owned by user
                existing_receipt = self.receipt_repo.get_by_id_and_user(receipt_id, user_id)
                if not existing_receipt:
                    raise ReceiptNotFoundError(
                        receipt_id=receipt_id,
                        user_id=user_id,
                        correlation_id=self.correlation_id
                    )
                
                # Ensure subtotal is present in receipt_data
                receipt_data = sanitized_input.receipt_data
                if not hasattr(receipt_data, 'subtotal') or receipt_data.subtotal is None:
                    # Calculate subtotal as fallback: total_amount - tax - service_charge
                    receipt_data.subtotal = receipt_data.total_amount - receipt_data.tax - receipt_data.service_charge
                
                # Delete existing items for this receipt
                existing_items = self.item_repo.get_multi(filters={"receipt_id": receipt_id})
                for item in existing_items:
                    # Delete item variations first
                    if hasattr(item, 'variations'):
                        for variation in item.variations:
                            if hasattr(variation, 'is_deleted'):
                                variation.is_deleted = True
                    # Delete item
                    if hasattr(item, 'is_deleted'):
                        item.is_deleted = True
                
                # Update the receipt
                receipt = self.receipt_repo.update_receipt(
                    receipt_id=receipt_id,
                    receipt_data=receipt_data,
                    receipt_url=sanitized_input.receipt_url,
                    status="ready"
                )
                
                if not receipt:
                    raise ReceiptNotFoundError(
                        receipt_id=receipt_id,
                        user_id=user_id,
                        correlation_id=self.correlation_id
                    )
                
                # Create new items with variations
                created_items = []
                for item_data in sanitized_input.receipt_data.items:
                    item = self.item_repo.create_item_with_variations(item_data, receipt.id)
                    created_items.append(item)
                
                # Clear existing receipt-friend associations and create new ones
                if sanitized_input.friend_ids:
                    # Verify friends ownership
                    valid_friends = self._verify_friends_ownership(sanitized_input.friend_ids, user_id, db)
                    
                    # Remove existing receipt-friend associations
                    existing_receipt_friends = self.receipt_friend_repo.get_receipt_friends(receipt_id)
                    for rf in existing_receipt_friends:
                        if hasattr(rf, 'is_deleted'):
                            rf.is_deleted = True
                    
                    # Add friends to receipt
                    self.receipt_friend_repo.add_friends_to_receipt(
                        receipt_id=receipt.id,
                        friend_ids=[f.id for f in valid_friends]
                    )
                
                self.log_operation(
                    "update_receipt_with_items_success",
                    receipt_id=receipt.id,
                    items_count=len(created_items),
                    friends_count=len(sanitized_input.friend_ids) if sanitized_input.friend_ids else 0
                )
                
                return {
                    "receipt_id": receipt.id,
                    "restaurant_name": receipt.restaurant_name,
                    "total_amount": receipt.total_amount,
                    "items_count": len(created_items),
                    "friends_count": len(sanitized_input.friend_ids) if sanitized_input.friend_ids else 0
                }
            
            result = self.run_in_transaction(db, _operation)
            return CreateReceiptResult(
                success=True,
                data=result,
                message="Receipt updated successfully with items"
            )
            
        except (ReceiptNotFoundError, ReceiptCreationError) as e:
            self.log_operation(
                "update_receipt_with_items_failed",
                error_code=e.error_code,
                reason=e.error_code.lower()
            )
            return CreateReceiptResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "update_receipt_with_items_error",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise

    def create_receipt_with_items(self, input_data: CreateReceiptInput, user_id: int, db: Session) -> CreateReceiptResult:
        """Create receipt with items and friend associations."""
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation("create_receipt_with_items_attempt", user_id=user_id)
        
        try:
            def _operation() -> Dict[str, Any]:
                # Ensure subtotal is present in receipt_data
                receipt_data = sanitized_input.receipt_data
                if not hasattr(receipt_data, 'subtotal') or receipt_data.subtotal is None:
                    # Calculate subtotal as fallback: total_amount - tax - service_charge
                    receipt_data.subtotal = receipt_data.total_amount - receipt_data.tax - receipt_data.service_charge
                
                # Create the receipt first
                receipt = self.receipt_repo.create_receipt(
                    receipt_data=receipt_data,
                    user_id=user_id,
                    receipt_url=sanitized_input.receipt_url
                )
                
                # Create items with variations
                created_items = []
                for item_data in sanitized_input.receipt_data.items:
                    item = self.item_repo.create_item_with_variations(item_data, receipt.id)
                    created_items.append(item)
                
                # Associate friends with receipt if provided
                if sanitized_input.friend_ids:
                    # Verify friends ownership
                    valid_friends = self._verify_friends_ownership(sanitized_input.friend_ids, user_id, db)
                    
                    # Add friends to receipt
                    self.receipt_friend_repo.add_friends_to_receipt(
                        receipt_id=receipt.id,
                        friend_ids=[f.id for f in valid_friends]
                    )
                
                self.log_operation(
                    "create_receipt_with_items_success",
                    receipt_id=receipt.id,
                    items_count=len(created_items),
                    friends_count=len(sanitized_input.friend_ids) if sanitized_input.friend_ids else 0
                )
                
                return {
                    "receipt_id": receipt.id,
                    "restaurant_name": receipt.restaurant_name,
                    "total_amount": receipt.total_amount,
                    "items_count": len(created_items),
                    "friends_count": len(sanitized_input.friend_ids) if sanitized_input.friend_ids else 0
                }
            
            result = self.run_in_transaction(db, _operation)
            return CreateReceiptResult(
                success=True,
                data=result,
                message="Receipt created successfully with items"
            )
            
        except ReceiptCreationError as e:
            self.log_operation(
                "create_receipt_with_items_failed",
                error_code=e.error_code,
                reason=e.error_code.lower()
            )
            return CreateReceiptResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "create_receipt_with_items_error",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise

    def get_receipt_by_id(self, input_data: GetReceiptInput, user_id: int, db: Session) -> GetReceiptResult:
        """Get a specific receipt by ID."""
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation("get_receipt_by_id_attempt", receipt_id=sanitized_input.receipt_id, user_id=user_id)
        
        try:
            receipt = self.receipt_repo.get_by_id_and_user(sanitized_input.receipt_id, user_id)
            
            if not receipt:
                raise ReceiptNotFoundError(
                    receipt_id=sanitized_input.receipt_id,
                    user_id=user_id,
                    correlation_id=self.correlation_id
                )
            
            # Convert to ReceiptRead schema
            receipt_data = self._convert_receipt_to_schema(receipt)
            
            self.log_operation(
                "get_receipt_by_id_success",
                receipt_id=sanitized_input.receipt_id,
                restaurant_name=receipt.restaurant_name
            )
            
            return GetReceiptResult(
                success=True,
                data=receipt_data,
                message="Receipt retrieved successfully"
            )
            
        except ReceiptNotFoundError as e:
            self.log_operation(
                "get_receipt_by_id_failed",
                error_code=e.error_code,
                receipt_id=sanitized_input.receipt_id
            )
            return GetReceiptResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "get_receipt_by_id_error",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise

    def _convert_receipt_to_schema(self, receipt) -> ReceiptRead:
        """Convert a database Receipt model to ReceiptRead schema."""
        from app.schemas.friend import FriendRead
        from app.schemas.receipt import Item, Variation
        
        # Convert items
        items_data = []
        for item in receipt.items:
            # Convert variations
            variations_data = []
            if item.variations:
                for variation in item.variations:
                    variations_data.append(Variation(
                        variation_name=variation.variation_name,
                        price=float(variation.price)
                    ))
            
            # Populate friends per item from ItemFriend associations (preloaded via repository)
            item_friends_data: List[FriendRead] = []
            try:
                for link in getattr(item, "item_friends", []) or []:
                    # Skip soft-deleted links or missing friend
                    if getattr(link, "is_deleted", False):
                        continue
                    friend = getattr(link, "friend", None)
                    if not friend or getattr(friend, "is_deleted", False):
                        continue
                    item_friends_data.append(FriendRead(
                        id=friend.id,
                        user_id=friend.user_id,
                        name=friend.name,
                        photo_url=friend.photo_url or ""
                    ))
            except Exception:
                # Defensive: do not break response if relationships are missing
                item_friends_data = []
            items_data.append(Item(
                item_id=item.id,
                item_name=item.item_name,
                quantity=item.quantity,
                unit_price=float(item.unit_price),
                variation=variations_data if variations_data else None,
                friends=item_friends_data
            ))
        
        # Convert friends from ReceiptFriend associations
        friends_data = []
        for receipt_friend in receipt.friends:
            if hasattr(receipt_friend, 'friend') and receipt_friend.friend:
                friends_data.append(FriendRead(
                    id=receipt_friend.friend.id,
                    user_id=receipt_friend.friend.user_id,
                    name=receipt_friend.friend.name,
                    photo_url=receipt_friend.friend.photo_url or ""
                ))
        
        # Create ReceiptRead schema
        return ReceiptRead(
            id=receipt.id,
            user_id=receipt.user_id,
            restaurant_name=receipt.restaurant_name,
            subtotal=float(receipt.subtotal),
            total_amount=float(receipt.total_amount),
            tax=float(receipt.tax),
            service_charge=float(receipt.service_charge),
            currency=receipt.currency,
            receipt_url=receipt.receipt_url,
            status=getattr(receipt, 'status', 'ready'),
            created_at=receipt.created_at,
            updated_at=receipt.updated_at,
            items=items_data,
            friends=friends_data
        )

    def get_user_receipts(self, input_data: GetReceiptsInput, user_id: int, db: Session) -> GetReceiptsResult:
        """Get all receipts for the current user."""
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation("get_user_receipts_attempt", user_id=user_id, skip=sanitized_input.skip, limit=sanitized_input.limit)
        
        try:
            receipts = self.receipt_repo.get_by_user_with_relationships(
                user_id=user_id,
                skip=sanitized_input.skip,
                limit=sanitized_input.limit
            )
            
            # Convert to ReceiptRead schemas manually
            receipts_data = [self._convert_receipt_to_schema(receipt) for receipt in receipts]
            
            self.log_operation(
                "get_user_receipts_success",
                user_id=user_id,
                receipts_count=len(receipts_data)
            )
            
            return GetReceiptsResult(
                success=True,
                data=receipts_data,
                message=f"Retrieved {len(receipts_data)} receipts successfully"
            )
            
        except Exception as e:
            self.log_operation(
                "get_user_receipts_error",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise

    def delete_receipt(self, input_data: DeleteReceiptInput, user_id: int, db: Session) -> DeleteReceiptResult:
        """Delete a receipt."""
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation("delete_receipt_attempt", receipt_id=sanitized_input.receipt_id, user_id=user_id)
        
        try:
            def _operation() -> bool:
                # Verify receipt exists and is owned by user
                receipt = self.receipt_repo.get_by_id_and_user(sanitized_input.receipt_id, user_id)
                
                if not receipt:
                    raise ReceiptNotFoundError(
                        receipt_id=sanitized_input.receipt_id,
                        correlation_id=self.correlation_id
                    )
                
                # Delete receipt and all related items/variations
                deleted = self.receipt_repo.delete_with_items(sanitized_input.receipt_id, user_id)
                
                if not deleted:
                    raise ReceiptDeletionError(
                        reason=f"Failed to delete receipt {sanitized_input.receipt_id}",
                        correlation_id=self.correlation_id
                    )
                
                self.log_operation(
                    "delete_receipt_success",
                    receipt_id=sanitized_input.receipt_id
                )
                return True
            
            result = self.run_in_transaction(db, _operation)
            return DeleteReceiptResult(
                success=True,
                data=result,
                message="Receipt deleted successfully"
            )
            
        except (ReceiptNotFoundError, ReceiptDeletionError) as e:
            self.log_operation(
                "delete_receipt_failed",
                error_code=e.error_code,
                receipt_id=sanitized_input.receipt_id
            )
            return DeleteReceiptResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "delete_receipt_error",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise

    def calculate_receipt_splits(self, input_data: CalculateSplitsInput, user_id: int, db: Session) -> CalculateSplitsResult:
        """Calculate receipt splits."""
        sanitized_input = self._sanitize_input(input_data)
        self.log_operation("calculate_receipt_splits_attempt", receipt_id=sanitized_input.receipt_id, user_id=user_id)
        
        try:
            # Verify receipt exists and is owned by user
            receipt = self.receipt_repo.get_with_items(sanitized_input.receipt_id, user_id)
            
            if not receipt:
                raise ReceiptNotFoundError(
                    receipt_id=sanitized_input.receipt_id,
                    correlation_id=self.correlation_id
                )
            
            # Get receipt friends
            receipt_friends = self.receipt_friend_repo.get_receipt_friends(sanitized_input.receipt_id)
            
            if not receipt_friends:
                raise ReceiptSplitCalculationError(
                    reason="No friends associated with this receipt for split calculation",
                    correlation_id=self.correlation_id
                )
            
            # Calculate splits
            splits_data = self._calculate_splits(receipt, receipt_friends)
            
            self.log_operation(
                "calculate_receipt_splits_success",
                receipt_id=sanitized_input.receipt_id,
                friends_count=len(receipt_friends),
                total_amount=float(receipt.total_amount)
            )
            
            return CalculateSplitsResult(
                success=True,
                data=splits_data,
                message="Receipt splits calculated successfully"
            )
            
        except (ReceiptNotFoundError, ReceiptSplitCalculationError) as e:
            self.log_operation(
                "calculate_receipt_splits_failed",
                error_code=e.error_code,
                receipt_id=sanitized_input.receipt_id
            )
            return CalculateSplitsResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "calculate_receipt_splits_error",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise

    def _verify_friends_ownership(self, friend_ids: List[int], user_id: int, db: Session) -> List[Friend]:
        """Verify that all friends belong to the user."""
        friends = self.friend_repo.get_multiple_by_ids_and_user(friend_ids, user_id)
        
        if len(friends) != len(friend_ids):
            found_ids = [f.id for f in friends]
            missing_ids = [fid for fid in friend_ids if fid not in found_ids]
            raise ReceiptCreationError(
                reason=f"Friends not found or not owned by user: {missing_ids}",
                correlation_id=self.correlation_id
            )
        
        return friends

    def _calculate_splits(self, receipt: Receipt, friends: List[Friend]) -> Dict[str, Any]:
        """Calculate splits based on item-friend associations.

        - Only items associated to a friend contribute to that friend's subtotal.
        - Items with no associated friends are considered owner's responsibility.
        - Tax and service_charge are allocated proportionally to friends based on their subtotal share.
        """
        total_amount = Decimal(str(receipt.total_amount))
        tax = Decimal(str(receipt.tax))
        service_charge = Decimal(str(receipt.service_charge))

        # Prepare trackers
        items: List[Dict[str, Any]] = []
        per_item_share_by_friend: Dict[int, List[Dict[str, Any]]] = {f.id: [] for f in friends}
        friend_subtotals: Dict[int, Decimal] = {f.id: Decimal("0") for f in friends}
        receipt_subtotal: Decimal = Decimal("0")

        for item in getattr(receipt, "items", []) or []:
            unit_price = Decimal(str(item.unit_price))  # This is the total price for all units
            quantity = int(item.quantity)
            unit_total = _round2(unit_price / Decimal(quantity))  # Price per person
            line_total = unit_price  # Total price remains the same

            # Determine associated friends for this item (exclude soft-deleted and deleted friends)
            associated_friends: List[Friend] = []
            for link in getattr(item, "item_friends", []) or []:
                if getattr(link, "is_deleted", False):
                    continue
                f = getattr(link, "friend", None)
                if not f or getattr(f, "is_deleted", False):
                    continue
                associated_friends.append(f)

            shares: List[Dict[str, Any]] = []
            if associated_friends:
                per_friend_share = _round2(line_total / Decimal(len(associated_friends)))
                for f in associated_friends:
                    friend_subtotals[f.id] = friend_subtotals[f.id] + per_friend_share
                    per_item_share_by_friend[f.id].append({
                        "item_id": item.id,
                        "item_name": item.item_name,
                        "share": float(per_friend_share)
                    })
                    shares.append({
                        "id": f.id,
                        "name": f.name,
                        "share": float(per_friend_share)
                    })

            # Append item representation (only show assigned friends)
            items.append({
                "item_id": item.id,
                "item_name": item.item_name,
                "quantity": quantity,
                "unit_price": float(unit_price),
                "variations": [],
                "unit_total": float(unit_total),
                "line_total": float(line_total),
                "friends": shares
            })

            # Accumulate receipt subtotal from all items
            receipt_subtotal = receipt_subtotal + line_total

        # Build totals per friend with proportional tax/service allocations
        totals: List[Dict[str, Any]] = []
        for f in friends:
            subtotal_f = friend_subtotals[f.id]
            ratio = (subtotal_f / receipt_subtotal) if receipt_subtotal > 0 else Decimal("0")
            tax_f = _round2(tax * ratio)
            service_f = _round2(service_charge * ratio)
            total_f = subtotal_f + tax_f + service_f
            totals.append({
                "id": f.id,
                "name": f.name,
                "photo_url": getattr(f, "photo_url", None) or "",
                "subtotal": float(subtotal_f),
                "tax": float(tax_f),
                "service_charge": float(service_f),
                "total": float(total_f),
                "items": per_item_share_by_friend.get(f.id, [])
            })

        # Summary (full receipt totals)
        summary = {
            "subtotal": float(receipt_subtotal),
            "tax": float(tax),
            "service_charge": float(service_charge),
            "total": float(total_amount)
        }

        return {
            "receipt_id": receipt.id,
            "currency": receipt.currency,
            "totals": totals,
            "items": items,
            "summary": summary,
            "note": "Split based on assigned item friends; unassigned costs go to owner"
        }


