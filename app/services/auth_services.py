"""Authentication service for user registration and login operations.

This service provides secure user authentication with comprehensive error handling,
input validation, and structured logging. It serves as the reference implementation
for service layer patterns in the application.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.services.base import BaseService
from app.services.exceptions import (
    AuthenticationError,
    UserNotFoundError, 
    UserInactiveError,
    InvalidPasswordError,
    EmailAlreadyExistsError,
    ValidationError
)
from app.repositories.user import UserRepository
from app.db.models.user import User
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from app.schemas.user import UserCreate
from app.schemas.auth import UserLogin, AuthResult, RegistrationResult, Token


class AuthService(BaseService):
    """Service class for handling user authentication operations.
    
    This service demonstrates the standard architecture pattern for all services:
    - Dependency injection through constructor or _set_repositories
    - Comprehensive error handling with domain exceptions
    - Input validation using Pydantic schemas
    - Structured logging with correlation IDs
    - Transaction management for data operations
    - Type-safe result objects instead of Optional returns
    
    Security Features:
    - Input sanitization and validation
    - Password complexity requirements
    - Structured audit logging
    - Clear separation of authentication concerns
    """
    
    def __init__(self, correlation_id: Optional[str] = None, **repositories):
        """Initialize authentication service.
        
        Args:
            correlation_id: Optional request correlation ID for logging
            **repositories: Repository instances (user_repo, etc.)
        """
        super().__init__(correlation_id)
        if repositories:
            self._set_repositories(**repositories)
        
        # Ensure required repositories are available
        if not hasattr(self, 'user_repo'):
            raise ValidationError(
                field="user_repo",
                message="UserRepository is required for AuthService",
                correlation_id=correlation_id
            )
    
    def register_user(self, user_in: UserCreate, db: Session) -> RegistrationResult:
        """Create a new user if the email is not already registered.
        
        This method demonstrates the standard service pattern:
        - Input validation through Pydantic schema
        - Domain exception handling
        - Transaction management
        - Structured result objects
        - Security-focused logging
        
        Args:
            user_in: User creation data containing email, name, and password
            db: Database session for transaction management
            
        Returns:
            RegistrationResult with success status and user details or error info
            
        Raises:
            EmailAlreadyExistsError: If email is already registered
            ValidationError: If input validation fails
        """
        # Sanitize and validate input
        sanitized_email = user_in.email.lower().strip()
        self.log_operation(
            "register_user_attempt", 
            email_domain=sanitized_email.split('@')[1] if '@' in sanitized_email else 'unknown'
        )
        
        try:
            def _register_operation() -> User:
                # Check if user already exists
                if self.user_repo.email_exists(sanitized_email):
                    raise EmailAlreadyExistsError(
                        email=sanitized_email,
                        correlation_id=self.correlation_id
                    )

                # Create new user with hashed password
                hashed_password = get_password_hash(user_in.password)
                new_user = self.user_repo.create_user(user_in, hashed_password)
                
                self.log_operation(
                    "register_user_success", 
                    user_id=new_user.id,
                    email_domain=sanitized_email.split('@')[1]
                )
                return new_user
            
            user = self.run_in_transaction(db, _register_operation)
            return RegistrationResult(
                success=True,
                user_id=user.id,
                message="User registered successfully"
            )
            
        except EmailAlreadyExistsError as e:
            self.log_operation(
                "register_user_failed",
                error_code=e.error_code,
                reason="email_already_exists"
            )
            return RegistrationResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "register_user_error",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise

    def authenticate_user_and_create_token(self, login_data: UserLogin) -> AuthResult:
        """Authenticate a user by email and password.
        
        This method demonstrates secure authentication with:
        - Input validation and sanitization
        - Domain-specific exceptions
        - Security-focused logging (no sensitive data)
        - Structured result objects
        - Clear error categorization
        
        Args:
            login_data: Validated login credentials from UserLogin schema
            
        Returns:
            AuthResult with token on success or error details on failure
            
        Raises:
            UserNotFoundError: If user doesn't exist
            UserInactiveError: If user account is inactive  
            InvalidPasswordError: If password is incorrect
        """
        # Input is already validated by Pydantic schema
        sanitized_email = login_data.email.lower().strip()
        
        self.log_operation(
            "authenticate_user_attempt", 
            email_domain=sanitized_email.split('@')[1] if '@' in sanitized_email else 'unknown'
        )
        
        try:
            # Find user by email
            user = self.user_repo.get_by_email(sanitized_email)
            if not user:
                raise UserNotFoundError(
                    email=sanitized_email,
                    correlation_id=self.correlation_id
                )
            
            # Check if user is active
            if not user.is_active:
                raise UserInactiveError(
                    user_id=user.id,
                    correlation_id=self.correlation_id
                )
            
            # Verify password
            if not verify_password(login_data.password, user.hashed_password):
                raise InvalidPasswordError(correlation_id=self.correlation_id)

            # Create access and refresh tokens
            access_token = create_access_token({"sub": str(user.id)})
            refresh_token = create_refresh_token({"sub": str(user.id)})
            
            # Calculate expiration time in seconds
            from app.core.config import settings
            expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert minutes to seconds
            
            self.log_operation(
                "authenticate_user_success", 
                user_id=user.id,
                email_domain=sanitized_email.split('@')[1]
            )
            
            return AuthResult(
                success=True,
                token=Token(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_type="bearer",
                    expires_in=expires_in
                )
            )
            
        except (UserNotFoundError, UserInactiveError, InvalidPasswordError) as e:
            self.log_operation(
                "authenticate_user_failed",
                error_code=e.error_code,
                reason=e.error_code.lower()
            )
            return AuthResult(
                success=False,
                error_code=e.error_code,
                message=e.message
            )
        except Exception as e:
            self.log_operation(
                "authenticate_user_error",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise
    
    # Convenience method for backward compatibility
    def authenticate_user(self, email: str, password: str) -> AuthResult:
        """Authenticate user with email and password strings.
        
        This method provides backward compatibility while encouraging
        use of the validated UserLogin schema.
        
        Args:
            email: User's email address
            password: Plain text password
            
        Returns:
            AuthResult with authentication outcome
        """
        try:
            login_data = UserLogin(email=email, password=password)
            return self.authenticate_user_and_create_token(login_data)
        except ValueError as e:
            return AuthResult(
                success=False,
                error_code="VALIDATION_ERROR",
                message=f"Input validation failed: {str(e)}"
            )
