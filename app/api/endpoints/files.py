from fastapi import APIRouter, Depends
from app.services.file_services import download_file, generate_presigned_url
from app.api.dependencies.auth import get_current_user
router = APIRouter()

@router.get("/{file_id}")
def get_file_url(file_id: str, user=Depends(get_current_user)):
  url = generate_presigned_url(file_id)
  return url
