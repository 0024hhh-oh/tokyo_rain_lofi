#!/usr/bin/env bash
set -euo pipefail

ASSET_DIR="${ASSET_DIR:-video_assets}"
TRACK_DIR="$ASSET_DIR/tracks"
OUTPUT_DIR="${OUTPUT_DIR:-dist}"
OUTPUT_FILE="${OUTPUT_FILE:-Tokyo_Memory_Archive_001.mp4}"
TARGET_SECONDS="${TARGET_SECONDS:-3600}"
BGM_VOLUME="${BGM_VOLUME:-1.0}"
BACKGROUND_AUDIO_VOLUME="${BACKGROUND_AUDIO_VOLUME:-1.0}"
AUDIO_LIMIT="${AUDIO_LIMIT:-0.98}"

BACKGROUND_FILE=""
CONCAT_FILE="$OUTPUT_DIR/suno_tracks_concat.txt"
OUTPUT_PATH="$OUTPUT_DIR/$OUTPUT_FILE"

mkdir -p "$OUTPUT_DIR"

select_background_file() {
  local -a exact_mp4 exact_mov videos
  mapfile -t exact_mp4 < <(find "$ASSET_DIR" -maxdepth 1 -type f -name 'background_loop.mp4' | sort)
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
    echo "Missing background video in $ASSET_DIR (expected background_loop.mp4, background_loop.mov, or exactly one .mp4/.mov file)." >&2
  fi
  return 1
}

BACKGROUND_FILE="$(select_background_file)"

mapfile -t TRACKS < <(find "$TRACK_DIR" -maxdepth 1 -type f -iname '*.mp3' | sort)
if [[ "${#TRACKS[@]}" -eq 0 ]]; then
  echo "Missing Suno mp3 tracks in: $TRACK_DIR" >&2
  exit 1
fi

: > "$CONCAT_FILE"
for track in "${TRACKS[@]}"; do
  printf "file '%s'\n" "$(realpath "$track")" >> "$CONCAT_FILE"
done

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
  background_loop=$BACKGROUND_FILE
  output=$OUTPUT_PATH
  target_seconds=$TARGET_SECONDS
  suno_track_count=${#TRACKS[@]}
  background_audio_volume=$BACKGROUND_AUDIO_VOLUME
  bgm_volume=$BGM_VOLUME
  audio_limit=$AUDIO_LIMIT

Visual processing intentionally disabled:
  waveform=disabled
  rain_overlay=disabled
  film_grain=disabled
  film_dust=disabled
  color_correction=disabled
  logo=disabled
  video_filters=disabled

CapCut background_loop.mp4 is treated as the completed video source.
The video stream is looped and copied without FFmpeg video filters or re-encoding.
Its audio is looped, kept at the configured volume, and mixed with concatenated Suno BGM.
EOF_STATUS

log_media_metadata "Selected background loop video" "$BACKGROUND_FILE"

ffmpeg_cmd=(
  ffmpeg -y
  -stream_loop -1 -i "$BACKGROUND_FILE"
  -stream_loop -1 -f concat -safe 0 -i "$CONCAT_FILE"
  -filter_complex "[0:a]atrim=0:${TARGET_SECONDS},asetpts=N/SR/TB,volume=${BACKGROUND_AUDIO_VOLUME}[background_audio];[1:a]atrim=0:${TARGET_SECONDS},asetpts=N/SR/TB,volume=${BGM_VOLUME}[suno_bgm];[background_audio][suno_bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=${AUDIO_LIMIT}[audio_out]"
  -map 0:v:0 -map "[audio_out]"
  -t "$TARGET_SECONDS"
  -c:v copy
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
