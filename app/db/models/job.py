from sqlalchemy import Column, ForeignKey, Integer, String, Text, SmallInteger, DateTime
from sqlalchemy.orm import relationship
from app.db.base_class import AuditMixin, Base


class Job(Base, AuditMixin):
	__tablename__ = "jobs"

	id = Column(Integer, primary_key=True, index=True)
	user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	job_type = Column(String, nullable=False, index=True)  # e.g., RECEIPT_ANALYSIS
	status = Column(String, nullable=False, index=True)  # PENDING, RUNNING, SUCCEEDED, FAILED
	progress = Column(SmallInteger, nullable=False, default=0)
	payload = Column(Text, nullable=True)  # JSON serialized string
	result = Column(Text, nullable=True)   # JSON serialized string
	error_code = Column(String, nullable=True)
	error_message = Column(Text, nullable=True)
	started_at = Column(DateTime(timezone=True), nullable=True)
	finished_at = Column(DateTime(timezone=True), nullable=True)
	receipt_id = Column(Integer, ForeignKey("receipts.id", ondelete="SET NULL"), nullable=True, index=True)

	user = relationship("User", back_populates="jobs")
	receipt = relationship("Receipt")

