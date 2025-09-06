from app.api.dependencies.storage import minio_client
from app.core.config import settings
from fastapi import UploadFile
import uuid

def upload_file(file: UploadFile, folder: str) -> str:
  file_id = f"{folder}/{uuid.uuid4()}-{file.filename}"

  minio_client.put_object(
    settings.MINIO_BUCKET,
    file_id,
    file.file,
    length=-1,  # MinIO will handle unknown file size
    part_size=10 * 1024 * 1024,
  )

  return f"{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{file_id}"


def download_file(file_id: str):
  response = minio_client.get_object(settings.MINIO_BUCKET, file_id)
  return response.read()

