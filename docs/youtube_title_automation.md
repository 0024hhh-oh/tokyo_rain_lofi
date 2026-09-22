# YouTube title automation

The production repository is `0024hhh-oh/tokyo_rain_lofi`.

The normal `Generate LOFI video` workflow scans both
`Tokyo ChillMatic FM/Projects/day` and
`Tokyo ChillMatic FM/Projects/night`.

## Format

- Night: `【Playlist】Tokyo Rainy Night Memories | SCENE【LOFI】【CHILL】【BGM】`
- Day: `【Playlist】Tokyo Memory Archive | SCENE【LOFI】【CHILL】【BGM】`

The scene is generated deterministically from the work-folder name and, when
useful, a descriptive background image or video filename. Generic names such as
`Batch25` and `background.png` are ignored. Sequence numbers are intentionally
not generated because the existing channel has duplicate and missing numbers.

Example work folder:

```text
Projects/night/batch_041_Oji_station/
  background_rainy_platform.png
  01.mp3
  ...
```

Generated title:

```text
【Playlist】Tokyo Rainy Night Memories | Oji station — rainy platform【LOFI】【CHILL】【BGM】
```

## Saved result and override

Before rendering, the generated title is written to `youtube_title.txt` in the
same work folder. The same exact string is passed to the private YouTube upload.

To lock a special title, add `youtube_title_override.txt` to that work folder.
Its first non-empty line must be 100 characters or fewer. The workflow copies
the override into `youtube_title.txt` and uploads with it.

This feature uses filenames and folder metadata. It does not inspect image
pixels and does not require an external AI API.
