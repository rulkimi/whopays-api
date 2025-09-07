from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.db.base_class import AuditMixin, Base

class User(Base, AuditMixin):
	__tablename__ = "users"

	id = Column(Integer, primary_key=True, index=True)
	email = Column(String, unique=True, index=True, nullable=False)
	name = Column(String, nullable=False)
	hashed_password = Column(String, nullable=False)
	is_active = Column(Boolean, default=True)
	is_superuser = Column(Boolean, default=False)

	friends = relationship("Friend", back_populates="user", cascade="all, delete-orphan")
	receipts = relationship("Receipt", back_populates="user", cascade="all, delete-orphan")