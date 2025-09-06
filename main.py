# app/main.py
from fastapi import FastAPI
from app.api.endpoints import auth, user

app = FastAPI()

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(user.router, prefix="/users", tags=["users"])
