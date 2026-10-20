from fastapi.testclient import TestClient

from browser_agent import storage
from browser_agent.api import app


def test_health_home_and_static_assets(tmp_path, monkeypatch):
    monkeypatch.setattr(storage.settings, "data_dir", str(tmp_path))

    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        home = client.get("/")
        assert home.status_code == 200
        assert "Let the browser" in home.text
        assert client.get("/static/app.js").status_code == 200


def test_run_input_validation_happens_before_browser_call(tmp_path, monkeypatch):
    monkeypatch.setattr(storage.settings, "data_dir", str(tmp_path))

    with TestClient(app) as client:
        response = client.post(
            "/runs",
            json={"start_url": "file:///etc/passwd", "goal": "Read this local file"},
        )
        assert response.status_code == 422
