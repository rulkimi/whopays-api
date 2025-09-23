"""Domain-specific exceptions for service layer operations.

This module provides a structured exception hierarchy with comprehensive error handling
capabilities for business operations, enabling proper error handling, logging, and
client response generation.

Architecture:
- ServiceError: Base exception with correlation ID and context support
- Category Base Classes: Domain-specific base exceptions (AuthError, BusinessError, etc.)
- Specific Exceptions: Concrete exceptions for specific business scenarios
- Error Context: Rich metadata and user-friendly message support
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from http import HTTPStatus


class ErrorSeverity(Enum):
    """Error severity levels for logging and monitoring."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification and handling."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    BUSINESS_RULE = "business_rule"
    RESOURCE_NOT_FOUND = "resource_not_found"
    CONFLICT = "conflict"
    EXTERNAL_SERVICE = "external_service"
    INFRASTRUCTURE = "infrastructure"
    SYSTEM = "system"


class ServiceError(Exception):
    """Base exception for all service layer errors.
    
    Provides structured error information with correlation ID support,
    HTTP status mapping, and rich context for debugging and client responses.
    
    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code for client handling
        correlation_id: Request correlation ID for tracing
        details: Additional error context (sanitized for logging)
        user_message: User-friendly message for client display
        severity: Error severity level for logging/monitoring
        category: Error category for classification
        http_status: HTTP status code for API responses
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "SERVICE_ERROR",
        correlation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        http_status: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR
    ):
        """Initialize service error with comprehensive context.
        
        Args:
            message: Human-readable error message for logging
            error_code: Machine-readable error code for client handling
            correlation_id: Request correlation ID for tracing
            details: Additional error context (sanitized for logging)
            user_message: User-friendly message for client display
            severity: Error severity level
            category: Error category for classification
            http_status: HTTP status code for API responses
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.correlation_id = correlation_id
        self.details = details or {}
        self.user_message = user_message or message
        self.severity = severity
        self.category = category
        self.http_status = http_status

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert exception to dictionary for logging or client response.
        
        Args:
            include_sensitive: Whether to include sensitive details
            
        Returns:
            Dictionary representation of the error
        """
        result = {
            "error_code": self.error_code,
            "message": self.user_message,
            "severity": self.severity.value,
            "category": self.category.value,
            "http_status": self.http_status.value
        }
        
        if self.correlation_id:
            result["correlation_id"] = self.correlation_id
            
        if include_sensitive and self.details:
            result["details"] = self.details
            result["internal_message"] = self.message
            
        return result

    def __str__(self) -> str:
        """String representation for logging."""
        return f"{self.error_code}: {self.message}"


# =============================================================================
# AUTHENTICATION & AUTHORIZATION ERRORS
# =============================================================================

class AuthError(ServiceError):
    """Base class for authentication and authorization errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        correlation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        http_status: HTTPStatus = HTTPStatus.UNAUTHORIZED
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            correlation_id=correlation_id,
            details=details,
            user_message=user_message,
            severity=severity,
            category=ErrorCategory.AUTHENTICATION,
            http_status=http_status
        )


class AuthenticationError(AuthError):
    """Authentication failed."""
    
    def __init__(
        self, 
        message: str = "Authentication failed",
        correlation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTH_FAILED",
            correlation_id=correlation_id,
            details=details,
            user_message="Authentication failed. Please check your credentials."
        )


class UserNotFoundError(AuthError):
    """User not found during authentication."""
    
    def __init__(
        self, 
        email: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message="User not found",
            error_code="USER_NOT_FOUND", 
            correlation_id=correlation_id,
            details={"email": email},
            user_message="User account not found. Please check your email address.",
            category=ErrorCategory.RESOURCE_NOT_FOUND,
            http_status=HTTPStatus.NOT_FOUND
        )


class UserInactiveError(AuthError):
    """User account is inactive."""
    
    def __init__(
        self, 
        user_id: int,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message="User account is inactive",
            error_code="USER_INACTIVE",
            correlation_id=correlation_id,
            details={"user_id": user_id},
            user_message="Your account is inactive. Please contact support.",
            http_status=HTTPStatus.FORBIDDEN
        )


class InvalidPasswordError(AuthError):
    """Invalid password provided."""
    
    def __init__(
        self, 
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message="Invalid password",
            error_code="INVALID_PASSWORD",
            correlation_id=correlation_id,
            user_message="Invalid password. Please try again.",
            severity=ErrorSeverity.LOW
        )


class EmailAlreadyExistsError(AuthError):
    """Email address is already registered."""
    
    def __init__(
        self, 
        email: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message="Email address already registered",
            error_code="EMAIL_EXISTS",
            correlation_id=correlation_id,
            details={"email": email},
            user_message="This email address is already registered. Please use a different email or try logging in.",
            category=ErrorCategory.CONFLICT,
            http_status=HTTPStatus.CONFLICT
        )


# =============================================================================
# VALIDATION ERRORS
# =============================================================================

class ValidationError(ServiceError):
    """Input validation failed."""
    
    def __init__(
        self, 
        field: str,
        message: str,
        correlation_id: Optional[str] = None,
        validation_errors: Optional[List[Dict[str, str]]] = None
    ):
        details = {"field": field, "validation_message": message}
        if validation_errors:
            details["validation_errors"] = validation_errors
            
        super().__init__(
            message=f"Validation failed for {field}: {message}",
            error_code="VALIDATION_ERROR",
            correlation_id=correlation_id,
            details=details,
            user_message=f"Invalid {field}: {message}",
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            http_status=HTTPStatus.BAD_REQUEST
        )


# =============================================================================
# BUSINESS DOMAIN ERRORS
# =============================================================================

class BusinessError(ServiceError):
    """Base class for business domain errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        correlation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        http_status: HTTPStatus = HTTPStatus.BAD_REQUEST
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            correlation_id=correlation_id,
            details=details,
            user_message=user_message,
            severity=severity,
            category=ErrorCategory.BUSINESS_RULE,
            http_status=http_status
        )


class ResourceNotFoundError(BusinessError):
    """Base class for resource not found errors."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: Union[int, str],
        user_id: Optional[int] = None,
        correlation_id: Optional[str] = None
    ):
        details = {"resource_type": resource_type, "resource_id": resource_id}
        if user_id is not None:
            details["user_id"] = user_id
            
        super().__init__(
            message=f"{resource_type} not found or access denied",
            error_code=f"{resource_type.upper()}_NOT_FOUND",
            correlation_id=correlation_id,
            details=details,
            user_message=f"{resource_type} not found or you don't have permission to access it.",
            http_status=HTTPStatus.NOT_FOUND
        )


# =============================================================================
# RECEIPT DOMAIN ERRORS
# =============================================================================

class ReceiptError(BusinessError):
    """Receipt-related errors."""
    pass


class ReceiptNotFoundError(ResourceNotFoundError):
    """Receipt not found or not owned by user."""
    
    def __init__(
        self, 
        receipt_id: int,
        user_id: int,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            resource_type="Receipt",
            resource_id=receipt_id,
            user_id=user_id,
            correlation_id=correlation_id
        )


class ReceiptAnalysisError(ReceiptError):
    """Receipt AI analysis failed."""
    
    def __init__(
        self, 
        reason: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Receipt analysis failed: {reason}",
            error_code="RECEIPT_ANALYSIS_FAILED",
            correlation_id=correlation_id,
            details={"reason": reason},
            user_message="Unable to analyze receipt. Please try uploading a clearer image.",
            severity=ErrorSeverity.HIGH
        )


class ReceiptCreationError(ReceiptError):
    """Receipt creation failed."""
    
    def __init__(
        self, 
        reason: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Receipt creation failed: {reason}",
            error_code="RECEIPT_CREATION_FAILED",
            correlation_id=correlation_id,
            details={"reason": reason},
            user_message="Unable to create receipt. Please try again."
        )


class ReceiptDeletionError(ReceiptError):
    """Receipt deletion failed."""
    
    def __init__(
        self, 
        receipt_id: int,
        reason: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Receipt deletion failed: {reason}",
            error_code="RECEIPT_DELETION_FAILED",
            correlation_id=correlation_id,
            details={"receipt_id": receipt_id, "reason": reason},
            user_message="Unable to delete receipt. Please try again."
        )


class ReceiptSplitCalculationError(ReceiptError):
    """Receipt split calculation failed."""
    
    def __init__(
        self, 
        receipt_id: int,
        reason: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Receipt split calculation failed: {reason}",
            error_code="RECEIPT_SPLIT_FAILED",
            correlation_id=correlation_id,
            details={"receipt_id": receipt_id, "reason": reason},
            user_message="Unable to calculate receipt split. Please check the receipt items and try again."
        )


# =============================================================================
# FRIEND DOMAIN ERRORS  
# =============================================================================

class FriendError(BusinessError):
    """Friend-related errors."""
    pass


class FriendNotFoundError(ResourceNotFoundError):
    """Friend not found or not owned by user."""
    
    def __init__(
        self, 
        friend_id: int,
        user_id: int,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            resource_type="Friend",
            resource_id=friend_id,
            user_id=user_id,
            correlation_id=correlation_id
        )


class FriendsValidationError(FriendError):
    """One or more friends are invalid or don't belong to the user."""
    
    def __init__(
        self, 
        invalid_friend_ids: List[int],
        user_id: int,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Invalid or unauthorized friends: {invalid_friend_ids}",
            error_code="FRIENDS_VALIDATION_FAILED",
            correlation_id=correlation_id,
            details={"invalid_friend_ids": invalid_friend_ids, "user_id": user_id},
            user_message="Some selected friends are not valid. Please check your selection."
        )


class FriendCreationError(FriendError):
    """Friend creation failed."""
    
    def __init__(
        self, 
        reason: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Friend creation failed: {reason}",
            error_code="FRIEND_CREATION_FAILED",
            correlation_id=correlation_id,
            details={"reason": reason},
            user_message="Unable to create friend. Please try again."
        )


class FriendUpdateError(FriendError):
    """Friend update failed."""
    
    def __init__(
        self, 
        friend_id: int,
        reason: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Friend update failed: {reason}",
            error_code="FRIEND_UPDATE_FAILED",
            correlation_id=correlation_id,
            details={"friend_id": friend_id, "reason": reason},
            user_message="Unable to update friend. Please try again."
        )


class FriendDeletionError(FriendError):
    """Friend deletion failed."""
    
    def __init__(
        self, 
        friend_id: int,
        reason: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Friend deletion failed: {reason}",
            error_code="FRIEND_DELETION_FAILED",
            correlation_id=correlation_id,
            details={"friend_id": friend_id, "reason": reason},
            user_message="Unable to delete friend. Please try again."
        )


# =============================================================================
# ITEM DOMAIN ERRORS
# =============================================================================

class ItemError(BusinessError):
    """Item-related errors."""
    pass


class ItemNotFoundError(ResourceNotFoundError):
    """Item not found or not owned by user."""
    
    def __init__(
        self, 
        item_id: int,
        user_id: int,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            resource_type="Item",
            resource_id=item_id,
            user_id=user_id,
            correlation_id=correlation_id
        )


class ItemFriendsValidationError(ItemError):
    """One or more friends are invalid for item assignment."""
    
    def __init__(
        self, 
        invalid_friend_ids: List[int],
        user_id: int,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Invalid or unauthorized friends for item: {invalid_friend_ids}",
            error_code="ITEM_FRIENDS_VALIDATION_FAILED",
            correlation_id=correlation_id,
            details={"invalid_friend_ids": invalid_friend_ids, "user_id": user_id},
            user_message="Some selected friends cannot be assigned to this item. Please check your selection."
        )


# =============================================================================
# ASSOCIATION ERRORS
# =============================================================================

class ReceiptFriendError(BusinessError):
    """Receipt-Friend association related errors."""
    pass


class ItemFriendError(BusinessError):
    """Item-Friend association related errors."""
    pass


class AssociationError(BusinessError):
    """Base class for association management errors."""
    
    def __init__(
        self,
        operation: str,
        entity_type: str,
        entity_id: int,
        reason: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"{entity_type} {operation} failed: {reason}",
            error_code=f"{entity_type.upper()}_{operation.upper()}_FAILED",
            correlation_id=correlation_id,
            details={"operation": operation, f"{entity_type.lower()}_id": entity_id, "reason": reason},
            user_message=f"Unable to {operation} {entity_type.lower()}. Please try again."
        )


class ReceiptFriendAssociationError(ReceiptFriendError):
    """Failed to manage receipt-friend associations."""
    
    def __init__(
        self, 
        operation: str,
        receipt_id: int,
        reason: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Receipt-friend {operation} failed: {reason}",
            error_code="RECEIPT_FRIEND_ASSOCIATION_FAILED",
            correlation_id=correlation_id,
            details={"operation": operation, "receipt_id": receipt_id, "reason": reason},
            user_message=f"Unable to {operation} receipt-friend association. Please try again."
        )


class ItemFriendAssociationError(ItemFriendError):
    """Failed to manage item-friend associations."""
    
    def __init__(
        self, 
        operation: str,
        item_id: int,
        reason: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Item-friend {operation} failed: {reason}",
            error_code="ITEM_FRIEND_ASSOCIATION_FAILED",
            correlation_id=correlation_id,
            details={"operation": operation, "item_id": item_id, "reason": reason},
            user_message=f"Unable to {operation} item-friend association. Please try again."
        )


# =============================================================================
# FILE & INFRASTRUCTURE ERRORS
# =============================================================================

class InfrastructureError(ServiceError):
    """Base class for infrastructure-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        correlation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        http_status: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            correlation_id=correlation_id,
            details=details,
            user_message=user_message or "A system error occurred. Please try again later.",
            severity=severity,
            category=ErrorCategory.INFRASTRUCTURE,
            http_status=http_status
        )


class FileError(InfrastructureError):
    """File-related errors."""
    pass


class FileUploadError(FileError):
    """File upload failed."""
    
    def __init__(
        self, 
        filename: str,
        reason: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"File upload failed for '{filename}': {reason}",
            error_code="FILE_UPLOAD_FAILED",
            correlation_id=correlation_id,
            details={"filename": filename, "reason": reason},
            user_message="File upload failed. Please try again with a different file."
        )


class FileDownloadError(FileError):
    """File download failed."""
    
    def __init__(
        self, 
        file_id: str,
        reason: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"File download failed for '{file_id}': {reason}",
            error_code="FILE_DOWNLOAD_FAILED",
            correlation_id=correlation_id,
            details={"file_id": file_id, "reason": reason},
            user_message="File download failed. Please try again."
        )


class FileNotFoundError(FileError):
    """File not found in storage."""
    
    def __init__(
        self, 
        file_id: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"File not found: {file_id}",
            error_code="FILE_NOT_FOUND",
            correlation_id=correlation_id,
            details={"file_id": file_id},
            user_message="File not found.",
            category=ErrorCategory.RESOURCE_NOT_FOUND,
            http_status=HTTPStatus.NOT_FOUND
        )


class FileAccessError(FileError):
    """File access denied or unauthorized."""
    
    def __init__(
        self, 
        file_id: str,
        user_id: int,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"File access denied: {file_id}",
            error_code="FILE_ACCESS_DENIED",
            correlation_id=correlation_id,
            details={"file_id": file_id, "user_id": user_id},
            user_message="You don't have permission to access this file.",
            category=ErrorCategory.AUTHORIZATION,
            http_status=HTTPStatus.FORBIDDEN
        )


class FileStorageError(FileError):
    """File storage system error."""
    
    def __init__(
        self, 
        operation: str,
        reason: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"File storage {operation} failed: {reason}",
            error_code="FILE_STORAGE_ERROR",
            correlation_id=correlation_id,
            details={"operation": operation, "reason": reason},
            severity=ErrorSeverity.CRITICAL
        )


class InvalidFileTypeError(FileError):
    """Invalid file type or format."""
    
    def __init__(
        self, 
        filename: str,
        file_type: str,
        allowed_types: List[str],
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Invalid file type '{file_type}' for '{filename}'. Allowed types: {allowed_types}",
            error_code="INVALID_FILE_TYPE",
            correlation_id=correlation_id,
            details={"filename": filename, "file_type": file_type, "allowed_types": allowed_types},
            user_message=f"Invalid file type. Please upload a file with one of these types: {', '.join(allowed_types)}",
            category=ErrorCategory.VALIDATION,
            http_status=HTTPStatus.BAD_REQUEST,
            severity=ErrorSeverity.LOW
        )


class FileSizeLimitError(FileError):
    """File size exceeds limit."""
    
    def __init__(
        self, 
        filename: str,
        file_size: int,
        max_size: int,
        correlation_id: Optional[str] = None
    ):
        max_size_mb = max_size / (1024 * 1024)
        file_size_mb = file_size / (1024 * 1024)
        
        super().__init__(
            message=f"File '{filename}' size {file_size} bytes exceeds limit of {max_size} bytes",
            error_code="FILE_SIZE_LIMIT_EXCEEDED",
            correlation_id=correlation_id,
            details={"filename": filename, "file_size": file_size, "max_size": max_size},
            user_message=f"File size ({file_size_mb:.1f}MB) exceeds the maximum allowed size of {max_size_mb:.1f}MB.",
            category=ErrorCategory.VALIDATION,
            http_status=HTTPStatus.BAD_REQUEST,
            severity=ErrorSeverity.LOW
        )


class PhotoUploadError(FileError):
    """Photo upload failed."""
    
    def __init__(
        self, 
        reason: str,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=f"Photo upload failed: {reason}",
            error_code="PHOTO_UPLOAD_FAILED",
            correlation_id=correlation_id,
            details={"reason": reason},
            user_message="Photo upload failed. Please try again with a different image."
        )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_error_response(
    error: ServiceError,
    include_details: bool = False
) -> Dict[str, Any]:
    """Create standardized error response dictionary.
    
    Args:
        error: ServiceError instance
        include_details: Whether to include sensitive details
        
    Returns:
        Standardized error response dictionary
    """
    return error.to_dict(include_sensitive=include_details)


def get_http_status_for_error(error: Exception) -> HTTPStatus:
    """Get appropriate HTTP status code for an exception.
    
    Args:
        error: Exception instance
        
    Returns:
        Appropriate HTTP status code
    """
    if isinstance(error, ServiceError):
        return error.http_status
    
    # Default mappings for non-ServiceError exceptions
    error_mappings = {
        ValueError: HTTPStatus.BAD_REQUEST,
        TypeError: HTTPStatus.BAD_REQUEST,
        KeyError: HTTPStatus.NOT_FOUND,
        AttributeError: HTTPStatus.INTERNAL_SERVER_ERROR,
        NotImplementedError: HTTPStatus.NOT_IMPLEMENTED,
    }
    
    return error_mappings.get(type(error), HTTPStatus.INTERNAL_SERVER_ERROR)