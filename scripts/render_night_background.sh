#!/usr/bin/env bash
set -euo pipefail

ASSET_DIR="${ASSET_DIR:-video_assets}"

if [[ ! -s "$ASSET_DIR/background.png" && ! -s "$ASSET_DIR/background.jpg" && ! -s "$ASSET_DIR/background.jpeg" ]]; then
  echo "Remotion lighting skipped: the project uses a background video or has no static image."
  exit 0
fi

if [[ ! -d node_modules ]]; then
  npm ci --no-audit --no-fund
fi

node scripts/prepare_remotion_background.mjs "$ASSET_DIR"
animate="$(node -p "JSON.parse(require('fs').readFileSync('src/generated-light-zones.json', 'utf8')).animate")"
if [[ "$animate" != "true" ]]; then
  echo "Remotion lighting skipped: the supplied image was not classified as a night image or had no safe light zones."
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
