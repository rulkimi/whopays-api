from app.api.dependencies.storage import minio_client
from app.core.config import settings
from fastapi import UploadFile
import uuid
from datetime import timedelta

def upload_file(file: UploadFile, folder: str) -> str:
	safe_filename = file.filename.replace(" ", "_")
	file_id = f"{folder}-{uuid.uuid4()}-{safe_filename}"

	minio_client.put_object(
		settings.MINIO_BUCKET,
		file_id,
		file.file,
		length=-1,  
		part_size=10 * 1024 * 1024,
	)

	return file_id

def download_file(file_id: str):
  response = minio_client.get_object(settings.MINIO_BUCKET, file_id)
  return response.read()

def generate_presigned_url(file_id: str, expiry_minutes: int = 10):
  url = minio_client.presigned_get_object(
    settings.MINIO_BUCKET,
    file_id,
    expires=timedelta(minutes=expiry_minutes)
  )
  return url.replace(settings.MINIO_ENDPOINT, settings.MINIO_PUBLIC_ENDPOINT)

