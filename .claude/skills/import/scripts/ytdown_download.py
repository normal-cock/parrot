#!/usr/bin/env python3
"""Download YouTube video (480p) via ytdown.io."""
import json, requests, time, sys, os
from requests.exceptions import RequestException


def download_video(youtube_url, output_path):
    ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36'
    proxies = {'http': 'http://127.0.0.1:1081', 'https': 'http://127.0.0.1:1081'}
    session = requests.Session()
    session.proxies = proxies

    # Step 1: Get media list
    resp = session.post(
        'https://app.ytdown.to/proxy.php',
        data={'url': youtube_url},
        headers={'User-Agent': ua},
        timeout=15
    )
    data = resp.json()
    items = data['api']['mediaItems']

    # Step 2: Find 480p item
    target = next((m for m in items if m.get('mediaRes') == '854x480'), items[0])
    print(f"Selected: {target['mediaQuality']} {target.get('mediaRes', 'audio')}")

    # Step 3: Resolve download URL (retry if still processing)
    max_retries = 5
    for attempt in range(max_retries):
        resp2 = session.get(target['mediaUrl'], headers={'User-Agent': ua}, timeout=15)
        try:
            detail = resp2.json()
            file_url = detail.get('fileUrl', '')
        except (ValueError, RequestException):
            file_url = resp2.text
        if file_url and not any(kw in file_url for kw in ('Waiting', 'Processing')):
            break
        print(f'ytdown processing... retry {attempt + 1}/{max_retries}')
        time.sleep(3)
    else:
        print(f'Failed to resolve download URL after {max_retries} retries: {file_url}')
        sys.exit(1)

    # Step 4: Download video
    resp3 = session.get(file_url, headers={'User-Agent': ua, 'Referer': 'https://app.ytdown.to/'}, timeout=120)
    with open(output_path, 'wb') as f:
        f.write(resp3.content)
    print('Downloaded: ' + detail.get('fileSize', str(len(resp3.content))))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <youtube_url> <output_mp4_path>')
        sys.exit(1)

    youtube_url = sys.argv[1]
    output_path = sys.argv[2]

    if os.path.exists(output_path):
        print(f'{output_path} already exists, skip')
        sys.exit(0)

    download_video(youtube_url, output_path)
