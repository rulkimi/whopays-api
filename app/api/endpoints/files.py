from fastapi import Depends, HTTPException, UploadFile, File
from app.api.router import create_router
from fastapi.responses import Response
from app.services.file_services import FileService
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_file_service
from app.schemas.file import (
    PresignedUrlInput,
    FileUploadInput,
    FileDownloadInput,
    PresignedUrlResult,
    FileUploadResult,
    FileDownloadResult
)
from app.db.models.user import User

router = create_router(name="files")


@router.get("/{file_id}")
def serve_file(
    file_id: str,
    user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
) -> Response:
    """Serve file content directly.
    
    Args:
        file_id: Unique file identifier
        user: Current authenticated user
        file_service: File service instance
        
    Returns:
        Response with file content
        
    Raises:
        HTTPException: If file serving fails
    """
    try:
        input_data = FileDownloadInput(file_id=file_id)
        result = file_service.download_file(input_data)
        
        if result.success:
            return Response(
                content=result.data,
                media_type=result.content_type or "application/octet-stream",
                headers={
                    "Content-Length": str(result.content_length or len(result.data))
                }
            )
        else:
            raise HTTPException(
                status_code=404 if result.error_code == "FILE_NOT_FOUND" else 400,
                detail={
                    "error_code": result.error_code,
                    "message": result.message
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error_code": "INTERNAL_ERROR", "message": str(e)}
        )


@router.get("/{file_id}/url")
def get_file_url(
    file_id: str,
    expiry_minutes: int = 10,
    user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
) -> PresignedUrlResult:
    """Generate presigned URL for file access.
    
    Args:
        file_id: Unique file identifier
        expiry_minutes: URL expiry time in minutes (default: 10)
        user: Current authenticated user
        file_service: File service instance
        
    Returns:
        PresignedUrlResult with URL or error information
        
    Raises:
        HTTPException: If URL generation fails
    """
    try:
        input_data = PresignedUrlInput(file_id=file_id, expiry_minutes=expiry_minutes)
        result = file_service.generate_presigned_url(input_data)
        
        if result.success:
            return result
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": result.error_code,
                    "message": result.message
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error_code": "INTERNAL_ERROR", "message": str(e)}
        )


@router.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    folder: str = "uploads",
    user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
) -> FileUploadResult:
    """Upload file to storage.
    
    Args:
        file: File to upload
        folder: Storage folder name (default: "uploads")
        user: Current authenticated user
        file_service: File service instance
        
    Returns:
        FileUploadResult with file_id or error information
        
    Raises:
        HTTPException: If upload fails
    """
    try:
        input_data = FileUploadInput(folder=folder)
        result = file_service.upload_file(file, input_data)
        
        if result.success:
            return result
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": result.error_code,
                    "message": result.message
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error_code": "INTERNAL_ERROR", "message": str(e)}
        )


@router.get("/download/{file_id}")
def download_file(
    file_id: str,
    user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
) -> FileDownloadResult:
    """Download file from storage.
    
    Args:
        file_id: Unique file identifier
        user: Current authenticated user
        file_service: File service instance
        
    Returns:
        FileDownloadResult with file content or error information
        
    Raises:
        HTTPException: If download fails
    """
    try:
        input_data = FileDownloadInput(file_id=file_id)
        result = file_service.download_file(input_data)
        
        if result.success:
            return result
        else:
            raise HTTPException(
                status_code=400 if result.error_code != "FILE_NOT_FOUND" else 404,
                detail={
                    "error_code": result.error_code,
                    "message": result.message
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error_code": "INTERNAL_ERROR", "message": str(e)}
        )
