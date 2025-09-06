from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class ReceiptFriend(Base):
  __tablename__ = "receipt_friend"

  receipt_id = Column(Integer, ForeignKey("receipts.id"), primary_key=True)
  friend_id = Column(Integer, ForeignKey("friends.id"), primary_key=True)

  receipt = relationship("Receipt", back_populates="friends")
  friend = relationship("Friend", back_populates="shared_receipts")
