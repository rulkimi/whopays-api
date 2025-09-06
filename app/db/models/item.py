from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, Float
from sqlalchemy.orm import relationship
from app.db.base_class import AuditMixin, Base

class Item(Base, AuditMixin):
	__tablename__ = "items"

	id = Column(Integer, primary_key=True, index=True)
	item_name = Column(String, nullable=False)
	quantity = Column(Integer, nullable=False)
	unit_price = Column(Float, nullable=False)

	receipt_id = Column(Integer, ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False, index=True)

	variations = relationship("Variation", back_populates="item")
	receipt = relationship("Receipt", back_populates="items")
	item_friends = relationship("ItemFriend", back_populates="item", cascade="all, delete-orphan")