"""Stateless localization API and same-origin React hosting."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
import logging
import os
import joblib
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .map_graph import GRAPH, NODES, map_payload, nearest_node, shortest_path
from .preprocess import signals_to_vector
from .simulator import AP_NAMES, APS, simulate_scan

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "backend/model.pkl"


@asynccontextmanager
async def lifespan(app):
    app.state.bundle = None
    try:
        bundle = joblib.load(MODEL_PATH)
        if bundle.get("version") != 2:
            raise ValueError("Model format changed. Retrain using python -m training.train.")
        app.state.bundle = bundle
    except Exception:
        logging.exception("Model unavailable. Run python -m training.train and restart.")
    yield


app = FastAPI(title="Indoor Navigation", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://127.0.0.1:5180,http://localhost:5180").split(","),
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
api = APIRouter()


class PredictRequest(BaseModel):
    signals: list[float | None] | dict[str, float | None]
    model: Literal["knn", "rf"] = "knn"


class Position(BaseModel):
    x: float = Field(ge=0, le=18, allow_inf_nan=False)
    y: float = Field(ge=0, le=12, allow_inf_nan=False)
    floor: Literal[1, 2] = 1


class RouteRequest(BaseModel):
    destination: str
    current_node: str | None = None
    position: Position | None = None


def get_bundle():
    bundle = getattr(app.state, "bundle", None)
    if bundle is None:
        raise HTTPException(503, "Model unavailable. Run python -m training.train and restart the server.")
    return bundle


@api.get("/health")
def health():
    return {"service": "indoor-navigation", "version": 2,
            "model_ready": getattr(app.state, "bundle", None) is not None}


@api.get("/metadata")
def metadata():
    bundle = get_bundle()
    return {"ap_names": bundle["ap_names"], "metrics": bundle["metrics"],
            "map": map_payload(), "access_points": APS, "missing_rssi": -100}


@api.get("/graph")
def graph():
    return {node: sorted(GRAPH.neighbors(node)) for node in GRAPH}


@api.get("/nodes")
def nodes():
    return list(NODES.values())


@api.post("/predict")
def predict(request: PredictRequest):
    bundle = get_bundle()
    try:
        vector = signals_to_vector(request.signals, bundle["ap_names"])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    xy = bundle["models"][request.model].predict(vector)[0]
    floor = int(bundle["floor_model"].predict(vector)[0])
    x, y = round(float(xy[0]), 2), round(float(xy[1]), 2)
    return {"x": x, "y": y, "floor": floor, "node": nearest_node(x, y, floor), "model": request.model}


@api.get("/scan/mock")
def mock_scan(node: str = "F1_P01"):
    if node not in NODES:
        raise HTTPException(404, "Unknown survey node.")
    point = NODES[node]
    return {"signals": simulate_scan(point["x"], point["y"], point["floor"]),
            "ap_names": AP_NAMES, "expected_location": point, "simulated": True}


@api.post("/route")
def route(request: RouteRequest):
    start = request.current_node
    connector = 0.0
    if request.position is not None:
        pos = request.position
        start = nearest_node(pos.x, pos.y, pos.floor)
        node = NODES[start]
        connector = ((pos.x - node["x"]) ** 2 + (pos.y - node["y"]) ** 2) ** 0.5
    if not start:
        raise HTTPException(422, "Provide current_node or position with x, y, floor.")
    try:
        path, distance = shortest_path(start, request.destination)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    transitions = [{"at": a, "to_floor": NODES[b]["floor"]} for a, b in zip(path, path[1:]) if NODES[a]["floor"] != NODES[b]["floor"]]
    return {"start": start, "destination": request.destination, "path": path,
            "distance_m": round(distance + connector, 2), "connector_m": round(connector, 2),
            "coordinates": [NODES[n] for n in path], "transitions": transitions}


app.include_router(api, prefix="/api")
app.include_router(api, include_in_schema=False)
dist = ROOT / "frontend/dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
