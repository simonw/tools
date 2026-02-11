#!/usr/bin/env python3
"""
A CLI tool to start and stop a background Python HTTP server.

Usage:
    uv run server_manage.py start <directory> --port <port>
    uv run server_manage.py stop
"""

import argparse
import os
import signal
import subprocess
import sys
import time


PID_FILE = "server.pid"


def start_server(directory: str, port: int):
    """Start a background HTTP server serving the given directory on the given port."""
    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            old_pid = f.read().strip()
        print(
            f"Warning: {PID_FILE} already exists (PID {old_pid}). "
            "Use 'stop' first or remove the file.",
            file=sys.stderr,
        )
        sys.exit(1)

    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--directory", directory],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))

    # Give the server a moment to start
    time.sleep(0.5)

    if proc.poll() is not None:
        print("Error: server process exited immediately.", file=sys.stderr)
        os.remove(PID_FILE)
        sys.exit(1)

    print(f"Server started on port {port} serving {directory} (PID {proc.pid})")
    print(f"PID written to {PID_FILE}")


def stop_server():
    """Stop the background HTTP server using the stored PID file."""
    if not os.path.exists(PID_FILE):
        print(f"Error: {PID_FILE} not found. Is the server running?", file=sys.stderr)
        sys.exit(1)

    with open(PID_FILE) as f:
        pid_str = f.read().strip()

    try:
        pid = int(pid_str)
    except ValueError:
        print(f"Error: invalid PID '{pid_str}' in {PID_FILE}.", file=sys.stderr)
        sys.exit(1)

    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to process {pid}")
    except ProcessLookupError:
        print(f"Process {pid} not found (already stopped?).")
    except PermissionError:
        print(f"Error: no permission to kill process {pid}.", file=sys.stderr)
        sys.exit(1)

    os.remove(PID_FILE)
    print(f"Removed {PID_FILE}")


def main():
    parser = argparse.ArgumentParser(
        description="Start or stop a background Python HTTP server."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Start the HTTP server")
    start_parser.add_argument("directory", help="Directory to serve")
    start_parser.add_argument(
        "--port", type=int, default=8000, help="Port to listen on (default: 8000)"
    )

    subparsers.add_parser("stop", help="Stop the running HTTP server")

    args = parser.parse_args()

    if args.command == "start":
        start_server(args.directory, args.port)
    elif args.command == "stop":
        stop_server()


if __name__ == "__main__":
    main()
