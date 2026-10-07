from fastapi.testclient import TestClient
from backend.api import app
from backend.persistence.service import initialize_database
from backend.persistence.store import RuntimeStore


def test_restarts_restore_same_fixture_and_mira(tmp_path):
    url = "sqlite:///" + str(tmp_path / "runtime.db")
    a = initialize_database(url)
    assert not a["restored_from_previous_process"]
    b = initialize_database(url)
    assert b["restored_from_previous_process"]
    assert a["fixture_sha256"] == b["fixture_sha256"]
    assert b["mira_revision"] == 1


def test_runtime_authorization_and_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "api.db"))
    monkeypatch.setenv("RUNTIME_API_TOKEN", "local-test-only")
    with TestClient(app) as client:
        assert client.get("/health").json()["persistence"] == "ready"
        assert client.get("/runtime/mira").status_code == 401
        assert client.post("/runtime/mira/life").status_code == 401
        before = client.get("/runtime/mira", headers={"Authorization": "Bearer local-test-only"}).json()
    with TestClient(app) as client:
        after = client.get("/runtime/mira", headers={"Authorization": "Bearer local-test-only"}).json()
        assert before == after


def test_runtime_disabled_without_token(monkeypatch):
    monkeypatch.delenv("RUNTIME_API_TOKEN", raising=False)
    with TestClient(app) as client:
        assert client.get("/runtime/mira").status_code == 503
