#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Project: AI-Mixer
# Author: Vishwas
# License: MIT License
# -----------------------------------------------------------------------------
# youtube_downloader.py
# YouTube audio downloader using yt-dlp for AI-Mixer.
# Downloads audio from YouTube URLs and converts to MP3 format.
# -----------------------------------------------------------------------------

import os
import re
import subprocess
from typing import Optional, Tuple


def sanitize_filename(title: str) -> str:
    """Sanitize a YouTube title to a safe filename."""
    # Remove invalid characters
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    # Replace spaces and multiple underscores
    safe = re.sub(r'\s+', '_', safe)
    safe = re.sub(r'_+', '_', safe)
    # Limit length
    safe = safe[:100]
    return safe.strip('_')


def download_from_youtube(
    url: str,
    output_dir: str,
    format_preference: str = "bestaudio/best",
) -> Tuple[bool, str, Optional[str]]:
    """
    Download audio from a YouTube URL.

    Args:
        url: YouTube video URL
        output_dir: Directory to save the downloaded file
        format_preference: yt-dlp format string

    Returns:
        Tuple of (success, message, filename or None)
    """
    os.makedirs(output_dir, exist_ok=True)

    # First, get the video title
    try:
        result = subprocess.run(
            ["yt-dlp", "--get-title", "--no-warnings", url],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return False, f"Failed to get video info: {result.stderr}", None

        title = result.stdout.strip()
        safe_title = sanitize_filename(title)
        output_template = os.path.join(output_dir, f"{safe_title}.%(ext)s")

    except subprocess.TimeoutExpired:
        return False, "Timeout while fetching video info", None
    except FileNotFoundError:
        return False, "yt-dlp not installed. Run: pip install yt-dlp", None
    except Exception as e:
        return False, f"Error getting video info: {str(e)}", None

    # Download and convert to MP3
    print(f"Downloading: {title}")

    cmd = [
        "yt-dlp",
        "-f", format_preference,
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",  # Best quality
        "--no-playlist",  # Single video only
        "--no-warnings",
        "-o", output_template,
        url
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for download
        )

        if result.returncode != 0:
            return False, f"Download failed: {result.stderr}", None

        # Find the downloaded file
        mp3_path = os.path.join(output_dir, f"{safe_title}.mp3")
        if os.path.exists(mp3_path):
            print(f"Successfully downloaded: {safe_title}.mp3")
            return True, f"Downloaded: {title}", f"{safe_title}.mp3"

        # Check for any mp3 file with similar name
        for f in os.listdir(output_dir):
            if f.startswith(safe_title[:20]) and f.endswith('.mp3'):
                print(f"Successfully downloaded: {f}")
                return True, f"Downloaded: {title}", f

        return False, "Download completed but file not found", None

    except subprocess.TimeoutExpired:
        return False, "Download timeout (exceeded 5 minutes)", None
    except Exception as e:
        return False, f"Download error: {str(e)}", None


def get_video_info(url: str) -> Tuple[bool, dict]:
    """
    Get metadata about a YouTube video without downloading.

    Returns:
        Tuple of (success, info_dict or error_message)
    """
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--dump-json",
                "--no-warnings",
                "--no-playlist",
                url
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return False, {"error": result.stderr}

        import json
        info = json.loads(result.stdout)

        return True, {
            "title": info.get("title", "Unknown"),
            "duration": info.get("duration", 0),
            "duration_string": info.get("duration_string", "0:00"),
            "uploader": info.get("uploader", "Unknown"),
            "view_count": info.get("view_count", 0),
            "thumbnail": info.get("thumbnail"),
        }

    except subprocess.TimeoutExpired:
        return False, {"error": "Timeout while fetching video info"}
    except FileNotFoundError:
        return False, {"error": "yt-dlp not installed"}
    except json.JSONDecodeError:
        return False, {"error": "Failed to parse video info"}
    except Exception as e:
        return False, {"error": str(e)}


def is_valid_youtube_url(url: str) -> bool:
    """Check if a URL is a valid YouTube URL."""
    youtube_patterns = [
        r'(https?://)?(www\.)?youtube\.com/watch\?v=[\w-]+',
        r'(https?://)?(www\.)?youtu\.be/[\w-]+',
        r'(https?://)?(www\.)?youtube\.com/shorts/[\w-]+',
        r'(https?://)?music\.youtube\.com/watch\?v=[\w-]+',
    ]

    for pattern in youtube_patterns:
        if re.match(pattern, url):
            return True
    return False


if __name__ == "__main__":
    # Test the downloader
    import sys

    if len(sys.argv) < 2:
        print("Usage: python youtube_downloader.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1]
    output_dir = os.path.join(os.path.dirname(__file__), "songs")

    if not is_valid_youtube_url(url):
        print(f"Invalid YouTube URL: {url}")
        sys.exit(1)

    success, message, filename = download_from_youtube(url, output_dir)
    print(f"Result: {message}")
    if filename:
        print(f"File: {filename}")
