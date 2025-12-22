#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx"]
# ///
"""
List model IDs from OpenAI, Anthropic, and Gemini using httpx.

API keys are obtained via:
  llm keys get openai
  llm keys get anthropic
  llm keys get gemini

Providers whose key command fails are skipped.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable, Optional

import httpx


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    models: list[str]


def _get_key_via_llm(provider: str) -> Optional[str]:
    """
    Run: llm keys get <provider>
    Return the key string (stripped) or None if command fails.
    """
    try:
        proc = subprocess.run(
            ["llm", "keys", "get", provider],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    key = (proc.stdout or "").strip()
    return key or None


def _print_section(title: str) -> None:
    print("\n" + "=" * len(title))
    print(title)
    print("=" * len(title))


def list_openai_models(client: httpx.Client, api_key: str) -> ProviderResult:
    url = "https://api.openai.com/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}

    r = client.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()

    models = []
    for m in data.get("data", []) or []:
        mid = m.get("id")
        if isinstance(mid, str):
            models.append(mid)

    models = sorted(set(models))
    return ProviderResult("openai", models)


def list_anthropic_models(client: httpx.Client, api_key: str) -> ProviderResult:
    url = "https://api.anthropic.com/v1/models"
    # Anthropic requires the anthropic-version header on API requests.
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    models: list[str] = []
    after_id: Optional[str] = None

    while True:
        params = {}
        if after_id:
            params["after_id"] = after_id

        r = client.get(url, headers=headers, params=params)
        r.raise_for_status()
        payload = r.json()

        for m in payload.get("data", []) or []:
            mid = m.get("id")
            if isinstance(mid, str):
                models.append(mid)

        has_more = bool(payload.get("has_more"))
        after_id = payload.get("last_id") if has_more else None
        if not has_more or not isinstance(after_id, str) or not after_id:
            break

    models = sorted(set(models))
    return ProviderResult("anthropic", models)


def list_gemini_models(client: httpx.Client, api_key: str) -> ProviderResult:
    url = "https://generativelanguage.googleapis.com/v1beta/models"

    models: list[str] = []
    page_token: Optional[str] = None

    while True:
        params = {"key": api_key}
        if page_token:
            params["pageToken"] = page_token

        r = client.get(url, params=params)
        r.raise_for_status()
        payload = r.json()

        for m in payload.get("models", []) or []:
            # Gemini uses "name" like "models/gemini-2.0-flash"
            name = m.get("name")
            if isinstance(name, str):
                models.append(name)

        page_token = payload.get("nextPageToken")
        if not isinstance(page_token, str) or not page_token:
            break

    models = sorted(set(models))
    return ProviderResult("gemini", models)


def main(argv: list[str]) -> int:
    # Optional: --json to emit machine-readable output.
    as_json = "--json" in argv

    # Try to get keys. Skip providers that error.
    keys = {
        "openai": _get_key_via_llm("openai"),
        "anthropic": _get_key_via_llm("anthropic"),
        "gemini": _get_key_via_llm("gemini"),
    }

    available = {k: v for k, v in keys.items() if v}
    if not available:
        print("No API keys found via `llm keys get {openai,anthropic,gemini}`. Nothing to do.", file=sys.stderr)
        return 2

    results: list[ProviderResult] = []

    with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
        for provider, key in available.items():
            try:
                if provider == "openai":
                    results.append(list_openai_models(client, key))
                elif provider == "anthropic":
                    results.append(list_anthropic_models(client, key))
                elif provider == "gemini":
                    results.append(list_gemini_models(client, key))
            except httpx.HTTPError as e:
                # Don't kill the whole run if one provider fails.
                print(f"[{provider}] HTTP error: {e}", file=sys.stderr)
            except (ValueError, json.JSONDecodeError) as e:
                print(f"[{provider}] JSON parse error: {e}", file=sys.stderr)

    if as_json:
        out = {r.provider: r.models for r in results}
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0

    # Pretty output
    for r in results:
        _print_section(f"{r.provider} ({len(r.models)} models)")
        for mid in r.models:
            print(mid)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

