"""Serve the built app and API on one free loopback port."""
import argparse
from pathlib import Path
import socket
import uvicorn

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    if not (ROOT / "frontend/dist/index.html").exists() or not (ROOT / "backend/model.pkl").exists():
        raise SystemExit("Build and train first: see README.md or run start.ps1.")
    # Reserve the chosen socket, avoiding a check-then-bind race and wrong-app URLs.
    for port in range(args.port, min(args.port + 20, 65536)):
        sock = socket.socket()
        try:
            sock.bind(("127.0.0.1", port))
            break
        except OSError:
            sock.close()
    else:
        raise SystemExit("No free port. Run python run.py --port 9000.")
    print(f"Indoor Navigation: http://127.0.0.1:{port}", flush=True)
    server = uvicorn.Server(uvicorn.Config("backend.main:app", host="127.0.0.1", port=port))
    try:
        server.run(sockets=[sock])
    finally:
        sock.close()


if __name__ == "__main__":
    main()
