from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import AuditMixin, Base

class Friend(Base, AuditMixin):
	__tablename__ = "friends" 

	id = Column(Integer, primary_key=True, index=True)
	photo_url = Column(String, index=True)
	user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

	user = relationship("User", back_populates="friends")