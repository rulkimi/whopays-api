"""File operation schemas for input validation and result objects.

This module defines Pydantic schemas for file operations including
upload, download, and URL generation with comprehensive validation.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator
import re
import mimetypes


class FileUploadInput(BaseModel):
    """Input validation for file upload operations."""
    
    folder: str = Field(..., description="Folder to store the file in")
    
    @validator('folder')
    def validate_folder(cls, v):
        """Validate and sanitize folder name."""
        if not v:
            raise ValueError("Folder name cannot be empty")
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', v.strip())
        
        if not sanitized:
            raise ValueError("Folder name must contain valid characters")
        
        if len(sanitized) > 50:
            raise ValueError("Folder name must be 50 characters or less")
        
        return sanitized


class FileDownloadInput(BaseModel):
    """Input validation for file download operations."""
    
    file_id: str = Field(..., description="Unique file identifier")
    
    @validator('file_id')
    def validate_file_id(cls, v):
        """Validate file ID format."""
        if not v or not v.strip():
            raise ValueError("File ID cannot be empty")
        
        # Basic sanitization - remove any path traversal attempts
        sanitized = v.strip().replace('..', '').replace('/', '_').replace('\\', '_')
        
        if len(sanitized) > 200:
            raise ValueError("File ID too long")
        
        return sanitized


class PresignedUrlInput(BaseModel):
    """Input validation for presigned URL generation."""
    
    file_id: str = Field(..., description="Unique file identifier")
    expiry_minutes: int = Field(default=10, description="URL expiry time in minutes")
    
    @validator('file_id')
    def validate_file_id(cls, v):
        """Validate file ID format."""
        if not v or not v.strip():
            raise ValueError("File ID cannot be empty")
        
        # Basic sanitization - remove any path traversal attempts
        sanitized = v.strip().replace('..', '').replace('/', '_').replace('\\', '_')
        
        if len(sanitized) > 200:
            raise ValueError("File ID too long")
        
        return sanitized
    
    @validator('expiry_minutes')
    def validate_expiry_minutes(cls, v):
        """Validate expiry time is within reasonable bounds."""
        if v < 1:
            raise ValueError("Expiry time must be at least 1 minute")
        if v > 1440:  # 24 hours
            raise ValueError("Expiry time cannot exceed 24 hours")
        return v


class FileValidationInput(BaseModel):
    """Input validation for file type and size validation."""
    
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    allowed_types: List[str] = Field(default_factory=list, description="Allowed MIME types")
    max_size_mb: int = Field(default=10, description="Maximum file size in MB")
    
    @validator('filename')
    def validate_filename(cls, v):
        """Validate and sanitize filename."""
        if not v or not v.strip():
            raise ValueError("Filename cannot be empty")
        
        # Remove path separators and dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', v.strip())
        
        if len(sanitized) > 255:
            raise ValueError("Filename too long")
        
        return sanitized
    
    @validator('file_size')
    def validate_file_size(cls, v):
        """Validate file size is positive."""
        if v < 0:
            raise ValueError("File size cannot be negative")
        return v
    
    @validator('max_size_mb')
    def validate_max_size(cls, v):
        """Validate maximum size is reasonable."""
        if v < 1:
            raise ValueError("Maximum size must be at least 1 MB")
        if v > 100:  # 100 MB limit
            raise ValueError("Maximum size cannot exceed 100 MB")
        return v


class FileUploadResult(BaseModel):
    """Result object for file upload operations."""
    
    success: bool
    data: Optional[str] = None  # file_id on success
    error_code: Optional[str] = None
    message: Optional[str] = None
    file_id: Optional[str] = None  # Convenience field
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set convenience field
        if self.success and self.data:
            self.file_id = self.data


class FileDownloadResult(BaseModel):
    """Result object for file download operations."""
    
    success: bool
    data: Optional[bytes] = None  # file content on success
    error_code: Optional[str] = None
    message: Optional[str] = None
    content_type: Optional[str] = None
    content_length: Optional[int] = None


class PresignedUrlResult(BaseModel):
    """Result object for presigned URL generation."""
    
    success: bool
    data: Optional[str] = None  # presigned URL on success
    error_code: Optional[str] = None
    message: Optional[str] = None
    url: Optional[str] = None  # Convenience field
    expires_in_minutes: Optional[int] = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set convenience field
        if self.success and self.data:
            self.url = self.data


class FileValidationResult(BaseModel):
    """Result object for file validation operations."""
    
    success: bool
    error_code: Optional[str] = None
    message: Optional[str] = None
    validation_errors: Optional[List[str]] = None
    file_type: Optional[str] = None
    is_valid_type: bool = True
    is_valid_size: bool = True


class FileInfo(BaseModel):
    """File information object."""
    
    file_id: str
    filename: str
    file_size: int
    content_type: Optional[str] = None
    upload_date: Optional[str] = None
    folder: Optional[str] = None


class FileListResult(BaseModel):
    """Result object for file listing operations."""
    
    success: bool
    data: Optional[List[FileInfo]] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    total_count: int = 0
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.data:
            self.total_count = len(self.data)


class FileOperationResult(BaseModel):
    """Generic result object for file operations."""
    
    success: bool
    data: Optional[dict] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    operation: Optional[str] = None
