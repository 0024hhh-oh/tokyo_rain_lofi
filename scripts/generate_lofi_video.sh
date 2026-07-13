#!/usr/bin/env bash
set -euo pipefail

ASSET_DIR="${ASSET_DIR:-video_assets}"
TRACK_DIR="$ASSET_DIR/tracks"
OUTPUT_DIR="${OUTPUT_DIR:-dist}"
OUTPUT_FILE="${OUTPUT_FILE:-Tokyo_Memory_Archive_001.mp4}"
BGM_VOLUME="${BGM_VOLUME:-1.0}"
BACKGROUND_AUDIO_VOLUME="${BACKGROUND_AUDIO_VOLUME:-1.0}"
AUDIO_LIMIT="${AUDIO_LIMIT:-0.98}"
RAIN_OUTRO_SECONDS="${RAIN_OUTRO_SECONDS:-5}"
LOOP_CROSSFADE_SECONDS="${LOOP_CROSSFADE_SECONDS:-1}"
VIDEO_EDGE_FADE_SECONDS="${VIDEO_EDGE_FADE_SECONDS:-1}"
LOOP_PRESET="${LOOP_PRESET:-veryfast}"
LOOP_CRF="${LOOP_CRF:-22}"

CONCAT_FILE="$OUTPUT_DIR/suno_tracks_concat.txt"
SEAMLESS_LOOP_FILE="$OUTPUT_DIR/seamless_background_loop.mp4"
OUTPUT_PATH="$OUTPUT_DIR/$OUTPUT_FILE"
mkdir -p "$OUTPUT_DIR"

select_background_file() {
  local -a exact_mp4 exact_mov videos
  mapfile -t exact_mp4 < <(find "$ASSET_DIR" -maxdepth 1 -type f -name 'background.mp4' | sort)
  if [[ "${#exact_mp4[@]}" -gt 0 ]]; then printf '%s\n' "${exact_mp4[0]}"; return 0; fi

  mapfile -t exact_mov < <(find "$ASSET_DIR" -maxdepth 1 -type f \( -name 'background_loop.mov' -o -name 'background_loop.MOV' \) | sort)
  if [[ "${#exact_mov[@]}" -gt 0 ]]; then printf '%s\n' "${exact_mov[0]}"; return 0; fi

  mapfile -t videos < <(find "$ASSET_DIR" -maxdepth 1 -type f \( -iname '*.mp4' -o -iname '*.mov' \) | sort)
  if [[ "${#videos[@]}" -eq 1 ]]; then printf '%s\n' "${videos[0]}"; return 0; fi

  echo "Missing or ambiguous background video in $ASSET_DIR." >&2
  return 1
}

ffprobe_duration_seconds() {
  ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$1"
}

has_audio_stream() {
  [[ -n "$(ffprobe -v error -select_streams a:0 -show_entries stream=index -of csv=p=0 "$1" | head -n 1)" ]]
}

has_video_stream() {
  [[ -n "$(ffprobe -v error -select_streams v:0 -show_entries stream=index -of csv=p=0 "$1" | head -n 1)" ]]
}

require_video_and_audio_streams() {
  local file="$1"
  local context="$2"
  if ! has_video_stream "$file"; then
    echo "${context} is missing a video stream: $file" >&2
    return 1
  fi
  if ! has_audio_stream "$file"; then
    echo "${context} is missing an audio stream: $file" >&2
    return 1
  fi
}

SOURCE_BACKGROUND_FILE="$(select_background_file)"
BACKGROUND_DURATION_SECONDS="$(ffprobe_duration_seconds "$SOURCE_BACKGROUND_FILE")"

python - "$BACKGROUND_DURATION_SECONDS" "$LOOP_CROSSFADE_SECONDS" <<'PY_VALIDATE'
import sys
from decimal import Decimal

duration = Decimal(sys.argv[1])
crossfade = Decimal(sys.argv[2])
if duration <= 0:
    raise SystemExit(f"Background duration must be positive: {duration}")
if crossfade <= 0:
    raise SystemExit(f"LOOP_CROSSFADE_SECONDS must be positive: {crossfade}")
if duration <= crossfade * 2:
    raise SystemExit(
        f"Background video is too short: duration={duration}s, "
        f"crossfade={crossfade}s; required duration > {crossfade * 2}s"
    )
PY_VALIDATE

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
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
        check=True, text=True, capture_output=True,
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
if outro < 0:
    raise SystemExit(f"Rain outro duration must be non-negative: {outro}")
print(format(suno + outro, "f"))
PY_TOTAL
)"

LOOP_DURATION_SECONDS="$(python - "$BACKGROUND_DURATION_SECONDS" "$LOOP_CROSSFADE_SECONDS" <<'PY_LOOP'
import sys
from decimal import Decimal
print(format(Decimal(sys.argv[1]) - Decimal(sys.argv[2]), "f"))
PY_LOOP
)"

if has_audio_stream "$SOURCE_BACKGROUND_FILE"; then
  BACKGROUND_HAS_AUDIO="yes"
else
  BACKGROUND_HAS_AUDIO="no"
fi

VIDEO_XFADE_OFFSET="$(python - "$BACKGROUND_DURATION_SECONDS" "$LOOP_CROSSFADE_SECONDS" <<'PY_OFFSET'
import sys
from decimal import Decimal
print(format(Decimal(sys.argv[1]) - Decimal(sys.argv[2]) * 2, "f"))
PY_OFFSET
)"

if [[ "$BACKGROUND_HAS_AUDIO" == "yes" ]]; then
  seamless_filter="[0:v]split=2[vbody][vhead];[vbody]trim=start=${LOOP_CROSSFADE_SECONDS}:end=${BACKGROUND_DURATION_SECONDS},setpts=PTS-STARTPTS[vbody_t];[vhead]trim=start=0:end=${LOOP_CROSSFADE_SECONDS},setpts=PTS-STARTPTS[vhead_t];[vbody_t][vhead_t]xfade=transition=fade:duration=${LOOP_CROSSFADE_SECONDS}:offset=${VIDEO_XFADE_OFFSET},format=yuv420p[vloop];[0:a]asplit=2[abody][ahead];[abody]atrim=start=${LOOP_CROSSFADE_SECONDS}:end=${BACKGROUND_DURATION_SECONDS},asetpts=PTS-STARTPTS[abody_t];[ahead]atrim=start=0:end=${LOOP_CROSSFADE_SECONDS},asetpts=PTS-STARTPTS[ahead_t];[abody_t][ahead_t]acrossfade=d=${LOOP_CROSSFADE_SECONDS}:c1=tri:c2=tri[aloop]"
  ffmpeg -y -i "$SOURCE_BACKGROUND_FILE" \
    -filter_complex "$seamless_filter" \
    -map '[vloop]' -map '[aloop]' \
    -t "$LOOP_DURATION_SECONDS" \
    -c:v libx264 -preset "$LOOP_PRESET" -crf "$LOOP_CRF" -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 \
    -movflags +faststart "$SEAMLESS_LOOP_FILE"
else
  seamless_filter="[0:v]split=2[vbody][vhead];[vbody]trim=start=${LOOP_CROSSFADE_SECONDS}:end=${BACKGROUND_DURATION_SECONDS},setpts=PTS-STARTPTS[vbody_t];[vhead]trim=start=0:end=${LOOP_CROSSFADE_SECONDS},setpts=PTS-STARTPTS[vhead_t];[vbody_t][vhead_t]xfade=transition=fade:duration=${LOOP_CROSSFADE_SECONDS}:offset=${VIDEO_XFADE_OFFSET},format=yuv420p[vloop]"
  ffmpeg -y -i "$SOURCE_BACKGROUND_FILE" \
    -filter_complex "$seamless_filter" \
    -map '[vloop]' -an \
    -t "$LOOP_DURATION_SECONDS" \
    -c:v libx264 -preset "$LOOP_PRESET" -crf "$LOOP_CRF" -pix_fmt yuv420p \
    -movflags +faststart "$SEAMLESS_LOOP_FILE"
fi

if [[ "$BACKGROUND_HAS_AUDIO" == "yes" ]]; then
  require_video_and_audio_streams "$SEAMLESS_LOOP_FILE" "Seamless background loop" || {
    echo "Cannot run final FFmpeg because the loop generated from an audio-bearing background has no usable audio stream." >&2
    exit 1
  }
else
  has_video_stream "$SEAMLESS_LOOP_FILE" || { echo "Seamless background loop is missing a video stream: $SEAMLESS_LOOP_FILE" >&2; exit 1; }
fi

FADE_OUT_START="$(python - "$VIDEO_TOTAL_SECONDS" "$VIDEO_EDGE_FADE_SECONDS" <<'PY_FADE'
import sys
from decimal import Decimal
print(format(max(Decimal("0"), Decimal(sys.argv[1]) - Decimal(sys.argv[2])), "f"))
PY_FADE
)"

if [[ "$BACKGROUND_HAS_AUDIO" == "yes" ]]; then
  final_filter="[0:v]trim=0:${VIDEO_TOTAL_SECONDS},setpts=PTS-STARTPTS,fade=t=in:st=0:d=${VIDEO_EDGE_FADE_SECONDS},fade=t=out:st=${FADE_OUT_START}:d=${VIDEO_EDGE_FADE_SECONDS},format=yuv420p[vout];[0:a]atrim=0:${VIDEO_TOTAL_SECONDS},asetpts=PTS-STARTPTS,volume=${BACKGROUND_AUDIO_VOLUME}[background_audio];[1:a]atrim=0:${SUNO_TOTAL_SECONDS},asetpts=PTS-STARTPTS,volume=${BGM_VOLUME},apad,atrim=0:${VIDEO_TOTAL_SECONDS}[suno_bgm];[background_audio][suno_bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=${AUDIO_LIMIT}[audio_out]"
else
  final_filter="[0:v]trim=0:${VIDEO_TOTAL_SECONDS},setpts=PTS-STARTPTS,fade=t=in:st=0:d=${VIDEO_EDGE_FADE_SECONDS},fade=t=out:st=${FADE_OUT_START}:d=${VIDEO_EDGE_FADE_SECONDS},format=yuv420p[vout];[1:a]atrim=0:${SUNO_TOTAL_SECONDS},asetpts=PTS-STARTPTS,volume=${BGM_VOLUME},apad,atrim=0:${VIDEO_TOTAL_SECONDS},alimiter=limit=${AUDIO_LIMIT}[audio_out]"
fi

cat <<EOF_STATUS
Minimal video generation mode:
  source_background=$SOURCE_BACKGROUND_FILE
  seamless_loop_file=$SEAMLESS_LOOP_FILE
  output=$OUTPUT_PATH
  suno_seconds=$SUNO_TOTAL_SECONDS
  video_seconds=$VIDEO_TOTAL_SECONDS
  background_duration_seconds=$BACKGROUND_DURATION_SECONDS
  seamless_loop_duration_seconds=$LOOP_DURATION_SECONDS
  loop_crossfade_seconds=$LOOP_CROSSFADE_SECONDS
  background_audio_stream=$BACKGROUND_HAS_AUDIO
  loop_strategy=single-crossfade-then-stream-loop
EOF_STATUS

ffmpeg_cmd=(
  ffmpeg -y
  -stream_loop -1 -i "$SEAMLESS_LOOP_FILE"
  -f concat -safe 0 -i "$CONCAT_FILE"
  -filter_complex "$final_filter"
  -map '[vout]' -map '[audio_out]'
  -t "$VIDEO_TOTAL_SECONDS"
  -c:v libx264 -preset "$LOOP_PRESET" -crf "$LOOP_CRF" -pix_fmt yuv420p
  -c:a aac -b:a 192k -ar 48000
  -movflags +faststart
  "$OUTPUT_PATH"
)

printf 'FFmpeg command:'
printf ' %q' "${ffmpeg_cmd[@]}"
echo
"${ffmpeg_cmd[@]}"

[[ -f "$OUTPUT_PATH" ]] || { echo "Output was not created: $OUTPUT_PATH" >&2; exit 1; }
ffprobe -v error -show_entries format=filename,duration,size,bit_rate -of default=noprint_wrappers=1 "$OUTPUT_PATH"
