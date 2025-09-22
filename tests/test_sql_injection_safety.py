import os
from types import SimpleNamespace

from fastapi.testclient import TestClient

# Ensure required env vars are present for app settings on import
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DB_DRIVER", "sqlite")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USER", "user")
os.environ.setdefault("DB_PASSWORD", "password")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_PORT", "5432")

from main import app
from app.api.dependencies.auth import get_current_user


def _override_get_current_user():
    return SimpleNamespace(id=1)


app.dependency_overrides[get_current_user] = _override_get_current_user

client = TestClient(app)


def test_receipt_id_path_injection_returns_422():
    # Path param expects int; injection-like string should fail validation
    resp = client.get("/receipts/1 OR 1=1")
    assert resp.status_code == 422


def test_friend_id_path_injection_returns_422():
    resp = client.delete("/friends/1; DROP TABLE users;--")
    assert resp.status_code == 422


def test_receipts_query_params_injection_returns_422():
    # skip and limit are ints; injection-like strings should fail
    resp = client.get("/receipts?skip=0; DROP TABLE receipts;--&limit=100")
    assert resp.status_code == 422


def test_body_injection_on_items_add_friends_returns_422():
    # Body model expects ints and List[int]
    payload = {
        "item_id": "1 OR 1=1",
        "friend_ids": ["2 OR 2=2"]
    }
    resp = client.post("/items/add-friends", json=payload)
    assert resp.status_code == 422


