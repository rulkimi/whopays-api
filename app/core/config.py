from pydantic_settings import BaseSettings

class Settings(BaseSettings):
	DATABASE_URL: str
	SECRET_KEY: str = "secret"
	ALGORITHM: str = "HS256"
	ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
	GOOGLE_GEMINI_API_KEY: str

	class Config:
		env_file = ".env"

settings = Settings()
