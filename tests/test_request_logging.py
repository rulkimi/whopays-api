import os
import sys

from fastapi.testclient import TestClient

# Ensure project root on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def test_correlation_id_header_present_on_404():
    from main import app

    client = TestClient(app)

    resp = client.get("/this-path-does-not-exist")
    assert resp.status_code == 404
    assert "X-Correlation-ID" in resp.headers

    try:
        client.close()
    except Exception:
        pass


