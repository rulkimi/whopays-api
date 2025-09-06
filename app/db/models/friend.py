from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import AuditMixin, Base

class Friend(Base, AuditMixin):
	__tablename__ = "friends" 

	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(50), nullable=False)
	photo_url = Column(String, index=True)
	user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

	user = relationship("User", back_populates="friends", lazy="select")
	shared_receipts = relationship("ReceiptFriend", back_populates="friend", cascade="all, delete-orphan")
	item_friends = relationship("ItemFriend", back_populates="friend", cascade="all, delete-orphan")