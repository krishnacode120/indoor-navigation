"""One compact workflow check; run after training. Requires httpx."""
from fastapi.testclient import TestClient
from backend.main import app


def main():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["model_ready"]
        metadata = client.get("/api/metadata").json()
        assert metadata["metrics"]["locations"] == 80
        signals = [-45, -60, -70, -80, -55, -67, -73, -64]
        prediction = client.post("/api/predict", json={"signals": signals})
        assert prediction.status_code == 200, prediction.text
        point = prediction.json()
        route = client.post("/api/route", json={"position": {k: point[k] for k in ("x", "y", "floor")}, "destination": "F2_P20"})
        assert route.status_code == 200, route.text
        assert route.json()["path"][-1] == "F2_P20"
        assert client.post("/api/predict", json={"signals": []}).status_code == 422
        print("PASS: model, metadata, prediction, routing, empty-scan rejection")


if __name__ == "__main__":
    main()
