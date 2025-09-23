"""Authentication schemas with comprehensive validation."""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
import re


class Token(BaseModel):
    """JWT token response model."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: Optional[int] = None


class UserLogin(BaseModel):
    """User login request with validation."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ..., 
        min_length=8,
        max_length=128,
        description="User's password"
    )
    
    @validator('email')
    def validate_email_format(cls, v):
        """Additional email validation beyond EmailStr."""
        # Normalize email to lowercase
        email = str(v).lower().strip()
        
        # Basic length check
        if len(email) > 254:  # RFC 5321 limit
            raise ValueError("Email address too long")
            
        return email
    
    @validator('password')
    def validate_password_security(cls, v):
        """Validate password meets security requirements."""
        if len(v.strip()) != len(v):
            raise ValueError("Password cannot start or end with whitespace")
            
        # Check for basic complexity (at least one letter and one number)
        if not re.search(r'[A-Za-z]', v) or not re.search(r'\d', v):
            raise ValueError("Password must contain at least one letter and one number")
            
        return v


class AuthResult(BaseModel):
    """Authentication operation result."""
    success: bool
    token: Optional[Token] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "success": True,
                "token": {
                    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "token_type": "bearer"
                }
            }
        }


class RegistrationResult(BaseModel):
    """User registration operation result."""
    success: bool
    user_id: Optional[int] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "success": True,
                "user_id": 123,
                "message": "User registered successfully"
            }
        }
