from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.services.base import BaseService
from app.services.exceptions import ValidationError, BusinessError
from app.repositories.job import JobRepository
from app.db.models.job import Job
from app.schemas.job import JobType, JobStatus


class JobService(BaseService):
	def __init__(self, job_repo: JobRepository, correlation_id: Optional[str] = None):
		super().__init__(correlation_id)
		self._set_repositories(job_repo=job_repo)

	def create_job(self, user_id: int, job_type: JobType, payload: Optional[Dict[str, Any]], db: Session) -> Job:
		def op():
			return self.job_repo.create({
				"user_id": user_id,
				"job_type": job_type.value,
				"status": JobStatus.PENDING.value,
				"progress": 0,
				"payload": None if payload is None else __import__('json').dumps(payload)
			})
		return self.run_in_transaction(db, op)

	def start(self, job_id: int, db: Session) -> Optional[Job]:
		return self._set_status(job_id, JobStatus.RUNNING, db, progress=10, started_at=datetime.now(timezone.utc))

	def progress(self, job_id: int, p: int, db: Session) -> Optional[Job]:
		clamped = max(0, min(100, p))
		return self._set_status(job_id, None, db, progress=clamped)

	def succeed(self, job_id: int, receipt_id: int, db: Session) -> Optional[Job]:
		return self._set_status(job_id, JobStatus.SUCCEEDED, db, progress=100, receipt_id=receipt_id, finished_at=datetime.now(timezone.utc))

	def fail(self, job_id: int, code: str, message: str, db: Session) -> Optional[Job]:
		return self._set_status(job_id, JobStatus.FAILED, db, error_code=code, error_message=message, finished_at=datetime.now(timezone.utc))

	def get_owned(self, job_id: int, user_id: int) -> Optional[Job]:
		return self.job_repo.get_by_id_and_user(job_id, user_id)

	def _set_status(
		self,
		job_id: int,
		status: Optional[JobStatus],
		db: Session,
		*,  # flexible fields
		progress: Optional[int] = None,
		receipt_id: Optional[int] = None,
		error_code: Optional[str] = None,
		error_message: Optional[str] = None,
		started_at: Optional[datetime] = None,
		finished_at: Optional[datetime] = None,
	) -> Optional[Job]:
		def op():
			fields: Dict[str, Any] = {}
			if status is not None:
				fields["status"] = status.value
			if progress is not None:
				fields["progress"] = max(0, min(100, progress))
			if receipt_id is not None:
				fields["receipt_id"] = receipt_id
			if error_code is not None:
				fields["error_code"] = error_code
			if error_message is not None:
				fields["error_message"] = error_message
			if started_at is not None:
				fields["started_at"] = started_at
			if finished_at is not None:
				fields["finished_at"] = finished_at
			return self.job_repo.update_fields(job_id, fields)
		return self.run_in_transaction(db, op)


