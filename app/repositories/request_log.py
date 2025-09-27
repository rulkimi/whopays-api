from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.db.models.request_log import RequestLog


class RequestLogRepository:
	"""Lightweight repository for request/outbound telemetry inserts."""

	def __init__(self, db: Session):
		self.db = db

	def _truncate(self, value: Optional[str], max_len: int) -> Optional[str]:
		if value is None:
			return None
		return value[:max_len]

	def insert_inbound(self, payload: Dict[str, Any]) -> None:
		log = RequestLog(
			direction="inbound",
			connection_type=self._truncate(payload.get("connection_type"), 16),
			correlation_id=self._truncate(payload.get("correlation_id"), 64) or "unknown",
			method=self._truncate(payload.get("method"), 16),
			path_template=self._truncate(payload.get("path_template"), 512),
			raw_path=self._truncate(payload.get("raw_path"), 512),
			route_name=self._truncate(payload.get("route_name"), 128),
			status_code=payload.get("status_code"),
			duration_ms=int(payload.get("duration_ms", 0)),
			client_ip=self._truncate(payload.get("client_ip"), 64),
			user_agent=self._truncate(payload.get("user_agent"), 256),
			auth_type=self._truncate(payload.get("auth_type"), 16),
			user_id=payload.get("user_id"),
		)
		self.db.add(log)
		self.db.commit()

	def insert_outbound(self, payload: Dict[str, Any]) -> None:
		log = RequestLog(
			direction="outbound",
			connection_type=self._truncate(payload.get("connection_type") or "sdk", 16),
			correlation_id=self._truncate(payload.get("correlation_id"), 64) or "unknown",
			status_code=payload.get("status_code"),
			duration_ms=int(payload.get("duration_ms", 0)),
			provider=self._truncate(payload.get("provider"), 64),
			target=self._truncate(payload.get("target"), 256),
			error_code=self._truncate(payload.get("error_code"), 64),
		)
		self.db.add(log)
		self.db.commit()


