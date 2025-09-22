from sqlalchemy.orm import Session

from app.db.models.user import User
from app.core.security import get_password_hash, verify_password, create_access_token
from app.schemas.user import UserCreate


def register_user(db: Session, user_in: UserCreate) -> User | None:
	"""
	Create a new user if the email is not already registered.

	Returns the created User or None if the email already exists.
	"""
	existing_user = db.query(User).filter(User.email == user_in.email).first()
	if existing_user:
		return None

	hashed_password = get_password_hash(user_in.password)
	new_user = User(
		email=user_in.email,
		name=user_in.name,
		hashed_password=hashed_password,
	)
	db.add(new_user)
	db.commit()
	db.refresh(new_user)
	return new_user


def authenticate_user_and_create_token(db: Session, email: str, password: str) -> str | None:
	"""
	Authenticate a user by email and password.

	Returns an access token string if valid, otherwise None.
	"""
	user = db.query(User).filter(User.email == email).first()
	if not user or not verify_password(password, user.hashed_password):
		return None

	return create_access_token({"sub": str(user.id)})


