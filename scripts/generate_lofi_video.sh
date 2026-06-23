#!/usr/bin/env bash
set -euo pipefail

ASSET_DIR="${ASSET_DIR:-video_assets}"
TRACK_DIR="$ASSET_DIR/tracks"
OUTPUT_DIR="${OUTPUT_DIR:-dist}"
OUTPUT_FILE="${OUTPUT_FILE:-Tokyo_Memory_Archive_001.mp4}"
TARGET_SECONDS="${TARGET_SECONDS:-3600}"
mkdir -p "$OUTPUT_DIR"

CONCAT_FILE="$OUTPUT_DIR/tracks_concat.txt"
: > "$CONCAT_FILE"
for i in $(seq -w 1 20); do
  track="$TRACK_DIR/track${i}.mp3"
  if [[ ! -f "$track" ]]; then
    echo "Missing required track: $track" >&2
    exit 1
  fi
  printf "file '%s'\n" "$(realpath "$track")" >> "$CONCAT_FILE"
done

if [[ ! -f "$ASSET_DIR/background.png" ]]; then
  echo "Missing required background: $ASSET_DIR/background.png" >&2
  exit 1
fi
HAS_RAIN_AUDIO=0
if [[ -f "$ASSET_DIR/rain.mp3" ]]; then
  HAS_RAIN_AUDIO=1
else
  echo "Optional rain audio not found; generating video with BGM only: $ASSET_DIR/rain.mp3"
fi

HAS_RAIN_OVERLAY=0
if [[ -f "$ASSET_DIR/rain_overlay.mp4" ]]; then
  HAS_RAIN_OVERLAY=1
else
  echo "Optional rain overlay not found; continuing without overlay: $ASSET_DIR/rain_overlay.mp4"
fi

if [[ "$HAS_RAIN_AUDIO" -eq 1 && "$HAS_RAIN_OVERLAY" -eq 1 ]]; then
  ffmpeg -y \
    -stream_loop -1 -f concat -safe 0 -i "$CONCAT_FILE" \
    -stream_loop -1 -i "$ASSET_DIR/rain.mp3" \
    -loop 1 -i "$ASSET_DIR/background.png" \
    -stream_loop -1 -i "$ASSET_DIR/rain_overlay.mp4" \
    -filter_complex "[0:a]atrim=0:${TARGET_SECONDS},asetpts=N/SR/TB,volume=0.92[music];[1:a]atrim=0:${TARGET_SECONDS},asetpts=N/SR/TB,volume=0.16[rain];[music][rain]amix=inputs=2:duration=first:dropout_transition=3,alimiter=limit=0.95[aout];[2:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,format=rgba[bg];[3:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,format=rgba,colorchannelmixer=aa=0.28[ov];[bg][ov]overlay=0:0:shortest=0,format=yuv420p[vout]" \
    -map "[vout]" -map "[aout]" -t "$TARGET_SECONDS" \
    -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "$OUTPUT_DIR/$OUTPUT_FILE"
elif [[ "$HAS_RAIN_AUDIO" -eq 1 ]]; then
  ffmpeg -y \
    -stream_loop -1 -f concat -safe 0 -i "$CONCAT_FILE" \
    -stream_loop -1 -i "$ASSET_DIR/rain.mp3" \
    -loop 1 -i "$ASSET_DIR/background.png" \
    -filter_complex "[0:a]atrim=0:${TARGET_SECONDS},asetpts=N/SR/TB,volume=0.92[music];[1:a]atrim=0:${TARGET_SECONDS},asetpts=N/SR/TB,volume=0.16[rain];[music][rain]amix=inputs=2:duration=first:dropout_transition=3,alimiter=limit=0.95[aout];[2:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,format=yuv420p[vout]" \
    -map "[vout]" -map "[aout]" -t "$TARGET_SECONDS" \
    -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "$OUTPUT_DIR/$OUTPUT_FILE"
elif [[ "$HAS_RAIN_OVERLAY" -eq 1 ]]; then
  ffmpeg -y \
    -stream_loop -1 -f concat -safe 0 -i "$CONCAT_FILE" \
    -loop 1 -i "$ASSET_DIR/background.png" \
    -stream_loop -1 -i "$ASSET_DIR/rain_overlay.mp4" \
    -filter_complex "[0:a]atrim=0:${TARGET_SECONDS},asetpts=N/SR/TB,volume=0.92,alimiter=limit=0.95[aout];[1:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,format=rgba[bg];[2:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,format=rgba,colorchannelmixer=aa=0.28[ov];[bg][ov]overlay=0:0:shortest=0,format=yuv420p[vout]" \
    -map "[vout]" -map "[aout]" -t "$TARGET_SECONDS" \
    -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "$OUTPUT_DIR/$OUTPUT_FILE"
else
  ffmpeg -y \
    -stream_loop -1 -f concat -safe 0 -i "$CONCAT_FILE" \
    -loop 1 -i "$ASSET_DIR/background.png" \
    -filter_complex "[0:a]atrim=0:${TARGET_SECONDS},asetpts=N/SR/TB,volume=0.92,alimiter=limit=0.95[aout];[1:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,format=yuv420p[vout]" \
    -map "[vout]" -map "[aout]" -t "$TARGET_SECONDS" \
    -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "$OUTPUT_DIR/$OUTPUT_FILE"
fi
