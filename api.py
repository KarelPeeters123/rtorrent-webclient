#!/usr/bin/env python3
"""Small Flask API to add a magnet to Transmission using the local helper.

POST /add  JSON body: { "magnet": "magnet:?xt=...", "tv": true|false }

The API imports the local `rtorrent` module and calls `add_magnet(magnet, tv=...)`.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from flask import Flask, jsonify, request

# Import the local helper module (rtorrent.py)
try:
    from . import rtorrent
except Exception:
    # allow running as a script from the directory
    import rtorrent  # type: ignore

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rtorrent-api")


def _result_ok(data: Dict[str, Any]):
    return jsonify({"ok": True, "result": data})


def _result_error(msg: str, code: int = 400):
    return jsonify({"ok": False, "error": msg}), code


@app.route("/add", methods=["POST"])
def add_magnet_route():
    if not request.is_json:
        return _result_error("Request body must be JSON", 400)

    body = request.get_json()
    magnet = body.get("magnet")
    media_type = body.get("media_type", "tv")

    if not magnet or not isinstance(magnet, str):
        return _result_error("Missing or invalid 'magnet' field", 400)

    try:
        logger.info("Adding magnet (tv=%s): %s", media_type, magnet)
        tv_flag = media_type == "tv"
        res = rtorrent.add_magnet(magnet, tv=tv_flag)
        return _result_ok(res)
    except Exception as exc:  # pragma: no cover - bubble runtime errors to client
        logger.exception("Failed to add magnet")
        return _result_error(f"Failed to add magnet: {exc}", 500)

@app.route("/list", methods=["GET"])
def list_torrents():
    """Return the output of `transmission-remote 127.0.0.1:9091 --list` as JSON."""
    import subprocess
    import shlex

    cmd = ["transmission-remote", "127.0.0.1:9091", "--list"]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        output = result.stdout.strip()

        # Parse Transmission's table output into a list of dicts
        lines = output.splitlines()
        if len(lines) < 2:
            return _result_ok({"torrents": [], "raw": output})

        header = lines[0]
        body = lines[1:-1]  # skip the summary line
        torrents = []

        for line in body:
            # Transmission's columns look like:
            # ID   Done       Have  ETA           Up    Down  Ratio  Status       Name
            # 1*   100%       1.05 GB  Done         0.0   0.0   0.00  Idle         Example.torrent
            parts = line.split(None, 8)
            if len(parts) < 9:
                continue
            torrents.append({
                "id": parts[0],
                "done": parts[1],
                "have": parts[2],
                "eta": parts[3],
                "up": parts[4],
                "down": parts[5],
                "ratio": parts[6],
                "status": parts[7],
                "name": parts[8],
            })

        return _result_ok({"torrents": torrents})

    except subprocess.CalledProcessError as e:
        return _result_error(f"Command failed: {e.stderr.strip()}", 500)
    except FileNotFoundError:
        return _result_error("transmission-remote not found; install Transmission CLI tools", 500)
    except Exception as e:
        return _result_error(f"Unexpected error: {e}", 500)

@app.route("/ping", methods=["GET"])
def index():
    return jsonify({"ok": True, "msg": "rtorrent-webclient API running"})

@app.route("/")
def serve_ui():
    return app.send_static_file("index.html")

if __name__ == "__main__":
    # Default host/port; use a process manager in production
    app.run(host="0.0.0.0", port=5000)
