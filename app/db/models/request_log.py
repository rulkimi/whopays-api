from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.db.base_class import Base


class RequestLog(Base):
	__tablename__ = "request_logs"

	id = Column(Integer, primary_key=True, index=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
	correlation_id = Column(String(64), nullable=False, index=True)
	direction = Column(String(16), nullable=False, default="inbound")
	connection_type = Column(String(16), nullable=True)
	method = Column(String(16), nullable=True)
	path_template = Column(String(512), nullable=True, index=True)
	raw_path = Column(String(512), nullable=True)
	route_name = Column(String(128), nullable=True)
	status_code = Column(Integer, nullable=True, index=True)
	duration_ms = Column(Integer, nullable=False)
	client_ip = Column(String(64), nullable=True)
	user_agent = Column(String(256), nullable=True)
	auth_type = Column(String(16), nullable=True)
	user_id = Column(Integer, nullable=True, index=True)
	provider = Column(String(64), nullable=True, index=True)
	target = Column(String(256), nullable=True, index=True)
	error_code = Column(String(64), nullable=True)


