#!/usr/bin/env python3
"""Production Flask API to add a magnet to Transmission using the local helper.

POST /add  JSON body: { "magnet": "magnet:?xt=...", "media_type": "tv"|"film" }

The API imports the local `rtorrent` module and calls `add_magnet(magnet, tv=...)`.
Run with gunicorn: gunicorn -w 4 -b 0.0.0.0:5000 api:app
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

from flask import Flask, jsonify, request

# Import the local helper module (rtorrent.py)
try:
    from . import rtorrent
except Exception:
    # allow running as a script from the directory
    import rtorrent  # type: ignore

app = Flask(__name__)

# Production-ready logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("rtorrent-api")

# CORS support (optional, if frontend is on different origin)
ENABLE_CORS = os.environ.get("ENABLE_CORS", "false").lower() == "true"
if ENABLE_CORS:
    try:
        from flask_cors import CORS
        CORS(app)
        logger.info("CORS enabled")
    except ImportError:
        logger.warning("flask-cors not installed; CORS disabled")


def _result_ok(data: Dict[str, Any]):
    """Return a successful JSON response."""
    return jsonify({"ok": True, "result": data})


def _result_error(msg: str, code: int = 400):
    """Return an error JSON response."""
    return jsonify({"ok": False, "error": msg}), code


@app.route("/add", methods=["POST"])
def add_magnet_route():
    """Add a torrent magnet link.
    
    Expected JSON: { "magnet": "magnet:?xt=...", "media_type": "tv"|"film" }
    """
    if not request.is_json:
        logger.warning("POST /add received non-JSON request")
        return _result_error("Request body must be JSON", 400)

    body = request.get_json()
    magnet = body.get("magnet")
    media_type = body.get("media_type", "film")  # default to film

    if not magnet or not isinstance(magnet, str):
        logger.warning("POST /add missing or invalid magnet field")
        return _result_error("Missing or invalid 'magnet' field", 400)

    if media_type not in ("tv", "film"):
        logger.warning("POST /add invalid media_type: %s", media_type)
        return _result_error("media_type must be 'tv' or 'film'", 400)

    try:
        tv_flag = media_type == "tv"
        logger.info("Adding magnet (media_type=%s): %s...", media_type, magnet[:80])
        res = rtorrent.add_magnet(magnet, tv=tv_flag)
        logger.info("Magnet added successfully: %s", res)
        return _result_ok(res)
    except Exception as exc:
        logger.exception("Failed to add magnet")
        return _result_error(f"Failed to add magnet: {exc}", 500)

@app.route("/list", methods=["GET"])
def list_torrents():
    """Return the output of `transmission-remote 127.0.0.1:9091 --list` as JSON."""
    import subprocess

    cmd = ["transmission-remote", "127.0.0.1:9091", "--list"]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=10,
        )
        output = result.stdout.strip()

        # Parse Transmission's table output into a list of dicts
        lines = output.splitlines()
        if len(lines) < 2:
            logger.info("No torrents found")
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
            torrents.append(
                {
                    "id": parts[0],
                    "done": parts[1],
                    "have": parts[2],
                    "eta": parts[3],
                    "up": parts[4],
                    "down": parts[5],
                    "ratio": parts[6],
                    "status": parts[7],
                    "name": parts[8],
                }
            )

        logger.info("Listed %d torrents", len(torrents))
        return _result_ok({"torrents": torrents})

    except subprocess.TimeoutExpired:
        logger.error("transmission-remote --list timed out")
        return _result_error("Request timed out", 504)
    except subprocess.CalledProcessError as e:
        logger.error("transmission-remote --list failed: %s", e.stderr)
        return _result_error(f"Command failed: {e.stderr.strip()}", 500)
    except FileNotFoundError:
        logger.error("transmission-remote not found in PATH")
        return _result_error(
            "transmission-remote not found; install Transmission CLI tools", 500
        )
    except Exception as e:
        logger.exception("Unexpected error in /list")
        return _result_error(f"Unexpected error: {e}", 500)

@app.route("/ping", methods=["GET"])
def ping():
    """Health check endpoint."""
    return jsonify({"ok": True, "msg": "rtorrent-webclient API running"})


if __name__ == "__main__":
    # When run directly, use Flask dev server (not for production)
    app.run(host="0.0.0.0", port=5000, debug=False)
