"""Base service class with common functionality for all services."""

import logging
from typing import Optional, Callable, TypeVar, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

T = TypeVar("T")


class BaseService:
    """Base service class providing common functionality for all services.
    
    Provides:
    - Transaction handling with rollback
    - Structured logging with correlation ID
    - Common error handling patterns
    - Repository coordination for business operations
    """
    
    def __init__(self, correlation_id: Optional[str] = None):
        """Initialize base service with optional correlation ID.
        
        Args:
            correlation_id: Optional request correlation ID for logging
        """
        self.correlation_id = correlation_id
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _set_repositories(self, **repositories):
        """Set repository instances for this service.
        
        This method should be called by subclasses to inject repositories.
        
        Args:
            **repositories: Named repository instances
        """
        for name, repo in repositories.items():
            setattr(self, name, repo)
    
    def run_in_transaction(self, db: Session, operation: Callable[[], T]) -> T:
        """Execute operation within a database transaction.
        
        Commits on success, rolls back on any exception.
        
        Args:
            db: Database session to use for the transaction
            operation: Callable that performs database operations
            
        Returns:
            Result of the operation
            
        Raises:
            Exception: Re-raises any exception from the operation after rollback
        """
        try:
            result = operation()
            db.commit()
            self.logger.info(
                "Transaction committed successfully",
                extra={
                    "correlation_id": self.correlation_id,
                    "service": self.__class__.__name__
                }
            )
            return result
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(
                "Database error occurred, transaction rolled back",
                extra={
                    "correlation_id": self.correlation_id,
                    "service": self.__class__.__name__,
                    "error": str(e)
                }
            )
            raise
        except Exception as e:
            db.rollback()
            self.logger.error(
                "Unexpected error occurred, transaction rolled back",
                extra={
                    "correlation_id": self.correlation_id,
                    "service": self.__class__.__name__,
                    "error": str(e)
                }
            )
            raise
    
    def log_operation(self, operation: str, **kwargs: Any) -> None:
        """Log service operation with structured fields.
        
        Args:
            operation: Name of the operation being performed
            **kwargs: Additional fields to include in log
        """
        log_data = {
            "correlation_id": self.correlation_id,
            "service": self.__class__.__name__,
            "operation": operation,
            **kwargs
        }
        self.logger.info(f"Service operation: {operation}", extra=log_data)
