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
safe_zone_count="$(node -e "const x=require('./src/generated-light-zones.json'); console.log(x.zones.filter(z => z.warmth >= 0.55 && z.y < 0.72).slice(0, 3).length)")"
if [[ "$animate" != "true" || "$safe_zone_count" != "3" ]]; then
  echo "Night lighting skipped: no exact three-light match; rain animation will still be rendered."
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
