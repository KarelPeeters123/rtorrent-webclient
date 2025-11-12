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
    tv = body.get("tv", False)

    if not magnet or not isinstance(magnet, str):
        return _result_error("Missing or invalid 'magnet' field", 400)

    try:
        tv_flag = bool(tv)
        logger.info("Adding magnet (tv=%s): %s", tv_flag, magnet)
        res = rtorrent.add_magnet(magnet, tv=tv_flag)
        return _result_ok(res)
    except Exception as exc:  # pragma: no cover - bubble runtime errors to client
        logger.exception("Failed to add magnet")
        return _result_error(f"Failed to add magnet: {exc}", 500)


@app.route("/", methods=["GET"])
def index():
    return jsonify({"ok": True, "msg": "rtorrent-webclient API running"})


if __name__ == "__main__":
    # Default host/port; use a process manager in production
    app.run(host="0.0.0.0", port=5000)
