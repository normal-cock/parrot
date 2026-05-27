#!/bin/bash
set -euo pipefail

URL="$1"
NAME="$2"
REPO="/data00/repos/parrot"
DIR="$REPO/tmp/$NAME"
SKILL_DIR="$REPO/.claude/skills/import"

if [ -z "$URL" ] || [ -z "$NAME" ]; then
    echo "Usage: import.sh <youtube_url> <name>"
    exit 1
fi

echo "=== Step 0: Create directory ==="
mkdir -p "$DIR"
cd "$DIR"

# Load proxy_on/proxy_off from ~/.bashrc
eval "$(sed -n '/^proxy_on()/,/^}/p; /^proxy_off()/,/^}/p' /home/work/.bashrc)"

echo "=== Step 1.1: Download video via ytdown.io (480p) ==="
if [ -f "${NAME}-raw.mp4" ]; then
    echo "${NAME}-raw.mp4 already exists, skip"
else
    proxy_on
    PYTHONUNBUFFERED=1 python3 -u "$SKILL_DIR/scripts/ytdown_download.py" "$URL" "${NAME}-raw.mp4"
    proxy_off
fi

echo "=== Step 1.2: Normalize audio ==="
if [ -f "${NAME}.mp4" ]; then
    echo "${NAME}.mp4 already exists, skip"
else
    ffmpeg -i "${NAME}-raw.mp4" -af "loudnorm=I=-16:LRA=11:TP=-1" \
        -c:v copy -c:a aac -b:a 192k -y "${NAME}.mp4"
fi

echo "=== Step 1.3: Extract MP3 ==="
if [ -f "${NAME}.mp3" ]; then
    echo "${NAME}.mp3 already exists, skip"
else
    ffmpeg -i "${NAME}.mp4" -vn -acodec libmp3lame "${NAME}.mp3"
fi

echo "=== Step 1.4: Generate M3U8 ==="
if [ -f "${NAME}.m3u8" ]; then
    echo "${NAME}.m3u8 already exists, skip"
else
    mkdir -p ts_file && ffmpeg -i "${NAME}.mp3" -hls_time 20 -hls_list_size 0 \
    -hls_segment_filename "ts_file/${NAME}-%d.ts" \
    -hls_base_url 'ts_file/' "${NAME}.m3u8"
fi

echo "=== Step 2: Subtitles ==="
RAW_SRT="${NAME}-raw.srt"
if [ -f "$RAW_SRT" ]; then
    echo "Found $RAW_SRT"
else
    echo "Downloading subtitles from downsub.com..."
    if python3 "$SKILL_DIR/scripts/downsub_download.py" "$URL" "$RAW_SRT"; then
        echo "Subtitle download complete"
    else
        echo "Warning: Auto-download failed."
        echo "Please download subtitles manually from https://downsub.com/ and save as ${DIR}/${RAW_SRT}"
    fi
fi

if [ -f "$RAW_SRT" ]; then
    echo "Converting SRT to VTT..."
    cp "$RAW_SRT" "$REPO/tmp/"
    make -C "$REPO" convert_subtitle_from_srt
    for vtt in "$REPO/tmp"/*.vtt; do
        if [ -f "$vtt" ]; then
            cp "$vtt" "${NAME}-raw.vtt"
        fi
    done
    rm -f "$REPO/tmp"/*.srt "$REPO/tmp"/*.vtt
fi

echo "=== Step 2.3: Convert subtitle to UTF-8 ==="
if [ -f "${NAME}-raw.vtt" ]; then
    python3 -c "
import sys
with open('${NAME}-raw.vtt', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()
with open('${NAME}-raw.vtt', 'w', encoding='utf-8') as f:
    f.write(content)
print('UTF-8 conversion done')
"
else
    echo "Warning: ${NAME}-raw.vtt not found, skipping UTF-8 conversion"
fi

echo "=== Step 2.4: Translate subtitles to Chinese (make translate_vtt) ==="
if [ -f "${NAME}-raw.vtt" ]; then
    cd "$REPO"
    PYTHONPATH=. python3 -c "
from parrot_v2.dal.doubao_llm import trans_vtt
import pysubs2, os

name = '${NAME}'
dir_ = '${DIR}'
raw_vtt = os.path.join(dir_, f'{name}-raw.vtt')
e_vtt = os.path.join(dir_, f'{name}-e.vtt')
c_vtt = os.path.join(dir_, f'{name}-c.vtt')

# Save English version (cleaned UTF-8 copy of raw)
subs = pysubs2.load(raw_vtt)
subs.save(e_vtt, format_='vtt')
print(f'Saved English VTT: {e_vtt}')

# Translate to Chinese
err = trans_vtt(raw_vtt, c_vtt)
if err:
    print(f'Translation error: {err}')
else:
    print(f'Saved Chinese VTT: {c_vtt}')
"
else
    echo "Warning: ${NAME}-raw.vtt not found, skipping translation"
fi

echo ""
echo "=== Done! ==="
echo "Files in $DIR:"
ls -lah "$DIR"
