import os
import sys
from types import SimpleNamespace
from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure project root is on sys.path for 'app' imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.db.base_class import Base
from app.db import base as models_import  # noqa: F401 - ensure models are imported
from app.db.models.user import User
from app.api.dependencies.database import get_db
from app.api.dependencies.auth import get_current_user


def test_receipt_upload_returns_job_and_job_get_works():
    # Create isolated file-based SQLite DB so the app and test share state
    db_path = os.path.abspath("test_job.db")
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            pass
    engine = create_engine(f"sqlite:///{db_path}")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    from main import app

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def _override_get_current_user():
        return SimpleNamespace(id=1)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    client = TestClient(app)

    # Seed user
    with TestingSessionLocal() as db:
        user = User(id=1, email="u@example.com", name="Owner", hashed_password="x")
        db.add(user)
        db.commit()

    # Prepare a tiny JPEG-like payload; content doesn't matter, endpoint validates via PIL open
    img_bytes = BytesIO(b"\xff\xd8\xff\xe0fakejpegdata\xff\xd9").getvalue()

    files = {"file": ("r.jpg", BytesIO(img_bytes), "image/jpeg")}
    resp = client.post("/receipts", files=files)
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "job_id" in data

    job_id = data["job_id"]
    # GET job status
    resp2 = client.get(f"/jobs/{job_id}")
    # It can be PENDING or RUNNING depending on timing; just ensure 200
    assert resp2.status_code == 200, resp2.text

    # Cleanup
    try:
        client.close()
    except Exception:
        pass
    try:
        engine.dispose()
    except Exception:
        pass
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            pass
