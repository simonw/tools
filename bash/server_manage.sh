#!/usr/bin/env bash
#
# A CLI tool to start and stop a background Python HTTP server.
#
# Usage:
#   bash server_manage.sh start <directory> --port <port>
#   bash server_manage.sh stop

set -euo pipefail

PID_FILE="server.pid"

usage() {
    echo "Usage:"
    echo "  $0 start <directory> [--port <port>]"
    echo "  $0 stop"
    exit 1
}

start_server() {
    local directory="$1"
    local port="${2:-8000}"

    directory="$(cd "$directory" && pwd)"

    if [ -f "$PID_FILE" ]; then
        echo "Error: $PID_FILE already exists (PID $(cat "$PID_FILE")). Use 'stop' first." >&2
        exit 1
    fi

    python3 -m http.server "$port" --directory "$directory" &>/dev/null &
    local pid=$!

    echo "$pid" > "$PID_FILE"

    sleep 0.5

    if ! kill -0 "$pid" 2>/dev/null; then
        echo "Error: server process exited immediately." >&2
        rm -f "$PID_FILE"
        exit 1
    fi

    echo "Server started on port $port serving $directory (PID $pid)"
    echo "PID written to $PID_FILE"
}

stop_server() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Error: $PID_FILE not found. Is the server running?" >&2
        exit 1
    fi

    local pid
    pid="$(cat "$PID_FILE")"

    if kill "$pid" 2>/dev/null; then
        echo "Sent SIGTERM to process $pid"
    else
        echo "Process $pid not found (already stopped?)."
    fi

    rm -f "$PID_FILE"
    echo "Removed $PID_FILE"
}

case "${1:-}" in
    start)
        shift
        if [ $# -lt 1 ]; then
            usage
        fi
        directory="$1"
        shift
        port=8000
        while [ $# -gt 0 ]; do
            case "$1" in
                --port)
                    port="$2"
                    shift 2
                    ;;
                *)
                    echo "Unknown option: $1" >&2
                    usage
                    ;;
            esac
        done
        start_server "$directory" "$port"
        ;;
    stop)
        stop_server
        ;;
    *)
        usage
        ;;
esac
