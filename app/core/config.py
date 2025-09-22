import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
	DB_DRIVER: str
	DB_HOST: str
	DB_USER: str
	DB_PASSWORD: str
	DB_NAME: str
	DB_PORT: int
	DATABASE_URL: str = f"{DB_DRIVER}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
	
	SECRET_KEY: str = "secret"
	ALGORITHM: str = "HS256"
	ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
	GOOGLE_GEMINI_API_KEY: str

	MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
	MINIO_PUBLIC_ENDPOINT: str = os.getenv("MINIO_PUBLIC_ENDPOINT", "localhost:9000")
	MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
	MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
	MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "uploads")
	MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
	MINIO_API_PORT: int = os.getenv("MINIO_API_PORT", 9000)
	MINIO_CONSOLE_PORT: int = os.getenv("MINIO_CONSOLE_PORT", 9001)

	class Config:
		env_file = ".env"

settings = Settings()
