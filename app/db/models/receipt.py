from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, Float
from sqlalchemy.orm import relationship
from app.db.base_class import AuditMixin, Base

class Receipt(Base, AuditMixin):
	__tablename__ = "receipts"

	id = Column(Integer, primary_key=True, index=True)
	restaurant_name = Column(String, index=True, nullable=False)
	total_amount = Column(Float, nullable=False)
	tax = Column(Float, nullable=False)
	service_charge = Column(Float, nullable=False)
	currency = Column(String, index=True, nullable=False)
	receipt_url = Column(String, index=True, nullable=True)

	user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

	items = relationship("Item", back_populates="receipt", cascade="all, delete-orphan")
	user = relationship("User", back_populates="receipts")
	friends = relationship("ReceiptFriend", back_populates="receipt", cascade="all, delete-orphan")