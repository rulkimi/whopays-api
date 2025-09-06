from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.db.models.user import User
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserRead

router = APIRouter()

@router.post("/register", response_model=UserRead)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
  user = db.query(User).filter(User.email == user_in.email).first()
  if user:
    raise HTTPException(status_code=400, detail="Email already registered")
  
  hashed_password = get_password_hash(user_in.password)
  new_user = User(email=user_in.email, hashed_password=hashed_password)
  db.add(new_user)
  db.commit()
  db.refresh(new_user)
  return new_user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
  user = db.query(User).filter(User.email == form_data.username).first()
  if not user or not verify_password(form_data.password, user.hashed_password):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
  
  token = create_access_token({"sub": str(user.id)})
  return {"access_token": token, "token_type": "bearer"}
