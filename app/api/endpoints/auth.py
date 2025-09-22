from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserRead
from app.services import auth_services

router = APIRouter()

@router.post("/register", response_model=UserRead)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> UserRead:
	"""Register a new user if the email is not already taken."""
	user = auth_services.register_user(db, user_in)
	if user is None:
		raise HTTPException(status_code=400, detail="Email already registered")
	return user

@router.post("/login", response_model=Token)
def login(
  form_data: OAuth2PasswordRequestForm = Depends(),
  db: Session = Depends(get_db),
) -> Token:
  """Authenticate the user and return an access token."""
  token = auth_services.authenticate_user_and_create_token(
    db, form_data.username, form_data.password
  )
  if token is None:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
  return {"access_token": token, "token_type": "bearer"}
