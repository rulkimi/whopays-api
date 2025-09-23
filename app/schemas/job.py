from __future__ import annotations

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from .mixin import TimestampModel


class JobType(str, Enum):
	RECEIPT_ANALYSIS = "RECEIPT_ANALYSIS"


class JobStatus(str, Enum):
	PENDING = "PENDING"
	RUNNING = "RUNNING"
	SUCCEEDED = "SUCCEEDED"
	FAILED = "FAILED"


class JobCreate(BaseModel):
	user_id: int
	job_type: JobType
	payload: Optional[Dict[str, Any]] = Field(default=None)


class JobRead(TimestampModel):
	id: int
	job_type: JobType
	status: JobStatus
	progress: int = Field(ge=0, le=100)
	receipt_id: Optional[int] = None
	error_code: Optional[str] = None
	error_message: Optional[str] = None
	started_at: Optional[str] = None
	finished_at: Optional[str] = None

	class Config:
		from_attributes = True

	@validator('progress')
	def validate_progress(cls, v: int) -> int:
		if v < 0:
			return 0
		if v > 100:
			return 100
		return v


