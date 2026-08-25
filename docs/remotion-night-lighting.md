# Remotion night-lighting stage

Static night backgrounds now pass through a Remotion stage before the existing
FFmpeg video generator. The phone workflow stays the same:

1. Put one `background.png`, `background.jpg`, or `background.jpeg` and the MP3
   tracks in a Google Drive project folder.
2. `Generate LOFI video` detects the project on its existing 30-minute schedule.
3. The lighting analyzer finds bright, warm regions in the supplied image.
   Bright daytime/dusk sources keep their original exposure and automatically
   use a softer feathered light profile; darker sources use the night profile.
4. Remotion creates a deterministic 30-second, 1920x1080 H.264 loop at
   `video_assets/background.mp4`.
5. The existing FFmpeg audio, rain, duration, and YouTube upload stages continue
   unchanged.

Bright daytime sources are not converted into night scenes. The day/night
lighting profile is selected automatically from average image luma, so the
Google Drive folder workflow does not change. Images with no safe lighting
regions still render without local light animation.

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
