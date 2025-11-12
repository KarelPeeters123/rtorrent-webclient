#!/usr/bin/env python3
"""Minimal Transmission helper for adding magnet links.

This implements Option A (Transmission) from the interactive discussion.

Usage:
    - CLI: python rtorrent.py add "magnet:?xt=..."
    - Programmatic: from rtorrent import add_magnet; add_magnet(magnet)

Behavior:
  - Try to use the Python library `transmission-rpc` (if installed) to add the torrent
    via Transmission's RPC (default host 127.0.0.1:9091).
  - If the library is not available, fall back to calling the `transmission-remote`
    CLI (must be installed and in PATH).

Configuration via environment variables:
  - TRANSMISSION_HOST (default: 127.0.0.1)
  - TRANSMISSION_PORT (default: 9091)
  - TRANSMISSION_USER
  - TRANSMISSION_PASS

This file purposefully keeps dependencies optional and falls back to the CLI for
maximum out-of-the-box compatibility.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from typing import Optional


def _get_config():
    return {
        "host": os.environ.get("TRANSMISSION_HOST", "127.0.0.1"),
        "port": int(os.environ.get("TRANSMISSION_PORT", "9091")),
        "user": os.environ.get("TRANSMISSION_USER") or None,
        "password": os.environ.get("TRANSMISSION_PASS") or None,
    }


# Fixed download directory used for all torrents
DOWNLOAD_DIR = os.environ.get("TRANSMISSION_DOWNLOAD_DIR", "/var/lib/transmission-daemon/downloads")


def add_magnet_transmission_rpc(magnet: str, host: str, port: int, user: Optional[str], password: Optional[str], download_dir: str):
    """Add magnet using transmission-rpc library. Raises ImportError if lib missing.
    Uses the provided download_dir.
    Returns the id or added Torrent object depending on the library.
    """
    try:
        import transmission_rpc
    except Exception as exc:
        raise ImportError("transmission-rpc library not available") from exc

    client = transmission_rpc.Client(host=host, port=port, username=user, password=password)
    # transmission-rpc's add_torrent accepts a uri and optional download_dir
    # It returns a Torrent or list of Torrents depending on the version.
    torr = client.add_torrent(magnet, download_dir=download_dir)
    return torr


def add_magnet_transmission_cli(magnet: str, download_dir: str):
    """Add magnet using transmission-remote CLI. Requires transmission-remote in PATH.
    Uses the provided download_dir. Returns subprocess.CompletedProcess on success.
    """
    # Use transmission-remote --add <magnet> --download-dir <download_dir>
    cmd = ["transmission-remote", "--add", magnet, "--download-dir", download_dir]
    # On some systems transmission-remote needs host/port/user/pass flags; rely on defaults
    try:
        proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return proc
    except FileNotFoundError:
        raise FileNotFoundError("transmission-remote not found in PATH; please install Transmission or use transmission-rpc library")


def add_magnet(magnet: str, tv: bool = False):
    """High-level add magnet: try RPC library, else CLI fallback.

    If tv=True, use DOWNLOAD_DIR/tv, otherwise use DOWNLOAD_DIR/film.
    Ensures the chosen directory exists (best-effort). Returns a dict with outcome info.
    """
    # choose subdir
    sub = "tv" if tv else "film"
    download_dir = os.path.join(DOWNLOAD_DIR, sub)
    # Ensure the download directory exists (best-effort)
    try:
        os.makedirs(download_dir, exist_ok=True)
    except Exception:
        # If creation fails, continue and let downstream calls report errors
        pass
    cfg = _get_config()
    # Try RPC library first
    try:
        torr = add_magnet_transmission_rpc(magnet, cfg["host"], cfg["port"], cfg["user"], cfg["password"], download_dir)
        return {"method": "rpc", "result": repr(torr)}
    except ImportError:
        # fallback to CLI
        pass
    except Exception as e:
        # RPC library present but call failed
        return {"method": "rpc", "error": str(e)}

    # CLI fallback
    try:
        proc = add_magnet_transmission_cli(magnet, download_dir)
        return {"method": "cli", "stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}
    except Exception as e:
        return {"method": "cli", "error": str(e)}


def _cli_main(argv=None):
    import argparse

    p = argparse.ArgumentParser(description="Add a magnet link to Transmission (RPC or CLI).")
    sub = p.add_subparsers(dest="cmd")

    addp = sub.add_parser("add", help="Add a magnet link")
    addp.add_argument("magnet", help="Magnet URI (quoted)")
    addp.add_argument("--tv", action="store_true", help="Place download in the 'tv' subdirectory; default is 'film'")

    args = p.parse_args(argv)
    if args.cmd == "add":
        out = add_magnet(args.magnet, tv=args.tv)
        print(out)
    else:
        p.print_help()


if __name__ == "__main__":
    _cli_main()
