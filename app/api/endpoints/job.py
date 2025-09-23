from fastapi import Depends, HTTPException, WebSocket, WebSocketDisconnect
import asyncio
from app.api.router import create_router
from sqlalchemy.orm import Session
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.api.dependencies.services import get_job_service
from app.services.job_services import JobService
from app.schemas.job import JobRead
from app.db.models.user import User
from app.repositories.job import JobRepository


router = create_router(name="job")


@router.get("/{job_id}", response_model=JobRead)
def get_job_status(
	job_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
	job_service: JobService = Depends(get_job_service),
):
	job = job_service.get_owned(job_id, current_user.id)
	if not job:
		raise HTTPException(status_code=404, detail="Job not found")
	return job


@router.websocket("/ws/{job_id}")
async def job_status_ws(
	websocket: WebSocket,
	job_id: int,
	db: Session = Depends(get_db)
):
	try:
		await websocket.accept()
		# Simple token auth: query param ?token=Bearer <jwt> or Authorization header
		token = websocket.query_params.get("token") or websocket.headers.get("authorization")
		if not token:
			await websocket.send_json({"event": "unauthorized"})
			await websocket.close(code=4401)
			return
		# Build service instances locally to avoid HTTP-only dependencies
		job_service = JobService(job_repo=JobRepository(db=db), correlation_id=None)
		# We do a lightweight poll loop; replace with pub/sub if available
		last_payload = None
		while True:
			# Ensure session doesn't serve stale cached objects
			db.expire_all()
			job = job_service.job_repo.get_by_id(job_id)
			if not job or job.is_deleted:
				await websocket.send_json({"event": "not_found"})
				await websocket.close()
				return
			payload = {
				"id": job.id,
				"status": job.status,
				"progress": job.progress,
				"error_code": job.error_code,
				"error_message": job.error_message,
				"receipt_id": job.receipt_id,
			}
			if payload != last_payload:
				await websocket.send_json({"event": "update", "data": payload})
				last_payload = payload
			# Exit when terminal state
			if job.status in ("SUCCEEDED", "FAILED"):
				await websocket.close()
				return
			await asyncio.sleep(1.0)
	except WebSocketDisconnect:
		return


