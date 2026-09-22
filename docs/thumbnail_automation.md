# YouTube thumbnail automation

The production repository is `0024hhh-oh/tokyo_rain_lofi`.

Run **Generate YouTube thumbnails** from GitHub Actions. It scans both
`Tokyo ChillMatic FM/Projects/day` and `Tokyo ChillMatic FM/Projects/night`
by default and writes `thumbnail.jpg` into each work folder.

Source priority:

1. `thumbnail_source.*` when present (renaming is optional)
2. The largest image in the work folder, excluding thumbnail/logo/overlay/mask files
3. A video frame at 1 second when no usable image exists

Night uses the fixed pink logo; day uses the fixed light-blue logo. The logo's dark
rectangle is removed during composition. The result is 1280x720.

This workflow never runs the LOFI video generator. `thumbnail.jpg` is also not a
recognized background name in the production video pipeline, so it cannot become
the video background by mistake.
