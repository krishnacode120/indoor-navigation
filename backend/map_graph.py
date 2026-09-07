"""An open teaching-floor grid with two stair connections. Units are meters."""
import math
import networkx as nx

WIDTH, HEIGHT = 18, 12
NODES = {}
GRAPH = nx.Graph()
LANDMARKS = {1: "Reception", 5: "Lecture hall", 8: "East stairs", 13: "West stairs", 16: "Library", 20: "Computer lab"}
for floor in (1, 2):
    for row in range(4):
        for col in range(5):
            number = row * 5 + col + 1
            node_id = f"F{floor}_P{number:02d}"
            label = LANDMARKS.get(number, f"Waypoint {number:02d}")
            NODES[node_id] = dict(id=node_id, x=col * 4.5, y=row * 4, floor=floor,
                                  label=f"{label} / F{floor}", stairs=number in (8, 13))
            GRAPH.add_node(node_id)
    for row in range(4):
        for col in range(5):
            number = row * 5 + col + 1
            source = f"F{floor}_P{number:02d}"
            if col < 4:
                GRAPH.add_edge(source, f"F{floor}_P{number + 1:02d}", weight=4.5)
            if row < 3:
                GRAPH.add_edge(source, f"F{floor}_P{number + 5:02d}", weight=4)
for number in (8, 13):
    GRAPH.add_edge(f"F1_P{number:02d}", f"F2_P{number:02d}", weight=8)


def nearest_node(x, y, floor):
    candidates = [n for n in NODES.values() if n["floor"] == floor]
    if not candidates:
        raise ValueError("Unknown floor.")
    return min(candidates, key=lambda n: math.hypot(x - n["x"], y - n["y"]))["id"]


def shortest_path(start, destination):
    if start not in NODES or destination not in NODES:
        raise ValueError("Unknown start or destination node.")
    path = nx.dijkstra_path(GRAPH, start, destination, weight="weight")
    return path, nx.path_weight(GRAPH, path, weight="weight")


def map_payload():
    return {"width": WIDTH, "height": HEIGHT, "floors": [1, 2], "nodes": list(NODES.values()),
            "edges": [{"start": a, "end": b, "distance_m": d["weight"]} for a, b, d in GRAPH.edges(data=True)]}
