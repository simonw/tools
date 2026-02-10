# Server Management CLI Demo

*2026-02-10T23:37:32Z*

This demo shows a Python CLI tool that starts and stops a background HTTP server. The key technique is using `subprocess.Popen` to launch the server as a detached child process, then storing its PID in a file so it can be stopped later.

First, let's look at the CLI's help output to see both subcommands.

```bash
uv run python/server_manage.py --help
```

```output
usage: server_manage.py [-h] {start,stop} ...

Start or stop a background Python HTTP server.

positional arguments:
  {start,stop}
    start       Start the HTTP server
    stop        Stop the running HTTP server

options:
  -h, --help    show this help message and exit
```

```bash
uv run python/server_manage.py start --help
```

```output
usage: server_manage.py start [-h] [--port PORT] directory

positional arguments:
  directory    Directory to serve

options:
  -h, --help   show this help message and exit
  --port PORT  Port to listen on (default: 8000)
```

Now let's start a server on port 8090, serving the current directory.

```bash
uv run python/server_manage.py start . --port 8090
```

```output
Server started on port 8090 serving /home/user/tools (PID 7607)
PID written to server.pid
```

The server is now running in the background. The process continues even though the start command has exited. Let's verify it with curl.

```bash
curl -s -o /dev/null -w 'HTTP status: %{http_code}\n' http://localhost:8090/
```

```output
HTTP status: 200
```

```bash
curl -s http://localhost:8090/ | head -5
```

```output
<!DOCTYPE HTML>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Directory listing for /</title>
```

We can also confirm the PID file was created and the process is running.

```bash
cat server.pid && echo '' && ps -p $(cat server.pid) -o pid,command --no-headers
```

```output
7607
 7607 /home/user/tools/.venv/bin/python3 -m http.server 8090 --directory /home/user/tools
```

Now let's stop the server.

```bash
uv run python/server_manage.py stop
```

```output
Sent SIGTERM to process 7607
Removed server.pid
```

Confirm the server is no longer reachable.

```bash
curl -s -o /dev/null -w 'HTTP status: %{http_code}\n' http://localhost:8090/ || echo 'Connection refused - server is stopped'
```

```output
HTTP status: 000
Connection refused - server is stopped
```

## Bash Version

There is also a bash equivalent at `bash/server_manage.sh`. It uses the same pattern: background the process with `&`, capture `$!` for the PID, and store it in a file.

```bash
bash bash/server_manage.sh start . --port 8091
```

```output
Server started on port 8091 serving /home/user/tools (PID 13847)
PID written to server.pid
```

```bash
curl -s -o /dev/null -w 'HTTP status: %{http_code}\n' http://localhost:8091/
```

```output
HTTP status: 200
```

```bash
bash bash/server_manage.sh stop
```

```output
Sent SIGTERM to process 13847
Removed server.pid
```
