from sqlalchemy import Column, ForeignKey, Integer, Boolean
from sqlalchemy.orm import relationship
from app.db.base_class import AuditMixin, Base

class ItemFriend(Base, AuditMixin):
	__tablename__ = "item_friends"

	id = Column(Integer, primary_key=True, index=True)
	item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
	friend_id = Column(Integer, ForeignKey("friends.id", ondelete="CASCADE"), nullable=False, index=True)

	item = relationship("Item", back_populates="item_friends")
	friend = relationship("Friend", back_populates="item_friends")
