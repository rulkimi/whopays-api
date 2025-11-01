from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: int = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_delta or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: int = None):
    """Create a refresh token with longer expiration time (default 7 days)."""
    to_encode = data.copy()
    # Default refresh token expires in 7 days (10080 minutes)
    refresh_expire_minutes = expires_delta or (getattr(settings, 'REFRESH_TOKEN_EXPIRE_MINUTES', 10080))
    expire = datetime.now(timezone.utc) + timedelta(minutes=refresh_expire_minutes)
    to_encode.update({"exp": expire, "type": "refresh"})  # Add type to distinguish refresh tokens
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
