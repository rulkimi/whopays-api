from __future__ import annotations

import time
import uuid
from typing import Callable, Optional, Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.background import BackgroundTask

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.request_log import RequestLogRepository


def generate_correlation_id(existing: Optional[str]) -> str:
	if existing and existing.strip():
		return existing.strip()
	return str(uuid.uuid4())


class RequestLoggingMiddleware(BaseHTTPMiddleware):
	"""Middleware to log inbound HTTP requests with correlation IDs."""

	async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
		if not settings.ENABLE_REQUEST_LOGGING:
			return await call_next(request)

		try:
			from random import random
			sampled_out = (settings.LOG_SAMPLE_RATE < 1.0) and (random() > float(settings.LOG_SAMPLE_RATE))
		except Exception:
			sampled_out = False

		correlation_id = generate_correlation_id(request.headers.get("X-Correlation-ID"))
		setattr(request.state, "correlation_id", correlation_id)

		start_ns = time.monotonic_ns()
		status_code: int = 500
		response: Optional[Response] = None

		try:
			response = await call_next(request)
			status_code = response.status_code
		except Exception:
			from starlette.responses import JSONResponse
			response = JSONResponse({"detail": "Internal Server Error"}, status_code=500)
			raise
		finally:
			duration_ms = int((time.monotonic_ns() - start_ns) / 1_000_000)

			if response is not None:
				response.headers["X-Correlation-ID"] = correlation_id

				if not sampled_out:
					payload = _build_inbound_payload(request, correlation_id, status_code, duration_ms)
					response.background = BackgroundTask(_insert_inbound, payload)

		return response


def _build_inbound_payload(request: Request, correlation_id: str, status_code: int, duration_ms: int) -> dict:
	# Route template and name may be unavailable for 404 or early errors
	path_template = None
	route_name = None
	try:
		if request.scope.get("route") is not None:
			path_template = getattr(request.scope["route"], "path", None)
			endpoint = request.scope.get("endpoint")
			route_name = getattr(endpoint, "__name__", None)
	except Exception:
		pass

	# Client IP determination (basic)
	xff = request.headers.get("x-forwarded-for")
	client_ip = (xff.split(",")[0].strip() if xff else (request.client.host if request.client else None))

	auth_header = request.headers.get("authorization") or ""
	auth_type = "bearer" if auth_header.lower().startswith("bearer ") else ("basic" if auth_header.lower().startswith("basic ") else "none")

	return {
		"correlation_id": correlation_id,
		"connection_type": "http",
		"method": request.method,
		"raw_path": request.url.path,
		"path_template": path_template or request.url.path,
		"route_name": route_name,
		"status_code": status_code,
		"duration_ms": duration_ms,
		"client_ip": client_ip,
		"user_agent": (request.headers.get("user-agent") or "")[:256],
		"auth_type": auth_type,
		"user_id": None,
	}


def _insert_inbound(payload: dict) -> None:
	try:
		db = SessionLocal()
		repo = RequestLogRepository(db)
		repo.insert_inbound(payload)
	except Exception:
		# Swallow to avoid impacting request path
		pass
	finally:
		try:
			db.close()
		except Exception:
			pass


def log_outbound_call(provider: str, target: str, operation: str, correlation_id: Optional[str], call: Callable[[], Any]) -> Any:
	"""Execute outbound call and log duration in background.

	Args:
		provider: External provider name (e.g., gemini, minio)
		target: Target entity (e.g., model name, object key)
		operation: Operation name
		correlation_id: Correlation ID for linkage
		call: Callable that performs the operation

	Returns:
		Result of `call()`
	"""
	if not settings.ENABLE_OUTBOUND_LOGGING:
		return call()

	start_ns = time.monotonic_ns()
	error_code: Optional[str] = None
	try:
		result = call()
		return result
	except Exception as e:
		error_code = type(e).__name__
		raise
	finally:
		duration_ms = int((time.monotonic_ns() - start_ns) / 1_000_000)
		payload = {
			"correlation_id": correlation_id or str(uuid.uuid4()),
			"connection_type": "sdk",
			"provider": provider,
			"target": target,
			"duration_ms": duration_ms,
			"error_code": error_code,
		}
		# Insert asynchronously
		try:
			db = SessionLocal()
			repo = RequestLogRepository(db)
			repo.insert_outbound(payload)
		except Exception:
			pass
		finally:
			try:
				db.close()
			except Exception:
				pass


