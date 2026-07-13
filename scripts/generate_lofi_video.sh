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
ENABLE_RAIN_OVERLAY="${ENABLE_RAIN_OVERLAY:-1}"
RAIN_OVERLAY_OPACITY="${RAIN_OVERLAY_OPACITY:-0.55}"
RAIN_DENSITY_THRESHOLD="${RAIN_DENSITY_THRESHOLD:-0.996}"
LOOP_PRESET="${LOOP_PRESET:-veryfast}"
LOOP_CRF="${LOOP_CRF:-22}"
CROSSFADED_BACKGROUND_AUDIO_CODEC="${CROSSFADED_BACKGROUND_AUDIO_CODEC:-aac}"

CONCAT_FILE="$OUTPUT_DIR/suno_tracks_concat.txt"
TRIMMED_BACKGROUND_LOOP_FILE="$OUTPUT_DIR/trimmed_background_loop.mp4"
BACKGROUND_AUDIO_LOOP_FILE="$OUTPUT_DIR/crossfaded_background_audio.m4a"
BACKGROUND_AUDIO_LOOP_STATUS="not-attempted"
BACKGROUND_AUDIO_LOOP_EXPECTED_SECONDS="0"
BACKGROUND_LOOP_TRIM_START_SECONDS="${BACKGROUND_LOOP_TRIM_START_SECONDS:-$VIDEO_EDGE_FADE_SECONDS}"
BACKGROUND_LOOP_TRIM_END_SECONDS="${BACKGROUND_LOOP_TRIM_END_SECONDS:-$VIDEO_EDGE_FADE_SECONDS}"
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

audio_duration_seconds() {
  local duration
  duration="$(ffprobe -v error -select_streams a:0 -show_entries stream=duration -of default=noprint_wrappers=1:nokey=1 "$1" | head -n 1)"
  python - "$duration" "$1" <<'PY_AUDIO_DURATION_FALLBACK'
import subprocess
import sys
from decimal import Decimal, InvalidOperation

try:
    duration = Decimal(sys.argv[1])
except (IndexError, InvalidOperation):
    duration = Decimal("0")
if duration <= 0:
    value = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", sys.argv[2]],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    duration = Decimal(value)
print(format(duration, "f"))
PY_AUDIO_DURATION_FALLBACK
}

has_positive_audio_duration() {
  local duration
  duration="$(audio_duration_seconds "$1")"
  python - "$duration" <<'PY_AUDIO_DURATION'
import sys
from decimal import Decimal, InvalidOperation

try:
    duration = Decimal(sys.argv[1])
except (IndexError, InvalidOperation):
    raise SystemExit(1)
raise SystemExit(0 if duration > 0 else 1)
PY_AUDIO_DURATION
}

has_video_stream() {
  [[ -n "$(ffprobe -v error -select_streams v:0 -show_entries stream=index -of csv=p=0 "$1" | head -n 1)" ]]
}

validate_crossfaded_audio_loop() {
  local file="$1"
  local expected_duration="$2"
  local actual_duration

  if [[ ! -s "$file" ]]; then
    echo "Crossfaded background audio file is missing or empty: $file" >&2
    return 1
  fi
  if ! has_audio_stream "$file"; then
    echo "Crossfaded background audio file has no audio stream: $file" >&2
    return 1
  fi

  actual_duration="$(audio_duration_seconds "$file")"
  if ! python - "$actual_duration" "$expected_duration" <<'PY_VALIDATE_CROSSFADE_DURATION'
import sys
from decimal import Decimal, InvalidOperation

try:
    actual = Decimal(sys.argv[1])
    expected = Decimal(sys.argv[2])
except (IndexError, InvalidOperation):
    raise SystemExit(1)

tolerance = Decimal("0.1")
if actual <= 0 or expected <= 0:
    raise SystemExit(1)
raise SystemExit(0 if abs(actual - expected) <= tolerance else 1)
PY_VALIDATE_CROSSFADE_DURATION
  then
    echo "Crossfaded background audio duration validation failed: actual=${actual_duration}s expected=${expected_duration}s tolerance=0.1s" >&2
    return 1
  fi
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
  if ! has_positive_audio_duration "$file"; then
    echo "${context} audio stream has no positive duration: $file" >&2
    return 1
  fi
}

SOURCE_BACKGROUND_FILE="$(select_background_file)"
SOURCE_BACKGROUND_DURATION_SECONDS="$(ffprobe_duration_seconds "$SOURCE_BACKGROUND_FILE")"

TRIMMED_BACKGROUND_DURATION_SECONDS="$(python - "$SOURCE_BACKGROUND_DURATION_SECONDS" "$BACKGROUND_LOOP_TRIM_START_SECONDS" "$BACKGROUND_LOOP_TRIM_END_SECONDS" <<'PY_TRIM_DURATION'
import sys
from decimal import Decimal

duration = Decimal(sys.argv[1])
trim_start = Decimal(sys.argv[2])
trim_end = Decimal(sys.argv[3])
if duration <= 0:
    raise SystemExit(f"Background duration must be positive: {duration}")
if trim_start < 0 or trim_end < 0:
    raise SystemExit(
        f"Background loop trim values must be non-negative: "
        f"start={trim_start}, end={trim_end}"
    )
trimmed = duration - trim_start - trim_end
if trimmed <= 0:
    raise SystemExit(
        f"Background loop trim removes the full source: "
        f"duration={duration}s, start={trim_start}s, end={trim_end}s"
    )
print(format(trimmed, "f"))
PY_TRIM_DURATION
)"

python - "$TRIMMED_BACKGROUND_DURATION_SECONDS" "$LOOP_CROSSFADE_SECONDS" <<'PY_VALIDATE'
import sys
from decimal import Decimal

duration = Decimal(sys.argv[1])
crossfade = Decimal(sys.argv[2])
if duration <= 0:
    raise SystemExit(f"Trimmed background duration must be positive: {duration}")
if crossfade <= 0:
    raise SystemExit(f"LOOP_CROSSFADE_SECONDS must be positive: {crossfade}")
if duration <= crossfade * 2:
    raise SystemExit(
        f"Trimmed background loop is too short: duration={duration}s, "
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

LOOP_DURATION_SECONDS="$(python - "$TRIMMED_BACKGROUND_DURATION_SECONDS" "$LOOP_CROSSFADE_SECONDS" <<'PY_LOOP'
import sys
from decimal import Decimal
print(format(Decimal(sys.argv[1]) - Decimal(sys.argv[2]), "f"))
PY_LOOP
)"

has_video_stream "$SOURCE_BACKGROUND_FILE" || { echo "Background source is missing a video stream: $SOURCE_BACKGROUND_FILE" >&2; exit 1; }

trimmed_background_cmd=(
  ffmpeg -y
  -ss "$BACKGROUND_LOOP_TRIM_START_SECONDS"
  -t "$TRIMMED_BACKGROUND_DURATION_SECONDS"
  -i "$SOURCE_BACKGROUND_FILE"
  -map 0:v:0
)
if has_audio_stream "$SOURCE_BACKGROUND_FILE"; then
  trimmed_background_cmd+=(
    -map 0:a:0
    -c:a aac -b:a 192k -ar 48000
  )
else
  trimmed_background_cmd+=(
    -an
  )
fi
trimmed_background_cmd+=(
  -c:v libx264 -preset "$LOOP_PRESET" -crf "$LOOP_CRF" -pix_fmt yuv420p
  -movflags +faststart
  "$TRIMMED_BACKGROUND_LOOP_FILE"
)

printf 'Trimmed background loop command:'
printf ' %q' "${trimmed_background_cmd[@]}"
echo
"${trimmed_background_cmd[@]}"

if has_audio_stream "$TRIMMED_BACKGROUND_LOOP_FILE"; then
  BACKGROUND_HAS_AUDIO="yes"
  BACKGROUND_AUDIO_DURATION_SECONDS="$(audio_duration_seconds "$TRIMMED_BACKGROUND_LOOP_FILE")"
else
  BACKGROUND_HAS_AUDIO="no"
  BACKGROUND_AUDIO_DURATION_SECONDS="0"
fi

if [[ "$BACKGROUND_HAS_AUDIO" == "yes" ]]; then
  python - "$BACKGROUND_AUDIO_DURATION_SECONDS" "$LOOP_CROSSFADE_SECONDS" <<'PY_VALIDATE_AUDIO_LOOP'
import sys
from decimal import Decimal

duration = Decimal(sys.argv[1])
crossfade = Decimal(sys.argv[2])
if duration <= crossfade * 2:
    raise SystemExit(
        f"Background audio is too short for loop crossfade: "
        f"duration={duration}s, crossfade={crossfade}s; required duration > {crossfade * 2}s"
    )
PY_VALIDATE_AUDIO_LOOP
  BACKGROUND_AUDIO_LOOP_EXPECTED_SECONDS="$(python - "$BACKGROUND_AUDIO_DURATION_SECONDS" "$LOOP_CROSSFADE_SECONDS" <<'PY_AUDIO_LOOP_DURATION'
import sys
from decimal import Decimal
print(format(Decimal(sys.argv[1]) - Decimal(sys.argv[2]), "f"))
PY_AUDIO_LOOP_DURATION
)"
  BACKGROUND_AUDIO_MID_END_SECONDS="$BACKGROUND_AUDIO_LOOP_EXPECTED_SECONDS"
  BACKGROUND_AUDIO_HEAD_DELAY_SAMPLES="$(python - "$BACKGROUND_AUDIO_MID_END_SECONDS" <<'PY_HEAD_DELAY_SAMPLES'
import sys
from decimal import Decimal, ROUND_HALF_UP
print((Decimal(sys.argv[1]) * Decimal("48000")).to_integral_value(rounding=ROUND_HALF_UP))
PY_HEAD_DELAY_SAMPLES
)"
  # Keep the early head samples buffered until the late tail branch is available.
  # Without this sample-accurate delay, FFmpeg can drain the shared asplit head
  # before acrossfade starts pulling it and produce an empty seam.
  audio_loop_filter="[0:a]asplit=3[amid][atail][ahead];[amid]atrim=start=${LOOP_CROSSFADE_SECONDS}:end=${BACKGROUND_AUDIO_MID_END_SECONDS},asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[amid_t];[atail]atrim=start=${BACKGROUND_AUDIO_MID_END_SECONDS}:end=${BACKGROUND_AUDIO_DURATION_SECONDS},asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[atail_t];[ahead]atrim=start=0:end=${LOOP_CROSSFADE_SECONDS},asetpts=PTS-STARTPTS,adelay=${BACKGROUND_AUDIO_HEAD_DELAY_SAMPLES}S:all=1,atrim=start=${BACKGROUND_AUDIO_MID_END_SECONDS}:end=${BACKGROUND_AUDIO_DURATION_SECONDS},asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[ahead_t];[atail_t][ahead_t]acrossfade=d=${LOOP_CROSSFADE_SECONDS}:c1=tri:c2=tri[aseam];[amid_t][aseam]concat=n=2:v=0:a=1[out]"
  rm -f "$BACKGROUND_AUDIO_LOOP_FILE"
  if ! ffmpeg -y -i "$TRIMMED_BACKGROUND_LOOP_FILE" \
    -filter_complex "$audio_loop_filter" \
    -map '[out]' -vn \
    -t "$BACKGROUND_AUDIO_LOOP_EXPECTED_SECONDS" \
    -c:a "$CROSSFADED_BACKGROUND_AUDIO_CODEC" -b:a 192k -ar 48000 \
    -movflags +faststart "$BACKGROUND_AUDIO_LOOP_FILE"; then
    echo "Crossfaded background audio loop generation failed; stopping before video generation: $BACKGROUND_AUDIO_LOOP_FILE" >&2
    rm -f "$BACKGROUND_AUDIO_LOOP_FILE"
    exit 1
  fi
  if ! validate_crossfaded_audio_loop "$BACKGROUND_AUDIO_LOOP_FILE" "$BACKGROUND_AUDIO_LOOP_EXPECTED_SECONDS"; then
    echo "Crossfaded background audio loop validation failed; stopping before video generation: $BACKGROUND_AUDIO_LOOP_FILE" >&2
    rm -f "$BACKGROUND_AUDIO_LOOP_FILE"
    exit 1
  fi
  BACKGROUND_AUDIO_LOOP_STATUS="generated"
else
  BACKGROUND_AUDIO_LOOP_STATUS="not-required-no-background-audio"
fi

has_video_stream "$TRIMMED_BACKGROUND_LOOP_FILE" || { echo "Trimmed background loop is missing a video stream: $TRIMMED_BACKGROUND_LOOP_FILE" >&2; exit 1; }


FADE_OUT_START="$(python - "$VIDEO_TOTAL_SECONDS" "$VIDEO_EDGE_FADE_SECONDS" <<'PY_FADE'
import sys
from decimal import Decimal
print(format(max(Decimal("0"), Decimal(sys.argv[1]) - Decimal(sys.argv[2])), "f"))
PY_FADE
)"

if [[ "$ENABLE_RAIN_OVERLAY" == "1" ]]; then
  video_filter="[0:v]split=2[video_source][rain_seed];[video_source]trim=0:${VIDEO_TOTAL_SECONDS},setpts=PTS-STARTPTS,fps=30,fade=t=in:st=0:d=${VIDEO_EDGE_FADE_SECONDS},fade=t=out:st=${FADE_OUT_START}:d=${VIDEO_EDGE_FADE_SECONDS},format=yuv420p[video_base];[rain_seed]select='eq(n,0)',geq=lum='if(gt(random(1)\,${RAIN_DENSITY_THRESHOLD})\,255\,0)':cb=128:cr=128,gblur=sigma=0.3:sigmaV=6,lutyuv=y='min(val*5\,255)',loop=loop=-1:size=1:start=0,setpts=N/30/TB,scroll=horizontal=-0.003:vertical=0.04,trim=0:${VIDEO_TOTAL_SECONDS},format=yuv420p[rain_layer];[video_base][rain_layer]blend=all_mode=screen:all_opacity=${RAIN_OVERLAY_OPACITY},format=yuv420p[vout]"
  RAIN_OVERLAY_STATUS="generated-visible-rain"
else
  video_filter="[0:v]trim=0:${VIDEO_TOTAL_SECONDS},setpts=PTS-STARTPTS,fade=t=in:st=0:d=${VIDEO_EDGE_FADE_SECONDS},fade=t=out:st=${FADE_OUT_START}:d=${VIDEO_EDGE_FADE_SECONDS},format=yuv420p[vout]"
  RAIN_OVERLAY_STATUS="disabled"
fi

if [[ "$BACKGROUND_HAS_AUDIO" == "yes" ]]; then
  final_filter="${video_filter};[1:a]atrim=0:${VIDEO_TOTAL_SECONDS},asetpts=PTS-STARTPTS,volume=${BACKGROUND_AUDIO_VOLUME}[background_audio];[2:a]atrim=0:${SUNO_TOTAL_SECONDS},asetpts=PTS-STARTPTS,volume=${BGM_VOLUME},apad,atrim=0:${VIDEO_TOTAL_SECONDS}[suno_bgm];[background_audio][suno_bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=${AUDIO_LIMIT}[audio_out]"
else
  final_filter="${video_filter};[1:a]atrim=0:${SUNO_TOTAL_SECONDS},asetpts=PTS-STARTPTS,volume=${BGM_VOLUME},apad,atrim=0:${VIDEO_TOTAL_SECONDS},alimiter=limit=${AUDIO_LIMIT}[audio_out]"
fi

cat <<EOF_STATUS
Minimal video generation mode:
  source_background=$SOURCE_BACKGROUND_FILE
  trimmed_background_loop_file=$TRIMMED_BACKGROUND_LOOP_FILE
  background_audio_loop_file=$BACKGROUND_AUDIO_LOOP_FILE
  background_audio_input_file=$BACKGROUND_AUDIO_LOOP_FILE
  background_audio_loop_status=$BACKGROUND_AUDIO_LOOP_STATUS
  output=$OUTPUT_PATH
  suno_seconds=$SUNO_TOTAL_SECONDS
  video_seconds=$VIDEO_TOTAL_SECONDS
  source_background_duration_seconds=$SOURCE_BACKGROUND_DURATION_SECONDS
  background_loop_trim_start_seconds=$BACKGROUND_LOOP_TRIM_START_SECONDS
  background_loop_trim_end_seconds=$BACKGROUND_LOOP_TRIM_END_SECONDS
  trimmed_background_duration_seconds=$TRIMMED_BACKGROUND_DURATION_SECONDS
  background_audio_duration_seconds=$BACKGROUND_AUDIO_DURATION_SECONDS
  seamless_loop_duration_seconds=$LOOP_DURATION_SECONDS
  loop_crossfade_seconds=$LOOP_CROSSFADE_SECONDS
  background_audio_stream=$BACKGROUND_HAS_AUDIO
  rain_overlay_status=$RAIN_OVERLAY_STATUS
  rain_overlay_opacity=$RAIN_OVERLAY_OPACITY
  rain_density_threshold=$RAIN_DENSITY_THRESHOLD
  loop_strategy=trimmed-video-loop-with-audio-only-crossfade
EOF_STATUS

if [[ "$BACKGROUND_HAS_AUDIO" == "yes" ]]; then
  ffmpeg_cmd=(
    ffmpeg -y
    -stream_loop -1 -i "$TRIMMED_BACKGROUND_LOOP_FILE"
    -stream_loop -1 -i "$BACKGROUND_AUDIO_LOOP_FILE"
    -f concat -safe 0 -i "$CONCAT_FILE"
    -filter_complex "$final_filter"
    -map '[vout]' -map '[audio_out]'
    -t "$VIDEO_TOTAL_SECONDS"
    -c:v libx264 -preset "$LOOP_PRESET" -crf "$LOOP_CRF" -pix_fmt yuv420p
    -c:a aac -b:a 192k -ar 48000
    -movflags +faststart
    "$OUTPUT_PATH"
  )
else
  ffmpeg_cmd=(
    ffmpeg -y
    -stream_loop -1 -i "$TRIMMED_BACKGROUND_LOOP_FILE"
    -f concat -safe 0 -i "$CONCAT_FILE"
    -filter_complex "$final_filter"
    -map '[vout]' -map '[audio_out]'
    -t "$VIDEO_TOTAL_SECONDS"
    -c:v libx264 -preset "$LOOP_PRESET" -crf "$LOOP_CRF" -pix_fmt yuv420p
    -c:a aac -b:a 192k -ar 48000
    -movflags +faststart
    "$OUTPUT_PATH"
  )
fi

printf 'FFmpeg command:'
printf ' %q' "${ffmpeg_cmd[@]}"
echo
"${ffmpeg_cmd[@]}"

[[ -f "$OUTPUT_PATH" ]] || { echo "Output was not created: $OUTPUT_PATH" >&2; exit 1; }
ffprobe -v error -show_entries format=filename,duration,size,bit_rate -of default=noprint_wrappers=1 "$OUTPUT_PATH"
