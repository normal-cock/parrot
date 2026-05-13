#!/usr/bin/env python3
"""Download subtitles from downsub.com via browser + API."""
import json, requests, time, sys, os, glob, subprocess, shutil

def find_browse():
    browse = shutil.which('browse')
    if not browse:
        print('ERROR: browse CLI not found')
        sys.exit(1)
    return browse

def get_turnstile_data(youtube_url, browse_bin, timeout=60):
    """Open downsub.com in browser and capture the Turnstile data payload."""
    # Clean old network captures
    net_dir = '/tmp/browse-default-network'
    if os.path.exists(net_dir):
        subprocess.run(['rm', '-rf', net_dir], capture_output=True)

    # Start browser and enable network capture
    subprocess.run([browse_bin, 'env', 'local'], capture_output=True, timeout=10)
    subprocess.run([browse_bin, 'network', 'on'], capture_output=True, timeout=10)

    # Open downsub.com
    downsub_url = f'https://downsub.com/?url={youtube_url.replace(":", "%3A").replace("/", "%2F").replace("?", "%3F").replace("=", "%3D")}'
    result = subprocess.run([browse_bin, 'open', downsub_url], capture_output=True, text=True, timeout=30)
    print(f'Browser opened: {downsub_url[:100]}...')

    # Wait for the POST to get.downsub.com to appear
    deadline = time.time() + timeout
    while time.time() < deadline:
        post_dirs = sorted(glob.glob(f'{net_dir}/*POST-get.downsub.com-root*'))
        if post_dirs:
            req_file = os.path.join(post_dirs[-1], 'request.json')
            if os.path.exists(req_file):
                with open(req_file) as f:
                    req = json.load(f)
                body = json.loads(req.get('body', '{}'))
                if body.get('data'):
                    print(f'Captured Turnstile data ({len(body["data"])} chars)')
                    return body
        time.sleep(2)

    print('ERROR: Timed out waiting for Turnstile data')
    sys.exit(1)

def download_srt(youtube_url, turnstile_data, output_path):
    """POST to get.downsub.com and download SRT file."""
    proxies = {'http': 'http://127.0.0.1:1081', 'https': 'http://127.0.0.1:1081'}
    ua = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
    session = requests.Session()
    session.proxies = proxies
    session.headers.update({'User-Agent': ua, 'Referer': 'https://downsub.com/'})

    # POST to get subtitle token
    resp = session.post('https://get.downsub.com/', json={
        'url': youtube_url,
        'data': turnstile_data
    }, timeout=30)
    result = resp.json()

    subtitles = result.get('subtitles', [])
    eng = next((s for s in subtitles if 'English' in s.get('name', '')), None)
    if not eng:
        eng = subtitles[0] if subtitles else None
    if not eng:
        print(f'ERROR: No subtitles found. Response state={result.get("state")}')
        sys.exit(1)

    print(f'Found subtitle: {eng["name"]}')

    # Download SRT
    srt_url = f'https://subtitle.downsub.com/srt/{eng["url"]}'
    srt_resp = session.get(srt_url, timeout=30)

    if srt_resp.status_code != 200:
        print(f'ERROR: Failed to download SRT, status={srt_resp.status_code}')
        sys.exit(1)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(srt_resp.text)

    print(f'Downloaded SRT: {output_path} ({len(srt_resp.text)} chars)')
    return True

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <youtube_url> <output_srt_path>')
        sys.exit(1)

    youtube_url = sys.argv[1]
    output_path = sys.argv[2]

    if os.path.exists(output_path):
        print(f'{output_path} already exists, skip')
        sys.exit(0)

    browse_bin = find_browse()
    turnstile = get_turnstile_data(youtube_url, browse_bin)
    download_srt(youtube_url, turnstile['data'], output_path)
