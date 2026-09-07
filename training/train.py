"""Evaluate on unseen locations, then fit deployment models on the full survey."""
import argparse
import json
from pathlib import Path
import sys
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from backend.preprocess import load_dataset
from training.generate_dataset import generate_dataset


def estimators():
    return {
        "knn": make_pipeline(StandardScaler(), KNeighborsRegressor(n_neighbors=5, weights="distance")),
        "rf": make_pipeline(StandardScaler(), RandomForestRegressor(n_estimators=160, min_samples_leaf=2, random_state=7)),
    }


def train(dataset=ROOT / "data/dataset.csv", output=ROOT / "backend/model.pkl"):
    dataset, output = Path(dataset), Path(output)
    if not dataset.exists():
        generate_dataset(dataset)
    df, aps = load_dataset(dataset)
    x, y = df[aps].to_numpy(), df[["x", "y"]].to_numpy()
    floors = df.floor.to_numpy(dtype=int)
    groups = df.groupby(["x", "y", "floor"]).ngroup().to_numpy()
    # Repeated scans at one location stay together to prevent location leakage.
    train_idx, test_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=7).split(x, y, groups))
    if len(train_idx) < 5 or set(floors[train_idx]) != {1, 2}:
        raise ValueError("Survey needs enough training locations on both floors.")
    metrics = {"scans": len(df), "locations": int(len(np.unique(groups))), "ap_count": len(aps),
               "train_scans": len(train_idx), "test_scans": len(test_idx),
               "evaluation": "25% held-out locations; scaler fitted on training only", "models": {}}
    for name, model in estimators().items():
        model.fit(x[train_idx], y[train_idx])
        pred = model.predict(x[test_idx])
        errors = np.linalg.norm(pred - y[test_idx], axis=1)
        metrics["models"][name] = {"mean_error_m": round(float(errors.mean()), 3),
            "median_error_m": round(float(np.median(errors)), 3),
            "p90_error_m": round(float(np.percentile(errors, 90)), 3),
            "samples": [{"actual": actual.tolist(), "predicted": estimate.round(2).tolist()}
                        for actual, estimate in zip(y[test_idx][:3], pred[:3])]}
    floor_model = make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=5, weights="distance"))
    floor_model.fit(x[train_idx], floors[train_idx])
    metrics["floor_accuracy"] = round(float(np.mean(floor_model.predict(x[test_idx]) == floors[test_idx])), 3)
    # Deployment receives all locations only AFTER evaluation is finalized.
    models = estimators()
    for model in models.values():
        model.fit(x, y)
    floor_model.fit(x, floors)
    output.parent.mkdir(parents=True, exist_ok=True)
    bundle = {"version": 2, "ap_names": aps, "models": models, "floor_model": floor_model, "metrics": metrics}
    joblib.dump(bundle, output)
    output.with_name("metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/dataset.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "backend/model.pkl")
    args = parser.parse_args()
    print(json.dumps(train(args.dataset, args.output), indent=2))
