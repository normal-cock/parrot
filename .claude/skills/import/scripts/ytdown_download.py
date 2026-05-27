#!/usr/bin/env python3
"""Download YouTube video (480p) via ytdown.io."""

import json, requests, time, sys, os
from requests.exceptions import RequestException


def download_video(youtube_url, output_path):
    print(f"Downloading: {youtube_url}")
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    proxies = {"http": "http://127.0.0.1:1081", "https": "http://127.0.0.1:1081"}
    session = requests.Session()
    session.proxies = proxies

    # Step 1: Get media list
    resp = session.post(
        "https://app.ytdown.to/proxy.php",
        data={"url": youtube_url},
        headers={"User-Agent": ua},
        timeout=15,
    )
    data = resp.json()
    items = data["api"]["mediaItems"]

    # Step 2: Find 480p item
    target = next((m for m in items if m.get("mediaRes") == "854x480"), items[0])
    print(f"Selected: {target['mediaQuality']} {target.get('mediaRes', 'audio')}")

    # Step 3: Resolve download URL (retry if still processing)
    max_retries = 5
    for attempt in range(max_retries):
        print(f"Requesting: {target['mediaUrl']}")
        resp2 = session.get(target["mediaUrl"], headers={"User-Agent": ua}, timeout=15)
        try:
            detail = resp2.json()
            file_url = detail.get("fileUrl", "")
        except (ValueError, RequestException):
            file_url = resp2.text
        if file_url and not any(kw in file_url for kw in ("Waiting", "Processing")):
            break
        print(f"ytdown processing... retry {attempt + 1}/{max_retries}")
        time.sleep(3)
    else:
        print(f"Failed to resolve download URL after {max_retries} retries: {file_url}")
        sys.exit(1)

    print(f"Got Download URL: {file_url}")

    # Step 4: Download video with progress
    resp3 = session.get(
        file_url,
        headers={"User-Agent": ua, "Referer": "https://app.ytdown.to/"},
        timeout=120,
        stream=True,
    )
    total = int(resp3.headers.get("Content-Length", 0))
    downloaded = 0
    start_time = time.time()
    is_tty = sys.stderr.isatty()

    def _progress(downloaded, elapsed, total):
        speed = downloaded / elapsed / 1024 / 1024 if elapsed > 0 else 0
        if total:
            pct = downloaded / total * 100
            bar_len = 30
            filled = int(bar_len * downloaded / total)
            bar = "█" * filled + "░" * (bar_len - filled)
            remaining = (total - downloaded) / (speed * 1024 * 1024) if speed > 0 else 0
            eta = f"{int(remaining // 60)}:{int(remaining % 60):02d}"
            return f"[{bar}] {pct:5.1f}%  {downloaded / 1024 / 1024:.1f}/{total / 1024 / 1024:.1f}MB  {speed:.1f}MB/s  ETA {eta}"
        else:
            return f"{downloaded / 1024 / 1024:.1f}MB  {speed:.1f}MB/s"

    last_report = 0.0
    with open(output_path, "wb") as f:
        for chunk in resp3.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                elapsed = time.time() - start_time
                if is_tty:
                    sys.stderr.write(f"\r  {_progress(downloaded, elapsed, total)}  ")
                    sys.stderr.flush()
                elif elapsed - last_report >= 5:
                    print(f"  {_progress(downloaded, elapsed, total)}")
                    last_report = elapsed

    if is_tty:
        sys.stderr.write("\n")
    elapsed = time.time() - start_time
    print(f"Downloaded: {downloaded / 1024 / 1024:.1f}MB in {elapsed:.1f}s ({downloaded / elapsed / 1024 / 1024:.1f}MB/s avg)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <youtube_url> <output_mp4_path>")
        sys.exit(1)

    youtube_url = sys.argv[1]
    output_path = sys.argv[2]

    if os.path.exists(output_path):
        print(f"{output_path} already exists, skip")
        sys.exit(0)

    download_video(youtube_url, output_path)
