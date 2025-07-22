#!/usr/bin/env python3
"""
ModelScope model size calculator

Usage: uv run modelscope_size.py https://modelscope.cn/models/Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8
"""

import sys
import json
import urllib.request
import urllib.parse
from typing import Dict, Any


def parse_model_url(url: str) -> tuple[str, str]:
    """Extract namespace and model name from ModelScope URL"""
    if not url.startswith("https://modelscope.cn/models/"):
        raise ValueError("Invalid ModelScope model URL")

    path = url.replace("https://modelscope.cn/models/", "")
    parts = path.split("/")

    if len(parts) < 2:
        raise ValueError("URL must contain namespace/model format")

    namespace = parts[0]
    model = parts[1]

    return namespace, model


def fetch_model_files(namespace: str, model: str) -> Dict[str, Any]:
    """Fetch model files from ModelScope API"""
    api_url = f"https://modelscope.cn/api/v1/models/{namespace}/{model}/repo/files?Revision=master&Root="

    try:
        with urllib.request.urlopen(api_url) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data
    except Exception as e:
        raise RuntimeError(f"Failed to fetch data from API: {e}")


def calculate_total_size(files_data: Dict[str, Any]) -> int:
    """Calculate total size of all files in bytes"""
    total_size = 0

    if "Data" not in files_data:
        raise ValueError("Invalid API response format")

    data = files_data["Data"]
    if "Files" not in data:
        raise ValueError("No Files found in API response")

    files = data["Files"]

    for file_info in files:
        if "Size" in file_info:
            total_size += file_info["Size"]

    return total_size


def bytes_to_gb(bytes_size: int) -> float:
    """Convert bytes to gigabytes"""
    return bytes_size / (1024**3)


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: uv run modelscope_size.py <modelscope_model_url>", file=sys.stderr
        )
        sys.exit(1)

    model_url = sys.argv[1]

    try:
        namespace, model = parse_model_url(model_url)
        files_data = fetch_model_files(namespace, model)
        total_bytes = calculate_total_size(files_data)
        total_gb = bytes_to_gb(total_bytes)

        print(f"{total_gb:.1f} GB")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
