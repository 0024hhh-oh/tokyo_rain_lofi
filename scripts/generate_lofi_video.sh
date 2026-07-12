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
LOOP_CROSSFADE_SECONDS="${LOOP_CROSSFADE_SECONDS:-1.5}"
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
BACKGROUND_FILE="$ASSET_DIR/background_seamless.mp4"


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

generate_seamless_background() {
  local source_path="$1"
  local output_path="$2"
  local crossfade_seconds="$3"
  local preset="$4"
  local crf="$5"
  local duration has_audio offset loop_duration start_epoch end_epoch elapsed

  duration="$(ffprobe_duration_seconds "$source_path")"
  if has_audio_stream "$source_path"; then
    has_audio="yes"
  else
    has_audio="no"
  fi

  echo "Original background duration seconds: $duration"
  echo "Loop crossfade seconds: $crossfade_seconds"
  echo "Background audio stream: $has_audio"

  read -r offset loop_duration < <(python - "$duration" "$crossfade_seconds" <<'PY_LOOP_VALIDATE'
import sys
from decimal import Decimal, InvalidOperation
try:
    duration = Decimal(sys.argv[1])
    crossfade = Decimal(sys.argv[2])
except InvalidOperation as exc:
    raise SystemExit(f"Invalid loop duration/crossfade value: {exc}") from exc
if duration <= 0:
    raise SystemExit(f"Background duration must be positive: {duration}")
if crossfade <= 0:
    raise SystemExit(f"LOOP_CROSSFADE_SECONDS must be positive: {crossfade}")
if duration <= crossfade * 2:
    raise SystemExit(
        f"Background video is too short for seamless loop generation: "
        f"duration={duration}s, LOOP_CROSSFADE_SECONDS={crossfade}s, "
        f"required duration > {crossfade * 2}s"
    )
print(format(duration - (crossfade * 2), "f"), format(duration - crossfade, "f"))
PY_LOOP_VALIDATE
  )

  echo "Seamless loop generation starting: $source_path -> $output_path"
  start_epoch="$(date +%s)"
  rm -f "$output_path"

  local filter_complex
  local -a seamless_cmd
  if [[ "$has_audio" == "yes" ]]; then
    filter_complex="[0:v]trim=start=${crossfade_seconds},setpts=PTS-STARTPTS[loop_main_v];[0:v]trim=start=0:duration=${crossfade_seconds},setpts=PTS-STARTPTS[loop_head_v];[loop_main_v][loop_head_v]xfade=transition=fade:duration=${crossfade_seconds}:offset=${offset},format=yuv420p[vout];[0:a]atrim=start=${crossfade_seconds},asetpts=PTS-STARTPTS[loop_main_a];[0:a]atrim=start=0:duration=${crossfade_seconds},asetpts=PTS-STARTPTS[loop_head_a];[loop_main_a][loop_head_a]acrossfade=d=${crossfade_seconds}:c1=tri:c2=tri[aout]"
    seamless_cmd=(
      ffmpeg -y -i "$source_path"
      -filter_complex "$filter_complex"
      -map "[vout]" -map "[aout]"
      -c:v libx264 -preset "$preset" -crf "$crf" -pix_fmt yuv420p
      -c:a aac -b:a 192k -ar 48000
      -movflags +faststart
      "$output_path"
    )
  else
    filter_complex="[0:v]trim=start=${crossfade_seconds},setpts=PTS-STARTPTS[loop_main_v];[0:v]trim=start=0:duration=${crossfade_seconds},setpts=PTS-STARTPTS[loop_head_v];[loop_main_v][loop_head_v]xfade=transition=fade:duration=${crossfade_seconds}:offset=${offset},format=yuv420p[vout]"
    seamless_cmd=(
      ffmpeg -y -i "$source_path"
      -filter_complex "$filter_complex"
      -map "[vout]"
      -c:v libx264 -preset "$preset" -crf "$crf" -pix_fmt yuv420p
      -movflags +faststart
      "$output_path"
    )
  fi

  echo "Seamless FFmpeg command:"
  printf ' %q' "${seamless_cmd[@]}"
  echo
  if ! "${seamless_cmd[@]}"; then
    echo "Seamless loop generation failed for $source_path" >&2
    return 1
  fi
  if [[ ! -f "$output_path" ]]; then
    echo "Seamless loop output was not created: $output_path" >&2
    return 1
  fi
  end_epoch="$(date +%s)"
  elapsed=$((end_epoch - start_epoch))
  echo "Seamless loop generation completed: $output_path"
  echo "Generated seamless loop duration seconds: $(ffprobe_duration_seconds "$output_path")"
  echo "Expected seamless loop duration seconds: $loop_duration"
  echo "Seamless FFmpeg execution time seconds: $elapsed"
}


generate_seamless_background "$SOURCE_BACKGROUND_FILE" "$BACKGROUND_FILE" "$LOOP_CROSSFADE_SECONDS" "$LOOP_PRESET" "$LOOP_CRF"

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

if has_audio_stream "$BACKGROUND_FILE"; then
  BACKGROUND_HAS_AUDIO="yes"
  BACKGROUND_AUDIO_LOOP_SAMPLES="$(python - "$BACKGROUND_FILE" <<'PY_BACKGROUND_AUDIO_LOOP'
import math
import subprocess
import sys
from decimal import Decimal, InvalidOperation

path = sys.argv[1]


def ffprobe_duration(args):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            *args,
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""

value = ffprobe_duration(["-select_streams", "a:0", "-show_entries", "stream=duration"])
if value in {"", "N/A"}:
    value = ffprobe_duration(["-show_entries", "format=duration"])

try:
    duration = Decimal(value)
except InvalidOperation as exc:
    raise SystemExit(f"Invalid background audio duration from ffprobe for {path}: {value}") from exc

if duration <= 0:
    raise SystemExit(f"Background audio duration must be positive for {path}: {value}")

# The filtergraph resamples background audio to 48 kHz before aloop, so aloop's
# size must be expressed in 48 kHz samples. Round up to preserve the full loop.
print(math.ceil(float(duration) * 48000))
PY_BACKGROUND_AUDIO_LOOP
)"
else
  BACKGROUND_HAS_AUDIO="no"
  BACKGROUND_AUDIO_LOOP_SAMPLES="0"
fi

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
  seamless_background=$BACKGROUND_FILE
  output=$OUTPUT_PATH
  suno_seconds=$SUNO_TOTAL_SECONDS
  rain_outro_seconds=$RAIN_OUTRO_SECONDS
  video_seconds=$VIDEO_TOTAL_SECONDS
  suno_track_count=${#TRACKS[@]}
  background_audio_volume=$BACKGROUND_AUDIO_VOLUME
  bgm_volume=$BGM_VOLUME
  audio_limit=$AUDIO_LIMIT
  background_audio_stream=$BACKGROUND_HAS_AUDIO
  background_audio_loop_samples=$BACKGROUND_AUDIO_LOOP_SAMPLES
  loop_crossfade_seconds=$LOOP_CROSSFADE_SECONDS
  loop_preset=$LOOP_PRESET
  loop_crf=$LOOP_CRF

Visual processing intentionally disabled:
  waveform=disabled
  rain_overlay=disabled
  film_grain=disabled
  film_dust=disabled
  color_correction=disabled
  logo=disabled
  video_filters=disabled

The generated seamless background video is treated as the completed video source.
The actual long-form background file is $BACKGROUND_FILE.
The video stream is looped and copied without FFmpeg video filters or re-encoding.
Its audio is looped to the total video duration and kept at the same volume for both the main program and the outro. The concatenated Suno BGM is not looped; it is padded with silence after its natural end so only the original background rain audio remains for the configured outro duration.
EOF_STATUS

log_media_metadata "Source background video" "$SOURCE_BACKGROUND_FILE"
log_media_metadata "Selected seamless background loop video" "$BACKGROUND_FILE"
echo "Long-form generation background file: $BACKGROUND_FILE"

if [[ "$BACKGROUND_HAS_AUDIO" == "yes" ]]; then
  ffmpeg_cmd=(
    ffmpeg -y
    -stream_loop -1 -i "$BACKGROUND_FILE"
    -f concat -safe 0 -i "$CONCAT_FILE"
    -filter_complex "[0:a]aresample=48000,aloop=loop=-1:size=${BACKGROUND_AUDIO_LOOP_SAMPLES},atrim=0:${VIDEO_TOTAL_SECONDS},asetpts=N/SR/TB,volume=${BACKGROUND_AUDIO_VOLUME}[background_audio];[1:a]atrim=0:${SUNO_TOTAL_SECONDS},asetpts=N/SR/TB,volume=${BGM_VOLUME},apad,atrim=0:${VIDEO_TOTAL_SECONDS}[suno_bgm];[background_audio][suno_bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=${AUDIO_LIMIT}[audio_out]"
    -map 0:v:0 -map "[audio_out]"
    -t "$VIDEO_TOTAL_SECONDS"
    -c:v copy
    -c:a aac -b:a 192k -ar 48000
    -movflags +faststart
    "$OUTPUT_PATH"
  )
else
  ffmpeg_cmd=(
    ffmpeg -y
    -stream_loop -1 -i "$BACKGROUND_FILE"
    -f concat -safe 0 -i "$CONCAT_FILE"
    -filter_complex "[1:a]atrim=0:${SUNO_TOTAL_SECONDS},asetpts=N/SR/TB,volume=${BGM_VOLUME},apad,atrim=0:${VIDEO_TOTAL_SECONDS},alimiter=limit=${AUDIO_LIMIT}[audio_out]"
    -map 0:v:0 -map "[audio_out]"
    -t "$VIDEO_TOTAL_SECONDS"
    -c:v copy
    -c:a aac -b:a 192k -ar 48000
    -movflags +faststart
    "$OUTPUT_PATH"
  )
fi

echo "FFmpeg command:"
printf ' %q' "${ffmpeg_cmd[@]}"
echo

"${ffmpeg_cmd[@]}"

if [[ ! -f "$OUTPUT_PATH" ]]; then
  echo "Output was not created: $OUTPUT_PATH" >&2
  exit 1
fi

log_media_metadata "Generated MP4" "$OUTPUT_PATH"
