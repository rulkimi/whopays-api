# app/main.py
from fastapi import FastAPI
from app.api.endpoints import auth, user, ai, friend, receipt
# Import all models to ensure relationships are properly resolved
from app.db import base  # This imports all models

app = FastAPI()

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(user.router, prefix="/users", tags=["users"])
app.include_router(friend.router, prefix="/friends", tags=["friends"])
app.include_router(receipt.router, prefix="/receipts", tags=["receipts"])

app.include_router(ai.router, prefix="/ai", tags=["playground"])