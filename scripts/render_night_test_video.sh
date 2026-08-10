#!/usr/bin/env bash
set -euo pipefail

ASSET_DIR="${ASSET_DIR:-video_assets}"
OUTPUT_DIR="${OUTPUT_DIR:-dist}"
OUTPUT_FILE="${OUTPUT_FILE:-night-test.mp4}"
BACKGROUND_VIDEO="$ASSET_DIR/background.mp4"
TRACK_FILE="$ASSET_DIR/tracks/night-test.mp3"
OUTPUT_PATH="$OUTPUT_DIR/$OUTPUT_FILE"
MOTION_MIN_YAVG="${MOTION_MIN_YAVG:-0.08}"
NIGHT_TEST_SECONDS="${NIGHT_TEST_SECONDS:-30}"
MOTION_FIRST_SECOND="${MOTION_FIRST_SECOND:-0.2}"
MOTION_SECOND_SECOND="${MOTION_SECOND_SECOND:-$(python - "$NIGHT_TEST_SECONDS" <<'PY'
import sys
print(max(0.4, float(sys.argv[1]) / 2))
PY
)}"

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
motion_log="$(mktemp)"
trap 'rm -f "$motion_log"' EXIT

ffmpeg -v error \
  -ss "$MOTION_FIRST_SECOND" -i "$BACKGROUND_VIDEO" \
  -ss "$MOTION_SECOND_SECOND" -i "$BACKGROUND_VIDEO" \
  -filter_complex "[0:v][1:v]blend=all_mode=difference,signalstats,metadata=print:file=${motion_log}" \
  -frames:v 1 -f null -

motion_yavg="$(awk -F= '/lavfi.signalstats.YAVG=/{print $2; exit}' "$motion_log")"
python - "$motion_yavg" "$MOTION_MIN_YAVG" <<'PY'
import sys

actual = float(sys.argv[1]) if sys.argv[1] else 0.0
minimum = float(sys.argv[2])
if actual < minimum:
    raise SystemExit(
        f"night-test motion check failed: YAVG difference {actual:.6f} < {minimum:.6f}"
    )
print(f"night-test motion verified: YAVG difference={actual:.6f}")
PY

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
