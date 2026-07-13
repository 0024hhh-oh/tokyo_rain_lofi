#!/usr/bin/env bash
set -euo pipefail

ASSET_DIR="${ASSET_DIR:-video_assets}"
TRACK_DIR="$ASSET_DIR/tracks"
OUTPUT_DIR="${OUTPUT_DIR:-dist}"
OUTPUT_FILE="${OUTPUT_FILE:-Tokyo_Memory_Archive_001.mp4}"
BGM_VOLUME="${BGM_VOLUME:-1.0}"
RAIN_AUDIO_VOLUME="${RAIN_AUDIO_VOLUME:-0.20}"
AUDIO_LIMIT="${AUDIO_LIMIT:-0.98}"
RAIN_OUTRO_SECONDS="${RAIN_OUTRO_SECONDS:-5}"
VIDEO_EDGE_FADE_SECONDS="${VIDEO_EDGE_FADE_SECONDS:-1}"
VIDEO_PRESET="${VIDEO_PRESET:-veryfast}"
VIDEO_CRF="${VIDEO_CRF:-22}"
VIDEO_WIDTH="${VIDEO_WIDTH:-1920}"
VIDEO_HEIGHT="${VIDEO_HEIGHT:-1080}"
VIDEO_FPS="${VIDEO_FPS:-30}"
RAIN_AUDIO_SOURCE="${RAIN_AUDIO_SOURCE:-$ASSET_DIR/rain_audio_source.mp4}"

CONCAT_FILE="$OUTPUT_DIR/suno_tracks_concat.txt"
OUTPUT_PATH="$OUTPUT_DIR/$OUTPUT_FILE"
mkdir -p "$OUTPUT_DIR"

ffprobe_duration_seconds() {
  ffprobe -v error -show_entries format=duration     -of default=noprint_wrappers=1:nokey=1 "$1"
}

has_video_stream() {
  [[ -n "$(ffprobe -v error -select_streams v:0     -show_entries stream=index -of csv=p=0 "$1" | head -n 1)" ]]
}

has_audio_stream() {
  [[ -n "$(ffprobe -v error -select_streams a:0     -show_entries stream=index -of csv=p=0 "$1" | head -n 1)" ]]
}

select_background_file() {
  local candidate
  for candidate in     "$ASSET_DIR/background.mp4"     "$ASSET_DIR/background_loop.mp4"     "$ASSET_DIR/background.mov"     "$ASSET_DIR/background_loop.mov"     "$ASSET_DIR/background.png"     "$ASSET_DIR/background.jpg"     "$ASSET_DIR/background.jpeg"
  do
    if [[ -s "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  echo "Missing background video/image in $ASSET_DIR" >&2
  return 1
}

BACKGROUND_FILE="$(select_background_file)"
if [[ ! -s "$RAIN_AUDIO_SOURCE" ]]; then
  echo "Missing shared rain audio source: $RAIN_AUDIO_SOURCE" >&2
  exit 1
fi
if ! has_audio_stream "$RAIN_AUDIO_SOURCE"; then
  echo "Shared rain source has no audio stream: $RAIN_AUDIO_SOURCE" >&2
  exit 1
fi

mapfile -t TRACKS < <(find "$TRACK_DIR" -maxdepth 1 -type f -iname '*.mp3' | sort)
if [[ "${#TRACKS[@]}" -eq 0 ]]; then
  echo "Missing Suno mp3 tracks in: $TRACK_DIR" >&2
  exit 1
fi

: > "$CONCAT_FILE"
for track in "${TRACKS[@]}"; do
  printf "file '%s'\n" "$(realpath "$track")" >> "$CONCAT_FILE"
done

SUNO_TOTAL_SECONDS="$(python - "${TRACKS[@]}" <<'PY_DURATION'
import subprocess
import sys
from decimal import Decimal

total = Decimal("0")
for path in sys.argv[1:]:
    value = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    duration = Decimal(value)
    if duration <= 0:
        raise SystemExit(f"Track duration must be positive for {path}: {value}")
    total += duration
print(format(total, "f"))
PY_DURATION
)"

VIDEO_TOTAL_SECONDS="$(python - "$SUNO_TOTAL_SECONDS" "$RAIN_OUTRO_SECONDS" <<'PY_TOTAL'
import sys
from decimal import Decimal

suno = Decimal(sys.argv[1])
outro = Decimal(sys.argv[2])
if suno <= 0:
    raise SystemExit(f"Suno duration must be positive: {suno}")
if outro < 0:
    raise SystemExit(f"Rain outro duration must be non-negative: {outro}")
print(format(suno + outro, "f"))
PY_TOTAL
)"

FADE_OUT_START="$(python - "$VIDEO_TOTAL_SECONDS" "$VIDEO_EDGE_FADE_SECONDS" <<'PY_FADE'
import sys
from decimal import Decimal

total = Decimal(sys.argv[1])
fade = Decimal(sys.argv[2])
if fade < 0:
    raise SystemExit(f"Video fade must be non-negative: {fade}")
print(format(max(Decimal("0"), total - fade), "f"))
PY_FADE
)"

RAIN_SOURCE_SECONDS="$(ffprobe_duration_seconds "$RAIN_AUDIO_SOURCE")"
BACKGROUND_KIND="video"
BACKGROUND_INPUT_ARGS=(-stream_loop -1 -i "$BACKGROUND_FILE")
if ! has_video_stream "$BACKGROUND_FILE"; then
  case "${BACKGROUND_FILE,,}" in
    *.png|*.jpg|*.jpeg)
      BACKGROUND_KIND="image"
      BACKGROUND_INPUT_ARGS=(-loop 1 -framerate "$VIDEO_FPS" -i "$BACKGROUND_FILE")
      ;;
    *)
      echo "Background source has no video stream: $BACKGROUND_FILE" >&2
      exit 1
      ;;
  esac
fi

VIDEO_FILTER="[0:v]fps=${VIDEO_FPS},scale=${VIDEO_WIDTH}:${VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop=${VIDEO_WIDTH}:${VIDEO_HEIGHT},setsar=1,trim=0:${VIDEO_TOTAL_SECONDS},setpts=PTS-STARTPTS"
if [[ "$VIDEO_EDGE_FADE_SECONDS" != "0" ]]; then
  VIDEO_FILTER+=",fade=t=in:st=0:d=${VIDEO_EDGE_FADE_SECONDS},fade=t=out:st=${FADE_OUT_START}:d=${VIDEO_EDGE_FADE_SECONDS}"
fi
VIDEO_FILTER+=",format=yuv420p[vout]"

AUDIO_FILTER="[1:a]aresample=48000,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,atrim=0:${VIDEO_TOTAL_SECONDS},asetpts=PTS-STARTPTS,volume=${RAIN_AUDIO_VOLUME}[rain_audio];[2:a]aresample=48000,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,atrim=0:${SUNO_TOTAL_SECONDS},asetpts=PTS-STARTPTS,volume=${BGM_VOLUME},apad,atrim=0:${VIDEO_TOTAL_SECONDS}[suno_bgm];[rain_audio][suno_bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=${AUDIO_LIMIT}[audio_out]"
FINAL_FILTER="${VIDEO_FILTER};${AUDIO_FILTER}"

cat <<EOF_STATUS
Separate rain audio generation mode:
  background_file=$BACKGROUND_FILE
  background_kind=$BACKGROUND_KIND
  background_audio_ignored=yes
  rain_audio_source=$RAIN_AUDIO_SOURCE
  rain_audio_source_seconds=$RAIN_SOURCE_SECONDS
  rain_audio_loop_strategy=stream-loop-without-crossfade
  suno_track_count=${#TRACKS[@]}
  suno_seconds=$SUNO_TOTAL_SECONDS
  rain_outro_seconds=$RAIN_OUTRO_SECONDS
  video_seconds=$VIDEO_TOTAL_SECONDS
  rain_audio_volume=$RAIN_AUDIO_VOLUME
  output=$OUTPUT_PATH
EOF_STATUS

ffmpeg_cmd=(
  ffmpeg -y
  "${BACKGROUND_INPUT_ARGS[@]}"
  -stream_loop -1 -i "$RAIN_AUDIO_SOURCE"
  -f concat -safe 0 -i "$CONCAT_FILE"
  -filter_complex "$FINAL_FILTER"
  -map '[vout]' -map '[audio_out]'
  -t "$VIDEO_TOTAL_SECONDS"
  -c:v libx264 -preset "$VIDEO_PRESET" -crf "$VIDEO_CRF" -pix_fmt yuv420p
  -c:a aac -b:a 192k -ar 48000
  -movflags +faststart
  "$OUTPUT_PATH"
)

printf 'FFmpeg command:'
printf ' %q' "${ffmpeg_cmd[@]}"
echo
"${ffmpeg_cmd[@]}"

if [[ ! -s "$OUTPUT_PATH" ]]; then
  echo "Output was not created or is empty: $OUTPUT_PATH" >&2
  exit 1
fi
if ! has_video_stream "$OUTPUT_PATH"; then
  echo "Output is missing a video stream: $OUTPUT_PATH" >&2
  exit 1
fi
if ! has_audio_stream "$OUTPUT_PATH"; then
  echo "Output is missing an audio stream: $OUTPUT_PATH" >&2
  exit 1
fi

OUTPUT_SECONDS="$(ffprobe_duration_seconds "$OUTPUT_PATH")"
python - "$OUTPUT_SECONDS" "$VIDEO_TOTAL_SECONDS" <<'PY_VALIDATE_OUTPUT'
import sys
from decimal import Decimal

actual = Decimal(sys.argv[1])
expected = Decimal(sys.argv[2])
if actual <= 0:
    raise SystemExit(f"Output duration must be positive: {actual}")
if abs(actual - expected) > Decimal("0.2"):
    raise SystemExit(
        f"Output duration mismatch: actual={actual}s expected={expected}s tolerance=0.2s"
    )
PY_VALIDATE_OUTPUT

ffprobe -v error   -show_entries format=filename,duration,size,bit_rate   -of default=noprint_wrappers=1 "$OUTPUT_PATH"
