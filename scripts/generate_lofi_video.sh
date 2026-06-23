#!/usr/bin/env bash
set -euo pipefail

ASSET_DIR="${ASSET_DIR:-video_assets}"
TRACK_DIR="$ASSET_DIR/tracks"
OUTPUT_DIR="${OUTPUT_DIR:-dist}"
OUTPUT_FILE="${OUTPUT_FILE:-Tokyo_Memory_Archive_001.mp4}"
TARGET_SECONDS="${TARGET_SECONDS:-3600}"
ENABLE_WAVEFORM="${ENABLE_WAVEFORM:-1}"
ENABLE_LOGO="${ENABLE_LOGO:-1}"
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

BACKGROUND_FILE="$(find_first_asset background || true)"
if [[ -z "$BACKGROUND_FILE" ]]; then
  echo "Missing required background: $ASSET_DIR/background.png, .jpg, or .jpeg" >&2
  exit 1
fi

echo "Using background: $BACKGROUND_FILE"

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

HAS_WAVEFORM=0
if [[ "$ENABLE_WAVEFORM" == "1" ]]; then
  if ffmpeg -hide_banner -filters 2>/dev/null | grep -q '[[:space:]]showwaves[[:space:]]'; then
    HAS_WAVEFORM=1
    echo "Audio waveform visualizer enabled."
  else
    echo "FFmpeg showwaves filter not available; continuing without waveform."
  fi
else
  echo "Audio waveform visualizer disabled by ENABLE_WAVEFORM=$ENABLE_WAVEFORM"
fi

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
  inputs+=( -loop 1 -i "$BACKGROUND_FILE" )
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

  if [[ "$include_optional_visuals" == "1" && "$HAS_WAVEFORM" -eq 1 ]]; then
    filter_complex+="[audio_mix]asplit=2[aout][wave_audio];[wave_audio]showwaves=s=720x96:mode=line:rate=30:colors=white@0.70,format=rgba[wave];"
  else
    filter_complex+="[audio_mix]anull[aout];"
  fi

  filter_complex+="[${background_index}:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,format=rgba[bg];"
  local current_video="bg"

  if [[ "$include_optional_visuals" == "1" && "$HAS_RAIN_OVERLAY" -eq 1 ]]; then
    filter_complex+="[${rain_overlay_index}:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,format=rgba,colorchannelmixer=aa=0.28[ov];[${current_video}][ov]overlay=0:0:shortest=0[tmp_rain];"
    current_video="tmp_rain"
  fi

  if [[ "$include_optional_visuals" == "1" && "$HAS_LOGO" -eq 1 ]]; then
    filter_complex+="[${logo_index}:v]scale=w='min(360,iw)':h=-1:force_original_aspect_ratio=decrease,fps=30,format=rgba,colorchannelmixer=aa=0.82[logo];[${current_video}][logo]overlay=(W-w)/2:H-h-150:shortest=0[tmp_logo];"
    current_video="tmp_logo"
  fi

  if [[ "$include_optional_visuals" == "1" && "$HAS_WAVEFORM" -eq 1 ]]; then
    filter_complex+="[${current_video}][wave]overlay=(W-w)/2:H-h-64:shortest=0,format=yuv420p[vout]"
  else
    filter_complex+="[${current_video}]format=yuv420p[vout]"
  fi

  ffmpeg -y \
    "${inputs[@]}" \
    -filter_complex "$filter_complex" \
    -map "[vout]" -map "[aout]" -t "$TARGET_SECONDS" \
    -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "$OUTPUT_DIR/$OUTPUT_FILE"
}

if ! run_ffmpeg 1; then
  echo "Optional visual generation failed; retrying without waveform, logo, or rain overlay to prioritize MP4 output." >&2
  run_ffmpeg 0
fi
