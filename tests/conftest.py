"""
Pytest configuration and fixtures for the tools tests.
"""

import socket
import subprocess
import sys
import time
import pytest


def find_unused_port():
    """Find and return an unused port number on localhost."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        return port
    finally:
        sock.close()


class StaticServer:
    """Manages a static file HTTP server with proper startup waiting."""

    def __init__(self, port):
        self.port = port
        self._process = None
        self._directory = None

    def start(self, directory='.'):
        """Start an HTTP server serving the specified directory."""
        if self._process is not None:
            raise RuntimeError("Server is already running")

        self._directory = directory
        self._process = subprocess.Popen(
            [sys.executable, '-m', 'http.server', str(self.port), '--directory', str(directory)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for the server to be ready (up to 5 seconds)
        import urllib.request
        import urllib.error

        for _ in range(50):  # 50 * 0.1 = 5 seconds max
            time.sleep(0.1)

            if self._process.poll() is not None:
                stdout, stderr = self._process.communicate()
                raise RuntimeError(f"Server failed to start: {stderr}")

            try:
                urllib.request.urlopen(f'http://127.0.0.1:{self.port}/', timeout=1)
                return self  # Server is ready
            except (urllib.error.URLError, ConnectionRefusedError):
                continue

        raise RuntimeError("Server did not become ready in time")

    def stop(self):
        """Stop the HTTP server if it's running."""
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
            self._process = None


@pytest.fixture
def unused_port():
    """Returns an unused port number on localhost."""
    return find_unused_port()


@pytest.fixture
def unused_port_server(unused_port):
    """
    Returns a StaticServer instance that can start an HTTP server on an unused port.
    The server automatically stops at the end of the test function.
    """
    server = StaticServer(unused_port)
    yield server
    server.stop()
