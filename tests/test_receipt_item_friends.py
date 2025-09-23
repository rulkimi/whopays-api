import os
import sys
from types import SimpleNamespace

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
from app.db.models.friend import Friend
from app.db.models.receipt import Receipt
from app.db.models.item import Item
from app.db.models.item_friend import ItemFriend
from app.db.models.receipt_friend import ReceiptFriend
from app.api.dependencies.database import get_db
from app.api.dependencies.auth import get_current_user


def test_get_receipt_items_friends_grouping():
    # Create isolated in-memory DB and override dependencies
    # Use file-based SQLite so connections share the same database
    db_path = os.path.abspath("test_feature.db")
    if os.path.exists(db_path):
        os.remove(db_path)
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

    # Seed data using the same session provided by override
    with TestingSessionLocal() as db:
        user = User(id=1, email="u@example.com", name="Owner", hashed_password="x")
        db.add(user)
        db.flush()

        r = Receipt(restaurant_name="Cafe", total_amount=100.0, tax=10.0, service_charge=5.0, currency="USD", user_id=1)
        db.add(r)
        db.flush()

        item_a = Item(item_name="Burger", quantity=1, unit_price=10.0, receipt_id=r.id)
        item_b = Item(item_name="Fries", quantity=2, unit_price=5.0, receipt_id=r.id)
        item_c = Item(item_name="Soda", quantity=1, unit_price=3.0, receipt_id=r.id)
        db.add_all([item_a, item_b, item_c])
        db.flush()

        f1 = Friend(name="Alex", user_id=1, photo_url="")
        f2 = Friend(name="Sam", user_id=1, photo_url="")
        db.add_all([f1, f2])
        db.flush()

        # Link friends to receipt (top-level)
        db.add_all([
            ReceiptFriend(receipt_id=r.id, friend_id=f1.id),
            ReceiptFriend(receipt_id=r.id, friend_id=f2.id),
        ])

        # Link friends to items
        db.add_all([
            ItemFriend(item_id=item_a.id, friend_id=f1.id),
            ItemFriend(item_id=item_b.id, friend_id=f2.id),
        ])
        db.commit()

        receipt_id = r.id

    # Call API and validate grouping
    resp = client.get(f"/receipts/{receipt_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    items = {it["item_name"]: it for it in data["items"]}

    assert [f["name"] for f in items["Burger"]["friends"]] == ["Alex"]
    assert [f["name"] for f in items["Fries"]["friends"]] == ["Sam"]
    assert items["Soda"]["friends"] == []

    # Ownership check: non-owner gets 404
    def _override_other_user():
        return SimpleNamespace(id=999)

    app.dependency_overrides[get_current_user] = _override_other_user
    resp2 = client.get(f"/receipts/{receipt_id}")

    # Cleanup DB file
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
    assert resp2.status_code == 404

