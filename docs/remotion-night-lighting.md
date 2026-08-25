# Remotion night-lighting stage

Static night backgrounds now pass through a Remotion stage before the existing
FFmpeg video generator. The phone workflow stays the same:

1. Put one `background.png`, `background.jpg`, or `background.jpeg` and the MP3
   tracks in a Google Drive project folder.
2. `Generate LOFI video` detects the project on its existing 30-minute schedule.
3. If the folder contains `light_overlay.png`, Remotion uses that supplied
   transparent light-only layer. No wall, road, river, reflection, or other
   image region is detected automatically.
4. Remotion creates a deterministic 30-second, 1920x1080 H.264 loop at
   `video_assets/background.mp4`.
5. The existing FFmpeg audio, rain, duration, and YouTube upload stages continue
   unchanged.

If `light_overlay.png` is absent, the background is rendered without lighting
processing. The source is never darkened, and black, gray, dimming, or
extinguishing overlays are not generated.

The overlay opacity follows a deterministic irregular 0 → peak → 0 schedule.
The overlay itself remains spatially fixed, so buildings, roads, water, rain,
and reflections cannot move or flicker independently.

Useful Actions log line:

```text
Remotion lighting: overlay=light_overlay.png animate=true (no image light detection)
```

Local checks:

```bash
npm ci
npm test
npm run typecheck
node scripts/create_remotion_fixture.mjs
ASSET_DIR=video_assets bash scripts/render_night_background.sh
```
