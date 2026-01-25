#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "yt-dlp",
#     "static-ffmpeg",
# ]
# ///
"""
Create a timelapse GIF from a YouTube livestream's DVR.

Usage:
    uv run livestream-gif.py <youtube-url> [--frames N] [--hours N] [--output FILE] [--resolution RES]

Examples:
    uv run livestream-gif.py "https://www.youtube.com/watch?v=BfGL7A2YgUY"
    uv run livestream-gif.py "https://www.youtube.com/watch?v=BfGL7A2YgUY" --frames 50 --hours 4
    uv run livestream-gif.py "https://www.youtube.com/watch?v=BfGL7A2YgUY" --frames 1  # quick test
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from static_ffmpeg import run as static_ffmpeg

# Get bundled ffmpeg/ffprobe paths
FFMPEG, FFPROBE = static_ffmpeg.get_or_fetch_platform_executables_else_raise()


def run_ytdlp(*args: str) -> subprocess.CompletedProcess:
    """Run yt-dlp as a module using the current Python interpreter."""
    cmd = [sys.executable, "-m", "yt_dlp", *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def run_ffmpeg(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run ffmpeg command."""
    cmd = [FFMPEG, *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def run_ffprobe(*args: str) -> subprocess.CompletedProcess:
    """Run ffprobe command."""
    cmd = [FFPROBE, *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def get_stream_url(youtube_url: str, format_id: str = "93") -> str:
    """Get the HLS stream URL for the given format."""
    result = run_ytdlp("-f", format_id, "--get-url", youtube_url)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get stream URL: {result.stderr}")
    return result.stdout.strip()


def get_stream_info(youtube_url: str) -> dict:
    """Get stream metadata."""
    result = run_ytdlp("--dump-json", youtube_url)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get stream info: {result.stderr}")
    return json.loads(result.stdout)


def get_available_formats(youtube_url: str) -> list[dict]:
    """Get available video formats."""
    info = get_stream_info(youtube_url)
    return info.get("formats", [])


def get_stream_position(hls_url: str) -> int:
    """Get the current stream position in seconds."""
    result = run_ffprobe(
        "-v", "error",
        "-show_entries", "format=start_time",
        "-of", "default=noprint_wrappers=1:nokey=1",
        hls_url
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to probe stream: {result.stderr}")
    return int(float(result.stdout.strip()))


def probe_dvr_start(hls_url: str, current_pos: int) -> int:
    """Find the actual DVR start by probing seekable positions.

    Returns the earliest seekable position in seconds.
    """
    import urllib.request
    import re

    # YouTube DVR: the manifest URL contains sequence numbers we can use
    # Try to get the earliest available segment from the manifest
    with urllib.request.urlopen(hls_url) as f:
        manifest = f.read().decode()

    # Look for EXT-X-MEDIA-SEQUENCE which tells us the first segment number
    match = re.search(r'#EXT-X-MEDIA-SEQUENCE:(\d+)', manifest)
    if match:
        first_seq = int(match.group(1))
        # Each segment is typically 5 seconds
        # The DVR start is approximately: current_pos - (current_seq - first_seq) * 5
        # But we don't easily know current_seq, so estimate from segment count

        # Count segments in manifest (this is the sliding window)
        segment_count = manifest.count('#EXTINF:')

        # If first_seq is low and stream has been running long, DVR might be limited
        # Estimate: first_seq * 5 seconds is approximately when DVR starts
        estimated_dvr_start = first_seq * 5

        if estimated_dvr_start < current_pos:
            return estimated_dvr_start

    # Fallback: assume 12 hours max DVR (typical YouTube limit)
    max_dvr = 12 * 3600
    return max(0, current_pos - max_dvr)


def grab_frame(hls_url: str, seek_pos: int, output_path: Path) -> bool:
    """Grab a single frame from the stream at the given position."""
    result = run_ffmpeg(
        "-ss", str(seek_pos),
        "-i", hls_url,
        "-frames:v", "1",
        "-update", "1",
        "-y", str(output_path),
        check=False
    )
    return result.returncode == 0 and output_path.exists()


def create_gif(frames_dir: Path, output_path: Path, fps: int = 10) -> None:
    """Create an animated GIF from frames using palette generation."""
    palette_path = frames_dir / "palette.png"

    # Generate optimized palette
    run_ffmpeg(
        "-framerate", str(fps),
        "-pattern_type", "glob",
        "-i", str(frames_dir / "*.jpg"),
        "-vf", "palettegen=stats_mode=diff",
        "-y", str(palette_path)
    )

    # Create GIF using palette (-loop 0 = infinite loop)
    run_ffmpeg(
        "-framerate", str(fps),
        "-pattern_type", "glob",
        "-i", str(frames_dir / "*.jpg"),
        "-i", str(palette_path),
        "-lavfi", "paletteuse=dither=bayer:bayer_scale=3",
        "-loop", "0",
        "-y", str(output_path)
    )


def create_mp4(frames_dir: Path, output_path: Path, fps: int = 10) -> None:
    """Create a silent MP4 video from frames.

    Note: MP4 doesn't have a native loop flag like GIF. Looping is controlled
    by the player (e.g., <video loop> in HTML, or player settings).
    """
    run_ffmpeg(
        "-framerate", str(fps),
        "-pattern_type", "glob",
        "-i", str(frames_dir / "*.jpg"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-an",  # No audio
        "-movflags", "+faststart",  # Web optimization
        "-y", str(output_path)
    )


def select_format(youtube_url: str, resolution: str) -> str:
    """Select the best format ID for the given resolution."""
    resolution_map = {
        "144p": "91",
        "240p": "92",
        "360p": "93",
        "480p": "94",
        "720p": "95",
        "1080p": "96",
    }

    if resolution in resolution_map:
        return resolution_map[resolution]

    # Try to find a matching format
    formats = get_available_formats(youtube_url)
    for fmt in formats:
        if resolution in str(fmt.get("height", "")):
            return str(fmt.get("format_id", "93"))

    return "93"  # Default to 360p


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", help="YouTube livestream URL")
    parser.add_argument(
        "--frames", "-f",
        type=int,
        default=100,
        help="Number of frames to capture (default: 100)"
    )
    parser.add_argument(
        "--hours", "-H",
        type=float,
        default=None,
        help="Hours of footage to cover (default: all available)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output path (default: livestream-timelapse.gif or .mp4)"
    )
    parser.add_argument(
        "--resolution", "-r",
        default="360p",
        choices=["144p", "240p", "360p", "480p", "720p", "1080p"],
        help="Video resolution (default: 360p)"
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=10,
        help="GIF frames per second (default: 10)"
    )
    parser.add_argument(
        "--keep-frames",
        action="store_true",
        help="Keep extracted frames after creating GIF"
    )
    parser.add_argument(
        "--mp4",
        action="store_true",
        help="Output as MP4 instead of GIF (silent video)"
    )

    args = parser.parse_args()

    # Validate
    if args.frames < 1:
        parser.error("--frames must be at least 1")
    if args.hours is not None and args.hours <= 0:
        parser.error("--hours must be positive")

    # Set default output path based on format
    if args.output is None:
        args.output = Path("livestream-timelapse.mp4" if args.mp4 else "livestream-timelapse.gif")

    output_format = "MP4" if args.mp4 else "GIF"

    # Get format ID for resolution
    format_id = select_format(args.url, args.resolution)

    # Get stream URL and position first to determine available duration
    print("Getting stream URL...")
    hls_url = get_stream_url(args.url, format_id)
    current_pos = get_stream_position(hls_url)

    # Find the actual DVR start position
    dvr_start = probe_dvr_start(hls_url, current_pos)
    dvr_seconds = current_pos - dvr_start
    dvr_hours = dvr_seconds / 3600

    if args.hours is None:
        args.hours = dvr_hours
        print(f"DVR window: {dvr_hours:.1f} hours available")
    elif args.hours * 3600 > dvr_seconds:
        print(f"Note: Requested {args.hours:.1f}h but only {dvr_hours:.1f}h available in DVR")
        args.hours = dvr_hours

    total_seconds = int(args.hours * 3600)
    start_pos = current_pos - total_seconds

    # Ensure we don't go before DVR start
    if start_pos < dvr_start:
        start_pos = dvr_start
        total_seconds = current_pos - start_pos
        args.hours = total_seconds / 3600
    interval = total_seconds // args.frames

    print(f"Creating timelapse {output_format} from: {args.url}")
    print(f"  Frames: {args.frames}")
    print(f"  Duration: {args.hours:.1f} hours")
    print(f"  Resolution: {args.resolution}")
    print(f"  Format ID: {format_id}")
    print(f"  Capturing 1 frame every {interval} seconds ({interval/60:.1f} minutes)")
    print()

    # Create temp directory for frames
    with tempfile.TemporaryDirectory() as tmpdir:
        frames_dir = Path(tmpdir)
        if args.keep_frames:
            frames_dir = Path("frames")
            frames_dir.mkdir(exist_ok=True)

        print(f"Stream position: {current_pos}s ({current_pos/3600:.1f} hours)")
        print(f"Starting from: {start_pos}s ({args.hours:.1f} hours ago)")
        print()

        # Grab frames
        url_refresh_interval = 20  # Refresh URL every N frames (they expire)

        for i in range(args.frames):
            seek_pos = start_pos + (i * interval)
            frame_path = frames_dir / f"frame_{i:04d}.jpg"

            # Refresh URL periodically
            if i > 0 and i % url_refresh_interval == 0:
                print("\nRefreshing stream URL...")
                hls_url = get_stream_url(args.url, format_id)

            print(f"\rCapturing frame {i+1}/{args.frames} (position: {seek_pos}s)...", end="", flush=True)

            if not grab_frame(hls_url, seek_pos, frame_path):
                print(f"\nWarning: Failed to grab frame {i+1}")

        print("\n")

        # Count captured frames
        captured = list(frames_dir.glob("*.jpg"))
        print(f"Captured {len(captured)} frames")

        if not captured:
            print("Error: No frames captured!")
            sys.exit(1)

        # Create output
        print(f"Creating {output_format} at {args.fps} fps...")
        if args.mp4:
            create_mp4(frames_dir, args.output, args.fps)
        else:
            create_gif(frames_dir, args.output, args.fps)

        if args.output.exists():
            size_mb = args.output.stat().st_size / (1024 * 1024)
            duration = len(captured) / args.fps
            print(f"\nCreated: {args.output}")
            print(f"  Size: {size_mb:.1f} MB")
            print(f"  Duration: {duration:.1f} seconds")
            print(f"  Frames: {len(captured)}")
        else:
            print("Error: Failed to create GIF")
            sys.exit(1)


if __name__ == "__main__":
    main()
