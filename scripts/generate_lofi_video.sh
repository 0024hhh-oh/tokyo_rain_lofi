#!/usr/bin/env bash
set -euo pipefail

ASSET_DIR="${ASSET_DIR:-video_assets}"
TRACK_DIR="$ASSET_DIR/tracks"
OUTPUT_DIR="${OUTPUT_DIR:-dist}"
OUTPUT_FILE="${OUTPUT_FILE:-Tokyo_Memory_Archive_001.mp4}"
TARGET_SECONDS="${TARGET_SECONDS:-3600}"
ENABLE_WAVEFORM="${ENABLE_WAVEFORM:-1}"
ENABLE_LOGO="${ENABLE_LOGO:-1}"
ENABLE_FILM_GRAIN="${ENABLE_FILM_GRAIN:-1}"
ENABLE_FILM_DUST="${ENABLE_FILM_DUST:-1}"
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
    echo "Audio waveform visualizer enabled: showwaves, 1680x300, centered near the bottom, white/gray, boosted for visible motion."
  else
    echo "FFmpeg showwaves filter not available; continuing without waveform."
  fi
else
  echo "Audio waveform visualizer disabled by ENABLE_WAVEFORM=$ENABLE_WAVEFORM"
fi

HAS_FILM_GRAIN=0
if [[ "$ENABLE_FILM_GRAIN" == "1" ]]; then
  if ffmpeg -hide_banner -filters 2>/dev/null | grep -q '[[:space:]]noise[[:space:]]'; then
    HAS_FILM_GRAIN=1
    echo "Visible moving film grain enabled: FFmpeg noise filter will be applied."
  else
    echo "FFmpeg noise filter not available; continuing without film grain."
  fi
else
  echo "Film grain disabled by ENABLE_FILM_GRAIN=$ENABLE_FILM_GRAIN"
fi

HAS_FILM_DUST=0
if [[ "$ENABLE_FILM_DUST" == "1" ]]; then
  echo "Procedural film dust disabled for FFmpeg stability; skipping drawbox dust filters."
else
  echo "Film dust disabled by ENABLE_FILM_DUST=$ENABLE_FILM_DUST"
fi

if [[ "$FAIL_ON_OPTIONAL_VISUAL_FALLBACK" == "1" ]]; then
  if [[ "$ENABLE_WAVEFORM" == "1" && "$HAS_WAVEFORM" -ne 1 ]]; then
    echo "FAIL_ON_OPTIONAL_VISUAL_FALLBACK=1; required showwaves waveform is unavailable." >&2
    exit 1
  fi
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
    filter_complex+="[audio_mix]asplit=2[aout][wave_audio];[wave_audio]volume=3.2,alimiter=limit=0.98,showwaves=s=1680x300:mode=p2p:rate=30:colors=0xf2f2f2@0.96:scale=sqrt,format=rgba,split=2[wave_core][wave_glow_src];[wave_glow_src]gblur=sigma=6,colorchannelmixer=aa=0.42[wave_glow];[wave_core]gblur=sigma=0.6[wave_line];[wave_glow][wave_line]overlay=0:0:shortest=1[wave];"
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
    filter_complex+="[${current_video}][wave]overlay=(W-w)/2:H-h-48:shortest=0[tmp_wave];"
    current_video="tmp_wave"
  fi

  if [[ "$include_optional_visuals" == "1" && "$HAS_FILM_GRAIN" -eq 1 ]]; then
    filter_complex+="[${current_video}]format=yuv420p,noise=alls=18:allf=t+u[vout]"
  else
    filter_complex+="[${current_video}]format=yuv420p[vout]"
  fi

  echo "Optional visual filter status:"
  if [[ "$include_optional_visuals" == "1" && "$HAS_WAVEFORM" -eq 1 ]]; then
    echo "  showwaves: APPLIED (1680x300, p2p, 30fps, boosted audio, thick glow line)"
    echo "  waveform overlay: APPLIED ((W-w)/2:H-h-48)"
  else
    echo "  showwaves: NOT APPLIED"
    echo "  waveform overlay: NOT APPLIED"
  fi
  if [[ "$include_optional_visuals" == "1" && "$HAS_RAIN_OVERLAY" -eq 1 ]]; then
    echo "  rain overlay: APPLIED"
  else
    echo "  rain overlay: NOT APPLIED"
  fi
  if [[ "$include_optional_visuals" == "1" && "$HAS_FILM_DUST" -eq 1 ]]; then
    echo "  dust: APPLIED (animated drawbox specks and scratches)"
  else
    echo "  dust: NOT APPLIED"
  fi
  if [[ "$include_optional_visuals" == "1" && "$HAS_FILM_GRAIN" -eq 1 ]]; then
    echo "  noise: APPLIED (alls=18:allf=t+u)"
  else
    echo "  noise: NOT APPLIED"
  fi

  echo "Complete filter_complex:"
  printf '%s\n' "$filter_complex"

  local -a ffmpeg_cmd=(
    ffmpeg -y
    "${inputs[@]}"
    -filter_complex "$filter_complex"
    -map "[vout]" -map "[aout]" -t "$TARGET_SECONDS"
    -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p
    -c:a aac -b:a 192k -ar 48000 -movflags +faststart
    "$OUTPUT_DIR/$OUTPUT_FILE"
  )

  echo "FFmpeg command:"
  printf ' %q' "${ffmpeg_cmd[@]}"
  echo

  "${ffmpeg_cmd[@]}"
}

if ! run_ffmpeg 1; then
  echo "Optional visual generation failed; retrying without waveform, logo, rain overlay, film grain, or dust to prioritize MP4 output." >&2
  if [[ "$FAIL_ON_OPTIONAL_VISUAL_FALLBACK" == "1" ]]; then
    echo "FAIL_ON_OPTIONAL_VISUAL_FALLBACK=1; failing instead of generating a fallback video without optional visuals." >&2
    exit 1
  fi
  run_ffmpeg 0
fi

log_output_metadata "$OUTPUT_DIR/$OUTPUT_FILE"
