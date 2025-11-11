#!/usr/bin/env python3
"""Minimal Transmission helper for adding magnet links.

This implements Option A (Transmission) from the interactive discussion.

Usage:
  - CLI: python rtorrent.py add "magnet:?xt=..." /path/to/dest
  - Programmatic: from rtorrent import add_magnet; add_magnet(magnet, dest)

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


def add_magnet_transmission_rpc(magnet: str, dest: str, host: str, port: int, user: Optional[str], password: Optional[str]):
    """Add magnet using transmission-rpc library. Raises ImportError if lib missing.
    Returns the id or added Torrent object depending on the library.
    """
    try:
        import transmission_rpc
    except Exception as exc:
        raise ImportError("transmission-rpc library not available") from exc

    client = transmission_rpc.Client(host=host, port=port, username=user, password=password)
    # transmission-rpc's add_torrent accepts a uri and optional download_dir
    # It returns a Torrent or list of Torrents depending on the version.
    torr = client.add_torrent(magnet, download_dir=dest)
    return torr


def add_magnet_transmission_cli(magnet: str, dest: str):
    """Add magnet using transmission-remote CLI. Requires transmission-remote in PATH.
    Returns subprocess.CompletedProcess on success.
    """
    # Use transmission-remote --add <magnet> --download-dir <dest>
    cmd = ["transmission-remote", "--add", magnet, "--download-dir", dest]
    # On some systems transmission-remote needs host/port/user/pass flags; rely on defaults
    try:
        proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return proc
    except FileNotFoundError:
        raise FileNotFoundError("transmission-remote not found in PATH; please install Transmission or use transmission-rpc library")


def add_magnet(magnet: str, dest: str):
    """High-level add magnet: try RPC library, else CLI fallback.

    Returns a dict with outcome information.
    """
    cfg = _get_config()
    # Try RPC library first
    try:
        torr = add_magnet_transmission_rpc(magnet, dest, cfg["host"], cfg["port"], cfg["user"], cfg["password"])
        return {"method": "rpc", "result": repr(torr)}
    except ImportError:
        # fallback to CLI
        pass
    except Exception as e:
        # RPC library present but call failed
        return {"method": "rpc", "error": str(e)}

    # CLI fallback
    try:
        proc = add_magnet_transmission_cli(magnet, dest)
        return {"method": "cli", "stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}
    except Exception as e:
        return {"method": "cli", "error": str(e)}


def _cli_main(argv=None):
    import argparse

    p = argparse.ArgumentParser(description="Add a magnet link to Transmission (RPC or CLI).")
    sub = p.add_subparsers(dest="cmd")

    addp = sub.add_parser("add", help="Add a magnet link")
    addp.add_argument("magnet", help="Magnet URI (quoted)")
    addp.add_argument("dest", help="Destination directory for this torrent")

    args = p.parse_args(argv)
    if args.cmd == "add":
        out = add_magnet(args.magnet, args.dest)
        print(out)
    else:
        p.print_help()


if __name__ == "__main__":
    _cli_main()
