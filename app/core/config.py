import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
	# Accept a direct URL (supports either DATABASE_URL or database_url env vars)
	database_url: str | None = None

	# Individual parts with sensible local defaults so dev can boot without .env
	DB_DRIVER: str 
	DB_HOST: str 
	DB_USER: str 
	DB_PASSWORD: str
	DB_NAME: str 
	DB_PORT: int
	# DATABASE_URL is computed via property below to avoid referencing annotated fields in class body
	
	SECRET_KEY: str = "secret"
	ALGORITHM: str = "HS256"
	ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
	GOOGLE_GEMINI_API_KEY: str | None = None

	# Observability / Telemetry flags
	ENABLE_REQUEST_LOGGING: bool = True
	ENABLE_OUTBOUND_LOGGING: bool = True
	LOG_SAMPLE_RATE: float = 1.0
	ENABLE_PROMETHEUS: bool = False

	MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
	MINIO_PUBLIC_ENDPOINT: str = os.getenv("MINIO_PUBLIC_ENDPOINT", "localhost:9000")
	MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
	MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
	MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "uploads")
	MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
	MINIO_API_PORT: int = int(os.getenv("MINIO_API_PORT", 9000))
	MINIO_CONSOLE_PORT: int = int(os.getenv("MINIO_CONSOLE_PORT", 9001))

	# Prefer explicit database_url if provided; otherwise assemble from parts
	@property
	def DATABASE_URL(self) -> str:
		# 1) Value from settings (supports .env and OS env via BaseSettings)
		if self.database_url and self.database_url.strip() and self.database_url.strip() != "://:@:/":
			return self.database_url.strip()
		# 2) Raw OS env (e.g., uppercase on Windows), as a fallback
		explicit_url = os.getenv("DATABASE_URL")
		if explicit_url and explicit_url.strip() and explicit_url.strip() != "://:@:/":
			return explicit_url.strip()
		# 3) Assemble from parts
		return f"{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

	# Pydantic v2 settings config
	model_config = SettingsConfigDict(
		env_file=".env",
		extra="ignore",  # tolerate unrelated env vars like database_url
		case_sensitive=False,  # accept lowercase keys on Windows and in .env
	)

settings = Settings()
