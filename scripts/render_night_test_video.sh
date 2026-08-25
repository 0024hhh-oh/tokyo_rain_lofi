#!/usr/bin/env bash
set -euo pipefail

ASSET_DIR="${ASSET_DIR:-video_assets}"
OUTPUT_DIR="${OUTPUT_DIR:-dist}"
OUTPUT_FILE="${OUTPUT_FILE:-night-test.mp4}"
BACKGROUND_VIDEO="$ASSET_DIR/background.mp4"
TRACK_FILE="$ASSET_DIR/tracks/night-test.mp3"
OUTPUT_PATH="$OUTPUT_DIR/$OUTPUT_FILE"
NIGHT_TEST_SECONDS="${NIGHT_TEST_SECONDS:-30}"

echo "night-test stage=remotion-render"
bash scripts/render_night_background.sh

test -s "$BACKGROUND_VIDEO" || {
  echo "night-test render failed: animated background video was not created" >&2
  exit 1
}
test -s "$TRACK_FILE" || {
  echo "night-test render failed: downloaded MP3 is missing" >&2
  exit 1
}

mkdir -p "$OUTPUT_DIR"
validation_dir="$(mktemp -d)"
trap 'rm -rf "$validation_dir"' EXIT
# Compare one steady frame with the three approved irregular lighting events.
validation_seconds=(0.30 0.92 3.00 3.75)
validation_frames=()
for index in "${!validation_seconds[@]}"; do
  frame="$validation_dir/frame-${index}.png"
  ffmpeg -v error -ss "${validation_seconds[$index]}" -i "$BACKGROUND_VIDEO" \
    -frames:v 1 "$frame"
  validation_frames+=("$frame")
done
node scripts/validate_visible_lighting.mjs \
  src/generated-light-zones.json "${validation_frames[@]}"

ffmpeg -y \
  -i "$BACKGROUND_VIDEO" \
  -stream_loop -1 -i "$TRACK_FILE" \
  -map 0:v:0 -map 1:a:0 \
  -t "$NIGHT_TEST_SECONDS" \
  -c:v copy \
  -c:a aac -b:a 192k -ar 48000 \
  -movflags +faststart \
  "$OUTPUT_PATH"

duration="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUTPUT_PATH")"
audio_codec="$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$OUTPUT_PATH")"
python - "$duration" "$audio_codec" "$NIGHT_TEST_SECONDS" <<'PY'
import sys

duration = float(sys.argv[1])
audio_codec = sys.argv[2].strip()
expected = float(sys.argv[3])
if abs(duration - expected) > 0.1:
    raise SystemExit(f"night-test duration must be {expected} seconds; got {duration}")
if not audio_codec:
    raise SystemExit("night-test output has no audio stream")
print(f"night-test output verified: duration={duration:.3f}s audio={audio_codec}")
PY
