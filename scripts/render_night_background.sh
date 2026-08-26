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
  # Decode the supplied rain video once into still frames. Remotion then reads
  # deterministic JPEGs instead of seeking the source video with OffthreadVideo,
  # which avoids the vertical smear seen in selected decoded video frames.
  mkdir -p public/night-frames
  find public/night-frames -type f -name 'frame-*.jpg' -delete
  ffmpeg -y -i "$source_copy" -map 0:v:0 \
    -vf "fps=30,scale=1920:1080:flags=lanczos,setsar=1" \
    -q:v 2 public/night-frames/frame-%04d.jpg
  node scripts/prepare_remotion_background.mjs "$ASSET_DIR"

  animate="$(node -p "JSON.parse(require('fs').readFileSync('src/generated-light-zones.json', 'utf8')).animate")"
  safe_zone_count="$(node -e "const x=require('./src/generated-light-zones.json'); console.log(x.zones.filter(z => z.eligible).slice(0, 3).length)")"
  echo "Night video lighting: animate=${animate} safe_light_count=${safe_zone_count} (rendering continues with zero to three lights)."

  source_frames="$(find public/night-frames -type f -name 'frame-*.jpg' | wc -l)"
  if [[ "$source_frames" -lt 1 ]]; then
    echo "No rain video frames were extracted." >&2
    exit 1
  fi
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
safe_zone_count="$(node -e "const x=require('./src/generated-light-zones.json'); console.log(x.zones.filter(z => z.eligible).slice(0, 3).length)")"
echo "Night image lighting: animate=${animate} safe_light_count=${safe_zone_count} (rendering continues with zero to three lights)."

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
