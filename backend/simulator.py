"""Synthetic radio environment shared by survey collection and fresh mock scans."""
import math
import random

APS = [
    {"id": "AP1", "x": 1, "y": 1, "floor": 1},
    {"id": "AP2", "x": 9, "y": 1, "floor": 1},
    {"id": "AP3", "x": 17, "y": 5, "floor": 1},
    {"id": "AP4", "x": 3, "y": 11, "floor": 1},
    {"id": "AP5", "x": 17, "y": 11, "floor": 2},
    {"id": "AP6", "x": 1, "y": 7, "floor": 2},
    {"id": "AP7", "x": 9, "y": 11, "floor": 2},
    {"id": "AP8", "x": 15, "y": 1, "floor": 2},
]
AP_NAMES = [ap["id"] for ap in APS]


def simulate_scan(x, y, floor, rng=None):
    rng = rng or random.Random()
    signals = {}
    for ap in APS:
        distance = max(1, math.hypot(x - ap["x"], y - ap["y"]))
        value = -32 - 23 * math.log10(distance) - 15 * abs(floor - ap["floor"])
        value = round(max(-90, min(-30, value + rng.gauss(0, 2.2))), 1)
        signals[ap["id"]] = None if rng.random() < 0.035 else value
    return signals
