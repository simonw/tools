#!/usr/bin/env python3
"""
Fetch file listing of every available Google Cloud bucket and report total sizes.
"""

import os
import subprocess
import datetime
import re
import argparse
from pathlib import Path


def run_command(command, capture_stderr=False):
    """Run a shell command and return the output"""
    try:
        stderr_option = subprocess.PIPE if capture_stderr else subprocess.DEVNULL
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=stderr_option, text=True, shell=True
        )
        if capture_stderr and result.returncode != 0:
            return "", result.stderr
        return result.stdout.strip(), ""
    except subprocess.SubprocessError as e:
        return "", str(e)


def bytes_to_gb(bytes_value):
    """Convert bytes to GB with 2 decimal places"""
    try:
        return round(float(bytes_value) / (1024**3), 2)
    except (ValueError, TypeError):
        return 0.0


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Calculate sizes of Google Cloud Storage buckets"
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        help="Directory to store bucket listings (default: create temp directory)",
    )
    args = parser.parse_args()

    # Create output directory if not specified
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
    else:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"bucket_listings_{timestamp}")
        output_dir.mkdir(exist_ok=True)

    print(f"Output directory: {output_dir}")
    print("Fetching list of buckets...")

    # Get list of buckets
    buckets_output, error = run_command("gcloud storage ls")
    if not buckets_output:
        print(f"No buckets found or error listing buckets: {error}")
        return

    buckets = buckets_output.splitlines()
    print(f"Found {len(buckets)} buckets.")

    for bucket in buckets:
        bucket = bucket.strip()
        if not bucket:
            continue

        bucket_name = bucket.replace("gs://", "")
        sanitized_name = re.sub(r"[^a-zA-Z0-9_-]", "_", bucket_name)
        listing_file = output_dir / f"{sanitized_name}_listing.txt"

        print(f"\nProcessing bucket: {bucket}")

        # Use gcloud storage ls --recursive with -l flag to get detailed listing
        list_cmd = f"gcloud storage ls --recursive {bucket} -l"
        print(f"Running: {list_cmd}")

        output, error = run_command(list_cmd, capture_stderr=True)

        if error:
            print(f"Error listing bucket contents: {error}")
            print(f"{bucket}: 0.00 GB (error accessing)")
            with open(listing_file, "w") as f:
                f.write(f"# Error: {error}\n")
            continue

        if not output:
            print(f"Bucket appears to be empty")
            print(f"{bucket}: 0.00 GB (empty bucket)")
            with open(listing_file, "w") as f:
                f.write("# Bucket appears to be empty\n")
            continue

        # Write the listing to the file
        with open(listing_file, "w") as f:
            f.write(output)

        # Process the file sizes from the listing
        bucket_size_bytes = 0
        lines_processed = 0
        lines_with_size = 0

        # Process the output line by line to extract sizes
        for line in output.splitlines():
            lines_processed += 1
            line = line.strip()
            if not line:
                continue

            # gcloud storage ls -l format has size as the first field
            # Example: 38226975 2024-11-20T04:37:17Z gs://bucket/path/to/object
            parts = line.split()
            if len(parts) >= 3 and parts[0].isdigit():
                try:
                    size = int(parts[0])
                    bucket_size_bytes += size
                    lines_with_size += 1
                except (ValueError, IndexError):
                    pass

        bucket_size_gb = bytes_to_gb(bucket_size_bytes)
        print(
            f"Processed {lines_processed} lines, found {lines_with_size} files with size"
        )
        print(f"{bucket}: {bucket_size_gb:.2f} GB")

        # Append summary to the listing file
        with open(listing_file, "a") as f:
            f.write(f"\n# SUMMARY\n")
            f.write(
                f"# Total size: {bucket_size_bytes} bytes ({bucket_size_gb:.2f} GB)\n"
            )
            f.write(f"# Files processed: {lines_with_size}\n")

    print(f"\nAll bucket listings saved in {output_dir}")
    print("Script complete!")


if __name__ == "__main__":
    main()
