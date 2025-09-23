# app/api/endpoints/user.py
from fastapi import Depends
from app.api.router import create_router
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.api.dependencies.auth import get_current_user
from app.db.models.user import User
from app.schemas.user import UserRead

router = create_router(name="user")

@router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
  return current_user
