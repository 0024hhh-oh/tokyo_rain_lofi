#!/usr/bin/env bash
set -euo pipefail

ASSET_DIR="${ASSET_DIR:-video_assets}"
TRACK_DIR="$ASSET_DIR/tracks"
OUTPUT_DIR="${OUTPUT_DIR:-dist}"
OUTPUT_FILE="${OUTPUT_FILE:-Tokyo_Memory_Archive_001.mp4}"
TARGET_SECONDS="${TARGET_SECONDS:-3600}"
FFMPEG_PRESET="${FFMPEG_PRESET:-ultrafast}"
FFMPEG_CRF="${FFMPEG_CRF:-30}"
ENABLE_LOGO="${ENABLE_LOGO:-1}"
ENABLE_RAIN_OVERLAY="${ENABLE_RAIN_OVERLAY:-0}"
ENABLE_FILM_GRAIN="${ENABLE_FILM_GRAIN:-0}"
ENABLE_FILM_DUST="${ENABLE_FILM_DUST:-0}"
FAIL_ON_OPTIONAL_VISUAL_FALLBACK="${FAIL_ON_OPTIONAL_VISUAL_FALLBACK:-0}"
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

find_first_asset() {
  local base="$1"
  local candidate
  for ext in png jpg jpeg; do
    candidate="$ASSET_DIR/${base}.${ext}"
    if [[ -f "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

BACKGROUND_FILE=""
BACKGROUND_TYPE="image"
if [[ -f "$ASSET_DIR/background_loop.mp4" ]]; then
  BACKGROUND_FILE="$ASSET_DIR/background_loop.mp4"
  BACKGROUND_TYPE="video"
elif BACKGROUND_FILE="$(find_first_asset background || true)"; [[ -n "$BACKGROUND_FILE" ]]; then
  BACKGROUND_TYPE="image"
else
  echo "background_loop.mp4 または background.png が必要です" >&2
  exit 1
fi

log_selected_background() {
  local background_path="$1"
  local background_realpath
  local actual_sha256
  local manifest_path="$ASSET_DIR/background_manifest.env"
  background_realpath="$(realpath "$background_path")"
  if command -v sha256sum >/dev/null 2>&1; then
    actual_sha256="$(sha256sum "$background_path" | awk '{print $1}')"
  elif command -v shasum >/dev/null 2>&1; then
    actual_sha256="$(shasum -a 256 "$background_path" | awk '{print $1}')"
  else
    actual_sha256="<unavailable: sha256sum/shasum not found>"
  fi

  if [[ -f "$manifest_path" ]]; then
    # shellcheck disable=SC1090
    source "$manifest_path"
  else
    BACKGROUND_SOURCE_NAME="$(basename "$background_path")"
    BACKGROUND_DRIVE_FILE_ID="<unknown: manifest missing>"
    BACKGROUND_SOURCE_PATH="$background_path"
    BACKGROUND_DESTINATION_PATH="$background_path"
    BACKGROUND_SHA256="$actual_sha256"
  fi

  echo "Selected background for FFmpeg:"
  echo "  source_name=$BACKGROUND_SOURCE_NAME"
  echo "  drive_file_id=$BACKGROUND_DRIVE_FILE_ID"
  echo "  source_path=$BACKGROUND_SOURCE_PATH"
  echo "  destination_path=$BACKGROUND_DESTINATION_PATH"
  echo "  actual_path=$background_realpath"
  echo "  manifest_sha256=$BACKGROUND_SHA256"
  echo "  actual_sha256=$actual_sha256"
  if [[ "$BACKGROUND_SHA256" != "$actual_sha256" ]]; then
    echo "Background SHA256 mismatch between download manifest and selected FFmpeg input." >&2
    exit 1
  fi
}

log_selected_background "$BACKGROUND_FILE"

HAS_RAIN_AUDIO=0
if [[ -f "$ASSET_DIR/rain.mp3" ]]; then
  HAS_RAIN_AUDIO=1
else
  echo "Optional rain audio not found; generating video with BGM only: $ASSET_DIR/rain.mp3"
fi

HAS_RAIN_OVERLAY=0
if [[ "$ENABLE_RAIN_OVERLAY" == "1" ]]; then
  if [[ -f "$ASSET_DIR/rain_overlay.mp4" ]]; then
    HAS_RAIN_OVERLAY=1
  else
    echo "Optional rain overlay not found; continuing without overlay: $ASSET_DIR/rain_overlay.mp4"
  fi
else
  echo "Rain overlay disabled by ENABLE_RAIN_OVERLAY=$ENABLE_RAIN_OVERLAY"
fi

LOGO_FILE=""
HAS_LOGO=0
if [[ "$ENABLE_LOGO" == "1" ]]; then
  LOGO_FILE="$(find_first_asset logo || true)"
  if [[ -n "$LOGO_FILE" ]]; then
    HAS_LOGO=1
    echo "Using optional logo: $LOGO_FILE"
  else
    echo "Optional logo not found; continuing without logo: $ASSET_DIR/logo.png, .jpg, or .jpeg"
  fi
else
  echo "Logo overlay disabled by ENABLE_LOGO=$ENABLE_LOGO"
fi

echo "No audio-reactive overlay is added: CapCut background_loop.mp4 already contains rain and film noise."

HAS_FILM_GRAIN=0
if [[ "$ENABLE_FILM_GRAIN" == "1" ]]; then
  if ffmpeg -hide_banner -filters 2>/dev/null | grep -q '[[:space:]]noise[[:space:]]'; then
    HAS_FILM_GRAIN=1
    echo "Visible LOFI/VHS film grain enabled: FFmpeg noise filter will be applied."
  else
    echo "FFmpeg noise filter not available; continuing without film grain."
  fi
else
  echo "Film grain disabled by ENABLE_FILM_GRAIN=$ENABLE_FILM_GRAIN"
fi

HAS_FILM_DUST=0
if [[ "$ENABLE_FILM_DUST" == "1" ]]; then
  echo "Film dust requested but disabled for FFmpeg stability; continuing without dust."
else
  echo "Film dust disabled by ENABLE_FILM_DUST=$ENABLE_FILM_DUST"
fi

if [[ "$FAIL_ON_OPTIONAL_VISUAL_FALLBACK" == "1" ]]; then
  if [[ "$ENABLE_FILM_GRAIN" == "1" && "$HAS_FILM_GRAIN" -ne 1 ]]; then
    echo "FAIL_ON_OPTIONAL_VISUAL_FALLBACK=1; required noise film grain is unavailable." >&2
    exit 1
  fi
fi

log_output_metadata() {
  local output_path="$1"
  if [[ ! -f "$output_path" ]]; then
    echo "Output metadata unavailable; file was not created: $output_path" >&2
    return 1
  fi

  echo "Generated file: $output_path"
  stat -c 'Generated file size: %s bytes' "$output_path"

  if command -v ffprobe >/dev/null 2>&1; then
    ffprobe -v error \
      -select_streams v:0 \
      -show_entries stream=width,height,duration \
      -of default=noprint_wrappers=1 "$output_path"
    ffprobe -v error \
      -show_entries format=duration,size \
      -of default=noprint_wrappers=1 "$output_path"
  else
    echo "ffprobe not found; skipping generated resolution and duration log." >&2
  fi
}

run_ffmpeg() {
  local include_optional_visuals="$1"
  local -a inputs=(
    -stream_loop -1 -f concat -safe 0 -i "$CONCAT_FILE"
  )
  local rain_audio_index=""
  local background_index
  local rain_overlay_index=""
  local logo_index=""
  local input_index=1

  if [[ "$HAS_RAIN_AUDIO" -eq 1 ]]; then
    rain_audio_index="$input_index"
    inputs+=( -stream_loop -1 -i "$ASSET_DIR/rain.mp3" )
    input_index=$((input_index + 1))
  fi

  background_index="$input_index"
  if [[ "$BACKGROUND_TYPE" == "video" ]]; then
    inputs+=( -stream_loop -1 -i "$BACKGROUND_FILE" )
  else
    inputs+=( -loop 1 -i "$BACKGROUND_FILE" )
  fi
  input_index=$((input_index + 1))

  if [[ "$include_optional_visuals" == "1" && "$HAS_RAIN_OVERLAY" -eq 1 ]]; then
    rain_overlay_index="$input_index"
    inputs+=( -stream_loop -1 -i "$ASSET_DIR/rain_overlay.mp4" )
    input_index=$((input_index + 1))
  fi

  if [[ "$include_optional_visuals" == "1" && "$HAS_LOGO" -eq 1 ]]; then
    logo_index="$input_index"
    inputs+=( -loop 1 -i "$LOGO_FILE" )
    input_index=$((input_index + 1))
  fi

  local filter_complex=""
  if [[ "$HAS_RAIN_AUDIO" -eq 1 ]]; then
    filter_complex="[0:a]atrim=0:${TARGET_SECONDS},asetpts=N/SR/TB,volume=0.92[music];[${rain_audio_index}:a]atrim=0:${TARGET_SECONDS},asetpts=N/SR/TB,volume=0.16[rain];[music][rain]amix=inputs=2:duration=first:dropout_transition=3,alimiter=limit=0.95[audio_mix];"
  else
    filter_complex="[0:a]atrim=0:${TARGET_SECONDS},asetpts=N/SR/TB,volume=0.92,alimiter=limit=0.95[audio_mix];"
  fi

  filter_complex+="[audio_mix]anull[aout];"

  if [[ "$BACKGROUND_TYPE" == "video" ]]; then
    # CapCut-rendered loops already contain the intended rain/film-noise look; keep frames visually unchanged.
    filter_complex+="[${background_index}:v]fps=30,format=rgba[bg];"
  else
    filter_complex+="[${background_index}:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,format=rgba[bg];"
  fi
  local current_video="bg"

  if [[ "$include_optional_visuals" == "1" && "$HAS_RAIN_OVERLAY" -eq 1 ]]; then
    filter_complex+="[${rain_overlay_index}:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,format=rgba,colorchannelmixer=aa=0.28[ov];[${current_video}][ov]overlay=0:0:shortest=0[tmp_rain];"
    current_video="tmp_rain"
  fi

  if [[ "$include_optional_visuals" == "1" && "$HAS_LOGO" -eq 1 ]]; then
    filter_complex+="[${logo_index}:v]scale=w='min(360,iw)':h=-1:force_original_aspect_ratio=decrease,fps=30,format=rgba,colorchannelmixer=aa=0.82[logo];[${current_video}][logo]overlay=(W-w)/2:H-h-150:shortest=0[tmp_logo];"
    current_video="tmp_logo"
  fi

  if [[ "$include_optional_visuals" == "1" && "$HAS_FILM_GRAIN" -eq 1 ]]; then
    filter_complex+="[${current_video}]format=yuv420p,noise=alls=24:allf=t+u[vout]"
  else
    filter_complex+="[${current_video}]format=yuv420p[vout]"
  fi

  echo "Optional visual filter status:"
  echo "  audio-reactive overlay: REMOVED"
  if [[ "$include_optional_visuals" == "1" && "$HAS_RAIN_OVERLAY" -eq 1 ]]; then
    echo "  rain overlay: APPLIED"
  else
    echo "  rain overlay: NOT APPLIED"
  fi
  echo "  dust: NOT APPLIED"
  if [[ "$include_optional_visuals" == "1" && "$HAS_FILM_GRAIN" -eq 1 ]]; then
    echo "  noise: APPLIED (alls=24:allf=t+u)"
  else
    echo "  noise: NOT APPLIED"
  fi

  local -a ffmpeg_cmd=(
    ffmpeg -y
    "${inputs[@]}"
    -filter_complex "$filter_complex"
    -map "[vout]" -map "[aout]" -t "$TARGET_SECONDS"
    -c:v libx264 -preset "$FFMPEG_PRESET" -crf "$FFMPEG_CRF" -pix_fmt yuv420p
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart
    "$OUTPUT_DIR/$OUTPUT_FILE"
  )

  echo "FFmpeg command:"
  printf ' %q' "${ffmpeg_cmd[@]}"
  echo

  "${ffmpeg_cmd[@]}"
}

if ! run_ffmpeg 1; then
  echo "Optional visual generation failed; retrying without logo, rain overlay, film grain, or dust to prioritize MP4 output. Check the FFmpeg command above for the failing filter graph." >&2
  if [[ "$FAIL_ON_OPTIONAL_VISUAL_FALLBACK" == "1" ]]; then
    echo "FAIL_ON_OPTIONAL_VISUAL_FALLBACK=1; failing instead of generating a fallback video without optional visuals." >&2
    exit 1
  fi
  run_ffmpeg 0
fi

log_output_metadata "$OUTPUT_DIR/$OUTPUT_FILE"
