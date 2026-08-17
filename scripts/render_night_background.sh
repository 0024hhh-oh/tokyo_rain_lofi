#!/usr/bin/env bash
set -euo pipefail

ASSET_DIR="${ASSET_DIR:-video_assets}"

video_source=""
for candidate in \
  "$ASSET_DIR/background.mp4" \
  "$ASSET_DIR/background_loop.mp4" \
  "$ASSET_DIR/background.mov" \
  "$ASSET_DIR/background_loop.mov"
do
  if [[ -s "$candidate" ]]; then
    video_source="$candidate"
    break
  fi
done

if [[ -n "$video_source" ]]; then
  if [[ ! -d node_modules ]]; then
    npm ci --no-audit --no-fund
  fi

  mkdir -p public
  source_copy="$ASSET_DIR/night_source_input.${video_source##*.}"
  mv "$video_source" "$source_copy"
  ffmpeg -y -i "$source_copy" -frames:v 1 -update 1 "$ASSET_DIR/background.png"
  ffmpeg -y -i "$source_copy" -map 0:v:0 -an -c:v copy public/night-source.mp4
  node scripts/prepare_remotion_background.mjs "$ASSET_DIR"

  animate="$(node -p "JSON.parse(require('fs').readFileSync('src/generated-light-zones.json', 'utf8')).animate")"
  safe_zone_count="$(node -e "const x=require('./src/generated-light-zones.json'); console.log(x.zones.filter(z => z.hasLightCore && z.warmth >= 0.4 && z.y < 0.72).slice(0, 3).length)")"
  if [[ "$animate" != "true" || "$safe_zone_count" != "3" ]]; then
    echo "Night video lighting requires exactly three safe warm light candidates." >&2
    exit 1
  fi

  source_duration="$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 public/night-source.mp4)"
  source_frames="$(python - "$source_duration" <<'PY_VIDEO_FRAMES'
import sys

duration = float(sys.argv[1])
frames = round(duration * 30)
if duration <= 0 or frames < 1:
    raise SystemExit(f"Invalid night source duration: {duration}")
print(frames)
PY_VIDEO_FRAMES
)"
  printf '{\n  "sourceDurationInFrames": %s\n}\n' "$source_frames" > src/generated-video-metadata.json

  rm -f "$ASSET_DIR/background.mp4"
  npx remotion render \
    src/index.ts \
    NightVideoLightingLoop \
    "$ASSET_DIR/background.mp4" \
    --codec=h264 \
    --crf=14 \
    --concurrency=2 \
    --muted \
    --frames=0-899 \
    --log=verbose

  audio_streams="$(ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$ASSET_DIR/background.mp4" | wc -l)"
  if [[ "$audio_streams" != "0" ]]; then
    echo "Rendered night background must not contain audio; got $audio_streams stream(s)." >&2
    exit 1
  fi
  ffprobe -v error \
    -show_entries stream=codec_name,width,height,r_frame_rate \
    -show_entries format=duration,size \
    -of default=noprint_wrappers=1 \
    "$ASSET_DIR/background.mp4"
  exit 0
fi

if [[ ! -s "$ASSET_DIR/background.png" && ! -s "$ASSET_DIR/background.jpg" && ! -s "$ASSET_DIR/background.jpeg" ]]; then
  echo "Remotion lighting skipped: no supported night background was found." >&2
  exit 1
fi

if [[ ! -d node_modules ]]; then
  npm ci --no-audit --no-fund
fi

node scripts/prepare_remotion_background.mjs "$ASSET_DIR"
animate="$(node -p "JSON.parse(require('fs').readFileSync('src/generated-light-zones.json', 'utf8')).animate")"
safe_zone_count="$(node -e "const x=require('./src/generated-light-zones.json'); console.log(x.zones.filter(z => z.hasLightCore && z.warmth >= 0.55 && z.y < 0.72).slice(0, 3).length)")"
if [[ "$animate" != "true" || "$safe_zone_count" != "3" ]]; then
  echo "Remotion lighting skipped: the supplied image did not contain exactly three safe warm light candidates."
  exit 0
fi

rm -f "$ASSET_DIR/background.mp4"
render_args=(
  npx remotion render
  src/index.ts
  NightLightingLoop
  "$ASSET_DIR/background.mp4"
  --codec=h264
  --crf=23
  --concurrency=2
  --log=verbose
)
if [[ -n "${REMOTION_FRAMES:-}" ]]; then
  render_args+=(--frames "$REMOTION_FRAMES")
fi
"${render_args[@]}"

ffprobe -v error \
  -show_entries stream=codec_name,width,height,r_frame_rate \
  -show_entries format=duration,size \
  -of default=noprint_wrappers=1 \
  "$ASSET_DIR/background.mp4"
