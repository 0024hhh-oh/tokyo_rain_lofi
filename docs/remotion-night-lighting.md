# Remotion night-lighting stage

Static night backgrounds now pass through a Remotion stage before the existing
FFmpeg video generator. The phone workflow stays the same:

1. Put one `background.png`, `background.jpg`, or `background.jpeg` and the MP3
   tracks in a Google Drive project folder.
2. `Generate LOFI video` detects the project on its existing 30-minute schedule.
3. The lighting analyzer finds bright, warm regions in the night image.
4. Remotion creates a deterministic 30-second, 1920x1080 H.264 loop at
   `video_assets/background.mp4`.
5. The existing FFmpeg audio, rain, duration, and YouTube upload stages continue
   unchanged.

Existing `background.mp4` / `background_loop.mp4` projects are not modified.
Bright daytime images and images with no safe lighting regions skip the Remotion
stage and retain the original static background.

The animation deliberately avoids hard on/off flashes. Each detected light uses
slow periodic drift plus one to three soft dimming events per 30-second loop.
All pseudo-random values use fixed Remotion seeds, so parallel renders are stable
and the loop is reproducible.

Useful Actions log line:

```text
Remotion lighting analysis: animate=true average_luma=... threshold=... zones=...
```

Local checks:

```bash
npm ci
npm test
npm run typecheck
node scripts/create_remotion_fixture.mjs
ASSET_DIR=video_assets bash scripts/render_night_background.sh
```
