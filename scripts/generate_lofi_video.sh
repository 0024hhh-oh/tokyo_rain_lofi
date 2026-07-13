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

SOURCE_BACKGROUND_FILE=""
BACKGROUND_FILE=""
CONCAT_FILE="$OUTPUT_DIR/suno_tracks_concat.txt"
OUTPUT_PATH="$OUTPUT_DIR/$OUTPUT_FILE"

mkdir -p "$OUTPUT_DIR"

select_background_file() {
  local -a exact_mp4 exact_mov videos
  mapfile -t exact_mp4 < <(find "$ASSET_DIR" -maxdepth 1 -type f -name 'background.mp4' | sort)
  if [[ "${#exact_mp4[@]}" -gt 0 ]]; then
    printf '%s\n' "${exact_mp4[0]}"
    return 0
  fi

  mapfile -t exact_mov < <(find "$ASSET_DIR" -maxdepth 1 -type f \( -name 'background_loop.mov' -o -name 'background_loop.MOV' \) | sort)
  if [[ "${#exact_mov[@]}" -gt 0 ]]; then
    printf '%s\n' "${exact_mov[0]}"
    return 0
  fi

  mapfile -t videos < <(find "$ASSET_DIR" -maxdepth 1 -type f \( -iname '*.mp4' -o -iname '*.mov' \) | sort)
  if [[ "${#videos[@]}" -eq 1 ]]; then
    printf '%s\n' "${videos[0]}"
    return 0
  fi

  if [[ "${#videos[@]}" -gt 1 ]]; then
    echo "Multiple background video candidates found. Rename the intended file to background_loop.mp4 or background_loop.mov." >&2
  else
    echo "Missing background video in $ASSET_DIR (expected background.mp4, background_loop.mov, or exactly one .mp4/.mov file)." >&2
  fi
  return 1
}

SOURCE_BACKGROUND_FILE="$(select_background_file)"
BACKGROUND_FILE="$SOURCE_BACKGROUND_FILE"


ffprobe_duration_seconds() {
  local path="$1"
  ffprobe -v error \
    -show_entries format=duration \
    -of default=noprint_wrappers=1:nokey=1 \
    "$path"
}

has_audio_stream() {
  local path="$1"
  [[ "$(ffprobe -v error -select_streams a:0 -show_entries stream=index -of csv=p=0 "$path" | head -n 1)" != "" ]]
}

calculate_background_loop_plan() {
  local source_path="$1"
  local total_seconds="$2"
  local crossfade_seconds="$3"

  python - "$source_path" "$total_seconds" "$crossfade_seconds" <<'PY_LOOP_PLAN'
import math
import subprocess
import sys
from decimal import Decimal, InvalidOperation

path, total_arg, crossfade_arg = sys.argv[1:4]

result = subprocess.run(
    [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ],
    check=True,
    text=True,
    capture_output=True,
)
try:
    duration = Decimal(result.stdout.strip())
    total = Decimal(total_arg)
    crossfade = Decimal(crossfade_arg)
except InvalidOperation as exc:
    raise SystemExit(f"Invalid duration/crossfade value: {exc}") from exc

if duration <= 0:
    raise SystemExit(f"Background duration must be positive: {duration}")
if total <= 0:
    raise SystemExit(f"Final video duration must be positive: {total}")
if crossfade <= 0:
    raise SystemExit(f"LOOP_CROSSFADE_SECONDS must be positive: {crossfade}")
if duration <= crossfade:
    raise SystemExit(
        f"Background video is too short for loop crossfades: "
        f"duration={duration}s, LOOP_CROSSFADE_SECONDS={crossfade}s, "
        f"required duration > {crossfade}s"
    )

step = duration - crossfade
if total <= duration:
    loop_count = 1
else:
    loop_count = 1 + math.ceil(float((total - duration) / step))

print(format(duration, "f"), loop_count, format(duration - crossfade, "f"))
PY_LOOP_PLAN
}

build_loop_filter_complex() {
  local source_path="$1"
  local total_seconds="$2"
  local suno_total_seconds="$3"
  local crossfade_seconds="$4"
  local background_has_audio="$5"
  local background_audio_volume="$6"
  local bgm_volume="$7"
  local audio_limit="$8"
  local edge_fade_seconds="$9"

  python - "$source_path" "$total_seconds" "$suno_total_seconds" "$crossfade_seconds" "$background_has_audio" "$background_audio_volume" "$bgm_volume" "$audio_limit" "$edge_fade_seconds" <<'PY_FILTER'
import math
import subprocess
import sys
from decimal import Decimal, InvalidOperation

(
    path,
    total_arg,
    suno_arg,
    crossfade_arg,
    has_audio,
    background_volume,
    bgm_volume,
    audio_limit,
    edge_fade_arg,
) = sys.argv[1:10]

result = subprocess.run(
    [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ],
    check=True,
    text=True,
    capture_output=True,
)
try:
    duration = Decimal(result.stdout.strip())
    total = Decimal(total_arg)
    suno_total = Decimal(suno_arg)
    crossfade = Decimal(crossfade_arg)
    edge_fade = Decimal(edge_fade_arg)
except InvalidOperation as exc:
    raise SystemExit(f"Invalid duration/crossfade value: {exc}") from exc

if duration <= 0:
    raise SystemExit(f"Background duration must be positive: {duration}")
if total <= 0:
    raise SystemExit(f"Final video duration must be positive: {total}")
if crossfade <= 0:
    raise SystemExit(f"LOOP_CROSSFADE_SECONDS must be positive: {crossfade}")
if duration <= crossfade:
    raise SystemExit(
        f"Background video is too short for loop crossfades: duration={duration}s, "
        f"LOOP_CROSSFADE_SECONDS={crossfade}s, required duration > {crossfade}s"
    )
if edge_fade < 0:
    raise SystemExit(f"VIDEO_EDGE_FADE_SECONDS must be non-negative: {edge_fade}")

step = duration - crossfade
loop_count = 1 if total <= duration else 1 + math.ceil(float((total - duration) / step))
if loop_count == 1:
    parts = ["[0:v]setpts=PTS-STARTPTS[v0]"]
    if has_audio == "yes":
        parts.append("[0:a]aresample=48000,asetpts=N/SR/TB[a0]")
else:
    parts = [f"[0:v]split={loop_count}" + "".join(f"[v{i}]" for i in range(loop_count))]
    if has_audio == "yes":
        parts.append(f"[0:a]aresample=48000,asplit={loop_count}" + "".join(f"[a{i}]" for i in range(loop_count)))

video_current = "v0"
current_duration = duration
for i in range(1, loop_count):
    offset = current_duration - crossfade
    out = f"vx{i}"
    parts.append(
        f"[{video_current}][v{i}]xfade=transition=fade:duration={crossfade}:offset={offset}[{out}]"
    )
    video_current = out
    current_duration += duration - crossfade

fade_out_start = max(Decimal("0"), total - edge_fade)
video_filters = [f"[{video_current}]trim=0:{total},setpts=PTS-STARTPTS"]
if edge_fade > 0:
    video_filters.append(f"fade=t=in:st=0:d={edge_fade}")
    video_filters.append(f"fade=t=out:st={fade_out_start}:d={edge_fade}")
video_filters.append("format=yuv420p[vout]")
parts.append(",".join(video_filters))

if has_audio == "yes":
    audio_current = "a0"
    for i in range(1, loop_count):
        out = f"ax{i}"
        parts.append(f"[{audio_current}][a{i}]acrossfade=d={crossfade}:c1=tri:c2=tri[{out}]")
        audio_current = out
    parts.append(
        f"[{audio_current}]atrim=0:{total},asetpts=N/SR/TB,volume={background_volume}[background_audio]"
    )
    parts.append(
        f"[1:a]atrim=0:{suno_total},asetpts=N/SR/TB,volume={bgm_volume},apad,atrim=0:{total}[suno_bgm]"
    )
    parts.append(
        f"[background_audio][suno_bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit={audio_limit}[audio_out]"
    )
else:
    parts.append(
        f"[1:a]atrim=0:{suno_total},asetpts=N/SR/TB,volume={bgm_volume},apad,atrim=0:{total},alimiter=limit={audio_limit}[audio_out]"
    )

print(";".join(parts))
PY_FILTER
}


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
from decimal import Decimal, InvalidOperation

total = Decimal("0")
for path in sys.argv[1:]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    value = result.stdout.strip()
    try:
        duration = Decimal(value)
    except InvalidOperation as exc:
        raise SystemExit(f"Invalid duration from ffprobe for {path}: {value}") from exc
    if duration <= 0:
        raise SystemExit(f"Track duration must be positive for {path}: {value}")
    total += duration

if total <= 0:
    raise SystemExit("Total Suno track duration must be positive.")

print(format(total, "f"))
PY_DURATION
)"

VIDEO_TOTAL_SECONDS="$(python - "$SUNO_TOTAL_SECONDS" "$RAIN_OUTRO_SECONDS" <<'PY_VIDEO_DURATION'
import sys
from decimal import Decimal, InvalidOperation

try:
    suno_total = Decimal(sys.argv[1])
    rain_outro = Decimal(sys.argv[2])
except InvalidOperation as exc:
    raise SystemExit(f"Invalid duration value: {exc}") from exc

if rain_outro < 0:
    raise SystemExit(f"Rain outro duration must be non-negative: {rain_outro}")

print(format(suno_total + rain_outro, "f"))
PY_VIDEO_DURATION
)"

if has_audio_stream "$SOURCE_BACKGROUND_FILE"; then
  BACKGROUND_HAS_AUDIO="yes"
else
  BACKGROUND_HAS_AUDIO="no"
fi

read -r BACKGROUND_DURATION_SECONDS BACKGROUND_LOOP_COUNT BACKGROUND_LOOP_OFFSET_SECONDS < <(calculate_background_loop_plan "$SOURCE_BACKGROUND_FILE" "$VIDEO_TOTAL_SECONDS" "$LOOP_CROSSFADE_SECONDS")
FILTER_COMPLEX="$(build_loop_filter_complex "$SOURCE_BACKGROUND_FILE" "$VIDEO_TOTAL_SECONDS" "$SUNO_TOTAL_SECONDS" "$LOOP_CROSSFADE_SECONDS" "$BACKGROUND_HAS_AUDIO" "$BACKGROUND_AUDIO_VOLUME" "$BGM_VOLUME" "$AUDIO_LIMIT" "$VIDEO_EDGE_FADE_SECONDS")"


log_media_metadata() {
  local label="$1"
  local path="$2"

  echo "$label: $path"
  if command -v ffprobe >/dev/null 2>&1; then
    ffprobe -v error \
      -show_entries format=filename,format_name,duration,size,bit_rate \
      -show_entries stream=index,codec_type,codec_name,width,height,avg_frame_rate,duration,bit_rate \
      -of default=noprint_wrappers=1 "$path" || true
  else
    echo "ffprobe not found; skipping metadata for $path" >&2
  fi
}

cat <<EOF_STATUS
Minimal video generation mode:
  source_background=$SOURCE_BACKGROUND_FILE
  video source: $SOURCE_BACKGROUND_FILE
  rain audio source: $SOURCE_BACKGROUND_FILE
  rain audio stream detected: $BACKGROUND_HAS_AUDIO
  output=$OUTPUT_PATH
  suno_seconds=$SUNO_TOTAL_SECONDS
  rain_outro_seconds=$RAIN_OUTRO_SECONDS
  video_seconds=$VIDEO_TOTAL_SECONDS
  suno_track_count=${#TRACKS[@]}
  background_audio_volume=$BACKGROUND_AUDIO_VOLUME
  bgm_volume=$BGM_VOLUME
  audio_limit=$AUDIO_LIMIT
  background_audio_stream=$BACKGROUND_HAS_AUDIO
  background_duration_seconds=$BACKGROUND_DURATION_SECONDS
  background_loop_count=$BACKGROUND_LOOP_COUNT
  loop_crossfade_seconds=$LOOP_CROSSFADE_SECONDS
  loop_offset_seconds=$BACKGROUND_LOOP_OFFSET_SECONDS
  video_edge_fade_seconds=$VIDEO_EDGE_FADE_SECONDS
  loop_preset=$LOOP_PRESET
  loop_crf=$LOOP_CRF

Visual processing intentionally disabled:
  waveform=disabled
  rain_overlay=disabled
  film_grain=disabled
  film_dust=disabled
  color_correction=disabled
  logo=disabled

The source rain MP4 contains both video and rain audio.
Each loop boundary is crossfaded with FFmpeg xfade for video and acrossfade for rain audio.
The loop offset is calculated automatically from the rain video duration and LOOP_CROSSFADE_SECONDS.
The final output is trimmed to VIDEO_TOTAL_SECONDS after dynamic loop assembly.
The concatenated Suno BGM is not looped; it is padded with silence after its natural end so only the original background rain audio remains for the configured outro duration.
EOF_STATUS

log_media_metadata "Source background video" "$SOURCE_BACKGROUND_FILE"
log_media_metadata "Selected seamless background loop video" "$BACKGROUND_FILE"
echo "Long-form generation background file: $BACKGROUND_FILE"
echo "Long-form rain audio file: $SOURCE_BACKGROUND_FILE"

ffmpeg_cmd=(
  ffmpeg -y
  -i "$SOURCE_BACKGROUND_FILE"
  -f concat -safe 0 -i "$CONCAT_FILE"
  -filter_complex "$FILTER_COMPLEX"
  -map "[vout]" -map "[audio_out]"
  -t "$VIDEO_TOTAL_SECONDS"
  -c:v libx264 -preset "$LOOP_PRESET" -crf "$LOOP_CRF" -pix_fmt yuv420p
  -c:a aac -b:a 192k -ar 48000
  -movflags +faststart
  "$OUTPUT_PATH"
)

echo "FFmpeg command:"
printf ' %q' "${ffmpeg_cmd[@]}"
echo

"${ffmpeg_cmd[@]}"

if [[ ! -f "$OUTPUT_PATH" ]]; then
  echo "Output was not created: $OUTPUT_PATH" >&2
  exit 1
fi

log_media_metadata "Generated MP4" "$OUTPUT_PATH"
