# YouTube description automation

The production repository is `0024hhh-oh/tokyo_rain_lofi`.

The normal `Generate LOFI video` workflow generates one description for each
valid work folder under `Projects/day` and `Projects/night`.

## Structure

Every generated description contains:

1. The Tokyo ChillMatic FM introduction
2. One day/night-specific scene sentence
3. The listening-use list
4. The channel's memory-archive statement
5. The fixed channel sign-off
6. Six existing hashtags

The scene sentence uses the same work-folder and background filename metadata as
the title generator.

Night example:

```text
Tonight's broadcast drifts through Oji station — rainy platform on a rainy Tokyo night.
```

Day example:

```text
Today's broadcast drifts through Kameido backstreet, a fading memory from somewhere in Tokyo.
```

## Saved result and override

Before rendering, the generated text is written to
`youtube_description.txt` in the same work folder. That exact text is encoded
for the GitHub Actions handoff and passed to the existing private YouTube upload.

To lock a special description, add `youtube_description_override.txt` to the
work folder. Its full non-empty content is used, up to YouTube's 5,000-character
limit, and is copied into `youtube_description.txt`.

No track timestamps are generated because the current project metadata does not
contain a verified final chapter map. The feature uses filenames and folder
metadata; it does not inspect image pixels and does not require an external AI
API.
