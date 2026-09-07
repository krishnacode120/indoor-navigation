"""Shared AP ordering and missing-signal policy for training and inference."""
import numpy as np
import pandas as pd

MISSING_RSSI = -100.0


def load_dataset(path):
    df = pd.read_csv(path)
    if not {"x", "y", "floor"}.issubset(df.columns):
        raise ValueError("CSV must include x, y, floor and AP columns.")
    aps = sorted(c for c in df if c.startswith("AP"))
    if len(aps) < 3:
        raise ValueError("At least three AP columns are required.")
    labels = df[["x", "y", "floor"]].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(labels.to_numpy()).all():
        raise ValueError("Location labels must be finite.")
    if not labels.floor.isin([1, 2]).all():
        raise ValueError("This building supports floors 1 and 2.")
    if not labels.x.between(0, 18).all() or not labels.y.between(0, 12).all():
        raise ValueError("Coordinates must lie within the 18 x 12 meter map.")
    features = df[aps].apply(pd.to_numeric, errors="raise").fillna(MISSING_RSSI)
    if not np.isfinite(features.to_numpy()).all() or not ((features >= -100) & (features <= 0)).all().all():
        raise ValueError("RSSI readings must be between -100 and 0 dBm.")
    df[aps] = features
    df[["x", "y", "floor"]] = labels
    return df, aps


def signals_to_vector(signals, aps):
    if isinstance(signals, dict):
        unknown = set(signals) - set(aps)
        if unknown:
            raise ValueError(f"Unknown AP names: {', '.join(sorted(unknown))}")
        values = [signals.get(ap) for ap in aps]
    else:
        if len(signals) > len(aps):
            raise ValueError(f"Expected at most {len(aps)} readings in /metadata AP order.")
        values = list(signals) + [None] * (len(aps) - len(signals))
    vector = np.array([MISSING_RSSI if v is None else v for v in values], dtype=float)
    if not np.isfinite(vector).all() or ((vector < -100) | (vector > 0)).any():
        raise ValueError("RSSI must be finite and between -100 and 0 dBm.")
    if np.count_nonzero(vector > MISSING_RSSI) < 3:
        raise ValueError("At least three detected APs are needed to locate reliably.")
    return vector.reshape(1, -1)
