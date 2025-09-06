from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, Float
from sqlalchemy.orm import relationship
from app.db.base_class import AuditMixin, Base

class Variation(Base, AuditMixin):
	__tablename__ = "variations"

	id = Column(Integer, primary_key=True, index=True)
	variation_name = Column(String, nullable=False)
	price = Column(Float, nullable=False)

	item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)

	item = relationship("Item", back_populates="variations")