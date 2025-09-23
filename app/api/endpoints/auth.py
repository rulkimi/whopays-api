from fastapi import Depends, HTTPException, status
from app.api.router import create_router
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.api.dependencies.services import get_auth_service
from app.schemas.auth import Token, UserLogin
from app.schemas.user import UserCreate, UserRead
from app.services.auth_services import AuthService

router = create_router(name="auth")

@router.post("/register", response_model=UserRead)
def register(
    user_in: UserCreate, 
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserRead:
	"""Register a new user if the email is not already taken."""
	registration_result = auth_service.register_user(user_in, db)
	if not registration_result.success:
		raise HTTPException(
			status_code=400, 
			detail=registration_result.message or "Registration failed"
		)
	
	# Need to fetch the created user to return UserRead
	# For now, we'll need to get the user from the repository
	# This is a temporary solution - ideally the service should return the user data
	from app.repositories.user import UserRepository
	user_repo = UserRepository(db)
	user = user_repo.get_by_id(registration_result.user_id)
	return user

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
) -> Token:
    """Authenticate user and return access token."""
    login_data = UserLogin(email=form_data.username, password=form_data.password)
    auth_result = auth_service.authenticate_user_and_create_token(login_data)
    
    if not auth_result.success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=auth_result.message or "Invalid credentials"
        )
    
    return auth_result.token
