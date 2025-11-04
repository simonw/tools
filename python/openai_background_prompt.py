#!/usr/bin/env python3
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx"
# ]
# ///
#
# openai_background_prompt.py
#
# Usage:
#   python openai_background_prompt.py o4-mini-deep-research 'Here is my prompt'
#
# Notes:
# - Prints the FINAL response JSON to STDOUT.
# - Logs important status updates (including Response ID) to STDERR in yellow.
# - Depends only on httpx (pip install httpx).
#
# Env:
#   OPENAI_API_KEY   (required)
#   OPENAI_ORG_ID    (optional -> sent as OpenAI-Organization)
#   OPENAI_PROJECT   (optional -> sent as OpenAI-Project)
#   OPENAI_BASE_URL  (optional -> defaults to https://api.openai.com/v1)

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Optional

import httpx

YELLOW = "\033[33m"
RESET = "\033[0m"

TERMINAL_STATUSES = {
    "succeeded",
    "failed",
    "cancelled",
    "expired",
    "rejected",
    "completed",
}


def ylog(msg: str) -> None:
    """Log a yellow message to stderr."""
    sys.stderr.write(f"{YELLOW}{msg}{RESET}\n")
    sys.stderr.flush()


def elog(msg: str) -> None:
    """Log a non-colored message to stderr."""
    sys.stderr.write(f"{msg}\n")
    sys.stderr.flush()


def build_tools(enable_web_search: bool, enable_code_interpreter: bool) -> list:
    tools = []
    if enable_web_search:
        tools.append({"type": "web_search_preview"})
    if enable_code_interpreter:
        tools.append({"type": "code_interpreter", "container": {"type": "auto"}})
    return tools


def create_background_job(
    client: httpx.Client,
    model: str,
    prompt: str,
    enable_web_search: bool = True,
    enable_code_interpreter: bool = True,
    reasoning_summary_auto: bool = True,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": model,
        "input": prompt,
        "background": True,
    }
    if reasoning_summary_auto:
        payload["reasoning"] = {"summary": "auto"}

    tools = build_tools(enable_web_search, enable_code_interpreter)
    if tools:
        payload["tools"] = tools

    r = client.post("/responses", json=payload, timeout=None)
    r.raise_for_status()
    return r.json()


def poll_until_complete(
    client: httpx.Client,
    response_id: str,
    poll_interval: float,
    max_wait: Optional[float],
) -> Dict[str, Any]:
    start = time.time()
    last_status = None

    while True:
        r = client.get(f"/responses/{response_id}", timeout=None)
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        if status != last_status:
            ylog(f"[{response_id}] status -> {status}")
            last_status = status
        else:
            # Output just a '.' on the same line to show progress
            sys.stderr.write(".")
            sys.stderr.flush()

        if status in TERMINAL_STATUSES:
            return data

        if max_wait is not None and (time.time() - start) > max_wait:
            elog("Max wait time exceeded while polling; returning last known payload.")
            return data

        time.sleep(poll_interval)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run an OpenAI Responses API background prompt and print the final JSON."
    )
    parser.add_argument(
        "model",
        help="Model name (e.g. o4-mini-deep-research or gpt-5-pro)",
    )
    parser.add_argument("prompt", help="The prompt string to run in background mode")
    parser.add_argument(
        "--web-search",
        action="store_true",
        help="Enable the web_search_preview tool",
    )
    parser.add_argument(
        "--code-interpreter",
        action="store_true",
        help="Enable the code_interpreter tool",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=3.0,
        help="Seconds between polls (default: 3.0)",
    )
    parser.add_argument(
        "--max-wait",
        type=float,
        default=None,
        help="Maximum seconds to wait before returning",
    )
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        elog("ERROR: OPENAI_API_KEY is not set.")
        return 2

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip(
        "/"
    )
    org_id = os.environ.get("OPENAI_ORG_ID")
    project = os.environ.get("OPENAI_PROJECT")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if org_id:
        headers["OpenAI-Organization"] = org_id
    if project:
        headers["OpenAI-Project"] = project

    try:
        with httpx.Client(base_url=base_url, headers=headers) as client:
            job = create_background_job(
                client=client,
                model=args.model,
                prompt=args.prompt,
                enable_web_search=args.web_search,
                enable_code_interpreter=args.code_interpreter,
                reasoning_summary_auto=True,
            )
            response_id = job.get("id")
            status = job.get("status")
            if not response_id:
                elog("ERROR: No response ID returned.")
                print(json.dumps(job, indent=2, ensure_ascii=False))
                return 1

            ylog(f"Response ID: {response_id}")
            if status:
                ylog(f"[{response_id}] initial status -> {status}")

            final = poll_until_complete(
                client=client,
                response_id=response_id,
                poll_interval=args.poll_interval,
                max_wait=args.max_wait,
            )

            # Log usage summary if available
            usage = final.get("usage") or {}
            if usage:
                ylog(
                    f"[{response_id}] usage -> input_tokens={usage.get('input_tokens')} "
                    f"output_tokens={usage.get('output_tokens')} total_tokens={usage.get('total_tokens')}"
                )

            # Print the full final JSON payload to STDOUT
            print(json.dumps(final, indent=2, ensure_ascii=False))
            # Non-zero exit on non-success terminal states.
            if final.get("status") != "succeeded":
                return 1
            return 0

    except httpx.HTTPStatusError as e:
        elog(f"HTTP error: {e.response.status_code} - {e.response.text}")
        return 1
    except httpx.RequestError as e:
        elog(f"Request error: {e}")
        return 1
    except KeyboardInterrupt:
        elog("Interrupted by user.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
