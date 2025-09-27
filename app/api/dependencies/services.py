"""Service dependency providers for FastAPI dependency injection."""

from fastapi import Depends, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.api.dependencies.database import get_db
from app.services.auth_services import AuthService
from app.services.receipt_services import ReceiptService
from app.services.receipt_friend_services import ReceiptFriendService
from app.services.item_friend_services import ItemFriendService
from app.services.friend_services import FriendService
from app.services.file_services import FileService
from app.services.job_services import JobService
from app.repositories.user import UserRepository
from app.repositories.receipt import ReceiptRepository
from app.repositories.item import ItemRepository
from app.repositories.friend import FriendRepository
from app.repositories.receipt_friend import ReceiptFriendRepository
from app.repositories.item_friend import ItemFriendRepository
from app.repositories.job import JobRepository


def get_correlation_id(request: Request) -> Optional[str]:
	"""Extract or generate correlation ID for logging and tracing."""
	from app.core.observability import generate_correlation_id
	cid = getattr(request.state, "correlation_id", None)
	if not cid:
		cid = generate_correlation_id(request.headers.get("X-Correlation-ID"))
		setattr(request.state, "correlation_id", cid)
	return cid


# Repository Dependencies
def get_user_repository(
    db: Session = Depends(get_db),
    correlation_id: Optional[str] = Depends(get_correlation_id)
) -> UserRepository:
    """Provide UserRepository instance."""
    return UserRepository(db=db, correlation_id=correlation_id)


def get_receipt_repository(
    db: Session = Depends(get_db),
    correlation_id: Optional[str] = Depends(get_correlation_id)
) -> ReceiptRepository:
    """Provide ReceiptRepository instance."""
    return ReceiptRepository(db=db, correlation_id=correlation_id)


def get_item_repository(
    db: Session = Depends(get_db),
    correlation_id: Optional[str] = Depends(get_correlation_id)
) -> ItemRepository:
    """Provide ItemRepository instance."""
    return ItemRepository(db=db, correlation_id=correlation_id)


def get_friend_repository(
    db: Session = Depends(get_db),
    correlation_id: Optional[str] = Depends(get_correlation_id)
) -> FriendRepository:
    """Provide FriendRepository instance."""
    return FriendRepository(db=db, correlation_id=correlation_id)


def get_receipt_friend_repository(
    db: Session = Depends(get_db),
    correlation_id: Optional[str] = Depends(get_correlation_id)
) -> ReceiptFriendRepository:
    """Provide ReceiptFriendRepository instance."""
    return ReceiptFriendRepository(db=db, correlation_id=correlation_id)


def get_item_friend_repository(
    db: Session = Depends(get_db),
    correlation_id: Optional[str] = Depends(get_correlation_id)
) -> ItemFriendRepository:
    """Provide ItemFriendRepository instance."""
    return ItemFriendRepository(db=db, correlation_id=correlation_id)


def get_job_repository(
    db: Session = Depends(get_db),
    correlation_id: Optional[str] = Depends(get_correlation_id)
) -> JobRepository:
    """Provide JobRepository instance."""
    return JobRepository(db=db, correlation_id=correlation_id)


# Service Dependencies
def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    correlation_id: Optional[str] = Depends(get_correlation_id)
) -> AuthService:
    """Provide AuthService instance with user repository and correlation ID.
    
    This demonstrates the standard service dependency injection pattern:
    - Repository dependencies injected through FastAPI Depends
    - Correlation ID for request tracing
    - Clean separation of concerns
    
    Args:
        user_repo: User repository from dependency injection
        correlation_id: Optional correlation ID from request headers
        
    Returns:
        Configured AuthService instance
    """
    return AuthService(correlation_id=correlation_id, user_repo=user_repo)


def get_receipt_service(
    receipt_repo: ReceiptRepository = Depends(get_receipt_repository),
    item_repo: ItemRepository = Depends(get_item_repository),
    friend_repo: FriendRepository = Depends(get_friend_repository),
    receipt_friend_repo: ReceiptFriendRepository = Depends(get_receipt_friend_repository),
    item_friend_repo: ItemFriendRepository = Depends(get_item_friend_repository),
    correlation_id: Optional[str] = Depends(get_correlation_id)
) -> ReceiptService:
    """Provide ReceiptService instance with all required repositories.
    
    Args:
        receipt_repo: Receipt repository from dependency injection
        item_repo: Item repository from dependency injection
        friend_repo: Friend repository from dependency injection
        receipt_friend_repo: Receipt-Friend repository from dependency injection
        item_friend_repo: Item-Friend repository from dependency injection
        correlation_id: Optional correlation ID from request headers
        
    Returns:
        Configured ReceiptService instance
    """
    return ReceiptService(
        receipt_repo=receipt_repo,
        item_repo=item_repo,
        friend_repo=friend_repo,
        receipt_friend_repo=receipt_friend_repo,
        item_friend_repo=item_friend_repo,
        correlation_id=correlation_id
    )


def get_receipt_friend_service(
    receipt_repo: ReceiptRepository = Depends(get_receipt_repository),
    friend_repo: FriendRepository = Depends(get_friend_repository),
    receipt_friend_repo: ReceiptFriendRepository = Depends(get_receipt_friend_repository),
    correlation_id: Optional[str] = Depends(get_correlation_id)
) -> ReceiptFriendService:
    """Provide ReceiptFriendService instance with required repositories.
    
    Args:
        receipt_repo: Receipt repository from dependency injection
        friend_repo: Friend repository from dependency injection
        receipt_friend_repo: Receipt-Friend repository from dependency injection
        correlation_id: Optional correlation ID from request headers
        
    Returns:
        Configured ReceiptFriendService instance
    """
    return ReceiptFriendService(
        receipt_repo=receipt_repo,
        friend_repo=friend_repo,
        receipt_friend_repo=receipt_friend_repo,
        correlation_id=correlation_id
    )


def get_item_friend_service(
    item_friend_repo: ItemFriendRepository = Depends(get_item_friend_repository),
    item_repo: ItemRepository = Depends(get_item_repository),
    friend_repo: FriendRepository = Depends(get_friend_repository),
    correlation_id: Optional[str] = Depends(get_correlation_id)
) -> ItemFriendService:
    """Provide ItemFriendService instance with required repositories.
    
    Args:
        item_friend_repo: Item-Friend repository from dependency injection
        item_repo: Item repository from dependency injection
        friend_repo: Friend repository from dependency injection
        correlation_id: Optional correlation ID from request headers
        
    Returns:
        Configured ItemFriendService instance
    """
    return ItemFriendService(
        item_friend_repo=item_friend_repo,
        item_repo=item_repo,
        friend_repo=friend_repo,
        correlation_id=correlation_id
    )


def get_friend_service(
    friend_repo: FriendRepository = Depends(get_friend_repository),
    correlation_id: Optional[str] = Depends(get_correlation_id)
) -> FriendService:
    """Provide FriendService instance with required repositories.
    
    This demonstrates the standard service dependency injection pattern:
    - Repository dependencies injected through FastAPI Depends
    - Correlation ID for request tracing
    - Clean separation of concerns
    
    Args:
        friend_repo: Friend repository from dependency injection
        correlation_id: Optional correlation ID from request headers
        
    Returns:
        Configured FriendService instance
    """
    return FriendService(correlation_id=correlation_id, friend_repo=friend_repo)


def get_file_service(
    correlation_id: Optional[str] = Depends(get_correlation_id)
) -> FileService:
    """Provide FileService instance with correlation ID.
    
    FileService is stateless and doesn't require repository dependencies
    as it interacts directly with MinIO storage. It only needs correlation ID
    for structured logging and request tracing.
    
    Args:
        correlation_id: Optional correlation ID from request headers
        
    Returns:
        Configured FileService instance
    """
    return FileService(correlation_id=correlation_id)


def get_job_service(
    job_repo: JobRepository = Depends(get_job_repository),
    correlation_id: Optional[str] = Depends(get_correlation_id)
) -> JobService:
    """Provide JobService instance with required repository."""
    return JobService(job_repo=job_repo, correlation_id=correlation_id)
