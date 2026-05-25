# Codex Task: Fix media folder paths and stabilize LOFI generator

This project is a Flask + FFmpeg Tokyo Rain LOFI video generator.

Current goal:
Make the project structure consistent and easy to operate from GitHub/Codex.

## Current folder structure

- static/bg/ : background images
- static/music/ : BGM audio files
- static/overlay/ : rain, grain, VHS overlay assets
- static/output/ : generated videos
- templates/ : HTML templates
- static/app.js : frontend control
- static/style.css : CSS
- app.py : Flask + FFmpeg backend

## Problems to fix

app.py currently uses:

- outputs/
- images/
- audio/

But the intended structure is:

- static/output/
- static/bg/
- static/music/
- static/overlay/

## Required changes

1. Update app.py paths:
   - OUTPUT_DIR = Path("static/output")
   - IMAGES_DIR = Path("static/bg")
   - AUDIO_DIR = Path("static/music")
   - OVERLAY_DIR = Path("static/overlay")

2. Make sure these directories are created automatically if missing.

3. Keep existing endpoints:
   - /
   - /generate
   - /status/<job_id>
   - /stop/<job_id>
   - /download/<path:filename>

4. Make /download serve files from static/output.

5. Do not remove existing rain/VHS/lofi FFmpeg effects.

6. Add safe fallback behavior:
   - If no background image exists, generate a color-gradient video.
   - If no music file exists, generate soft synthetic audio or keep existing fallback audio.

7. Add comments explaining the folder structure.

8. Update README.md with the correct structure and usage.

9. Keep the app simple and smartphone-friendly.

## Desired direction

This is not a flashy short-video generator.
It is for long-form YouTube sleep/concentration LOFI videos.

Style:
- rainy Tokyo night
- nostalgic
- lonely
- muted colors
- VHS texture
- film grain
- subtle rain
- low stimulation
- long replay tolerance