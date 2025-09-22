from minio import Minio
from app.core.config import settings

def _normalize_minio_endpoint(endpoint: str, default_secure: bool) -> tuple[str, bool]:
  ep = (endpoint or "").strip()
  secure = default_secure
  if ep.startswith("http://"):
    secure = False
    ep = ep[len("http://"):]
  elif ep.startswith("https://"):
    secure = True
    ep = ep[len("https://"):]
  if "/" in ep:
    ep = ep.split("/", 1)[0]
  return ep, secure

_endpoint, _secure = _normalize_minio_endpoint(settings.MINIO_ENDPOINT, settings.MINIO_SECURE)

minio_client = Minio(
  _endpoint,
  access_key=settings.MINIO_ACCESS_KEY,
  secret_key=settings.MINIO_SECRET_KEY,
  secure=_secure,
)

# Ensure bucket exists
if not minio_client.bucket_exists(settings.MINIO_BUCKET):
  minio_client.make_bucket(settings.MINIO_BUCKET)
