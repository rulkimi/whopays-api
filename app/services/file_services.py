from app.api.dependencies.storage import minio_client
from app.core.config import settings
from fastapi import UploadFile
import uuid
from datetime import timedelta
from urllib.parse import urlparse

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
    raw_url = minio_client.presigned_get_object(
        settings.MINIO_BUCKET,
        file_id,
        expires=timedelta(minutes=expiry_minutes),
    )

    # Ensure we only swap host:port, not scheme
    internal = settings.MINIO_ENDPOINT
    public = settings.MINIO_PUBLIC_ENDPOINT.rstrip("/")

    # replace only netloc (host:port), not scheme
    parsed = urlparse(raw_url)
    replaced = raw_url.replace(f"{parsed.scheme}://{parsed.netloc}", public, 1)
    return replaced

