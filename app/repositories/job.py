"""Job repository for job-related database operations."""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository
from app.db.models.job import Job


class JobRepository(BaseRepository[Job]):
	"""Repository for Job entity operations."""

	def __init__(self, db: Session, correlation_id: Optional[str] = None):
		super().__init__(db, Job, correlation_id)

	def get_by_id_and_user(self, job_id: int, user_id: int) -> Optional[Job]:
		"""Get job by ID ensuring ownership by user."""
		result = self.db.query(self.model).filter(
			self.model.id == job_id,
			self.model.user_id == user_id,
			self.model.is_deleted == False
		).first()
		self._log_operation("get_by_id_and_user", job_id=job_id, user_id=user_id, found=result is not None)
		return result

	def update_fields(self, job_id: int, fields: Dict[str, Any]) -> Optional[Job]:
		"""Update arbitrary job fields and return the job."""
		job = self.get_by_id(job_id)
		if not job:
			return None
		for k, v in fields.items():
			if hasattr(job, k):
				setattr(job, k, v)
		self.db.flush()
		self.db.refresh(job)
		self._log_operation("update_fields", job_id=job_id, fields=list(fields.keys()))
		return job


