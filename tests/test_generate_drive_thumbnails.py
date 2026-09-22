import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from generate_drive_thumbnails import build_ffmpeg_command, select_thumbnail_source


class ThumbnailSelectionTests(unittest.TestCase):
    def test_uses_original_image_name_without_renaming(self):
        items = [
            {"id": "video", "name": "scene.MOV", "mimeType": "video/quicktime", "size": "50"},
            {"id": "image", "name": "IMG_4649.jpeg", "mimeType": "image/jpeg", "size": "100"},
        ]
        self.assertEqual(select_thumbnail_source(items)["id"], "image")

    def test_largest_safe_image_wins_and_helpers_are_ignored(self):
        items = [
            {"id": "small", "name": "street.jpg", "mimeType": "image/jpeg", "size": "100"},
            {"id": "large", "name": "station.png", "mimeType": "image/png", "size": "200"},
            {"id": "logo", "name": "custom-logo.png", "mimeType": "image/png", "size": "999"},
            {"id": "overlay", "name": "light_overlay.png", "mimeType": "image/png", "size": "999"},
            {"id": "old", "name": "thumbnail.jpg", "mimeType": "image/jpeg", "size": "999"},
        ]
        self.assertEqual(select_thumbnail_source(items)["id"], "large")

    def test_explicit_thumbnail_source_is_optional_but_has_priority(self):
        items = [
            {"id": "explicit", "name": "thumbnail_source.jpg", "mimeType": "image/jpeg", "size": "1"},
            {"id": "large", "name": "large.png", "mimeType": "image/png", "size": "999"},
        ]
        self.assertEqual(select_thumbnail_source(items)["id"], "explicit")

    def test_video_is_fallback_when_no_safe_image_exists(self):
        items = [
            {"id": "other", "name": "z.MOV", "mimeType": "video/quicktime"},
            {"id": "background", "name": "background.mp4", "mimeType": "video/mp4"},
        ]
        self.assertEqual(select_thumbnail_source(items)["id"], "background")

    def test_video_command_seeks_one_second_and_image_does_not(self):
        video = build_ffmpeg_command(
            ffmpeg="ffmpeg",
            source=Path("scene.mov"),
            logo=Path("logo.jpg"),
            output=Path("thumbnail.jpg"),
        )
        image = build_ffmpeg_command(
            ffmpeg="ffmpeg",
            source=Path("scene.jpg"),
            logo=Path("logo.jpg"),
            output=Path("thumbnail.jpg"),
        )
        self.assertIn("-ss", video)
        self.assertNotIn("-ss", image)
        filters = video[video.index("-filter_complex") + 1]
        self.assertIn("colorkey=0x080808:0.24:0.10", filters)
        self.assertIn("overlay=77:(H-h)/2", filters)


if __name__ == "__main__":
    unittest.main()
