#!/usr/bin/env python3
"""Minimal HTTP server for git repositories using git-http-backend."""

import argparse
import io
import os
import subprocess
from http.client import parse_headers
from socketserver import ThreadingMixIn
from wsgiref.simple_server import make_server, WSGIServer


class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def git_http_app(repo_path):
    """Create a WSGI app that serves a git repo via git-http-backend."""
    repo_path = os.path.abspath(repo_path)
    repo_name = os.path.basename(repo_path)
    project_root = os.path.dirname(repo_path)

    # Find git-http-backend
    exec_path = subprocess.check_output(["git", "--exec-path"], text=True).strip()
    backend = os.path.join(exec_path, "git-http-backend")

    def app(environ, start_response):
        path_info = "/" + repo_name + environ.get("PATH_INFO", "")

        env = {
            "GIT_PROJECT_ROOT": project_root,
            "GIT_HTTP_EXPORT_ALL": "1",
            "PATH_INFO": path_info,
            "REQUEST_METHOD": environ.get("REQUEST_METHOD", "GET"),
            "QUERY_STRING": environ.get("QUERY_STRING", ""),
            "CONTENT_TYPE": environ.get("CONTENT_TYPE", ""),
            "CONTENT_LENGTH": environ.get("CONTENT_LENGTH", ""),
            **{k: v for k, v in environ.items() if k.startswith("HTTP_")},
        }

        # Read request body
        body_input = b""
        if env["CONTENT_LENGTH"]:
            try:
                body_input = environ["wsgi.input"].read(int(env["CONTENT_LENGTH"]))
            except (ValueError, TypeError):
                pass

        proc = subprocess.run(
            [backend], env={**os.environ, **env}, input=body_input, capture_output=True
        )

        # Parse CGI response: headers\n\nbody
        header_end = proc.stdout.find(b"\r\n\r\n")
        sep_len = 4
        if header_end == -1:
            header_end = proc.stdout.find(b"\n\n")
            sep_len = 2

        if header_end == -1:
            start_response("200 OK", [("Content-Type", "application/octet-stream")])
            return [proc.stdout]

        headers = parse_headers(io.BytesIO(proc.stdout[:header_end] + b"\r\n\r\n"))
        body = proc.stdout[header_end + sep_len :]

        status = headers.get("Status", "200 OK")
        header_list = [(k, v) for k, v in headers.items() if k.lower() != "status"]

        start_response(status, header_list)
        return [body]

    return app


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Serve a git repo over HTTP (read-only)")
    p.add_argument("repo", help="Path to git repository")
    p.add_argument("-p", "--port", type=int, default=8000)
    p.add_argument("-H", "--host", default="localhost")
    args = p.parse_args()

    app = git_http_app(args.repo)
    server = make_server(args.host, args.port, app, server_class=ThreadedWSGIServer)
    print(f"Serving {args.repo} at http://{args.host}:{args.port}/")
    print(f"Clone: git clone http://{args.host}:{args.port}/ directory_name")
    server.serve_forever()
