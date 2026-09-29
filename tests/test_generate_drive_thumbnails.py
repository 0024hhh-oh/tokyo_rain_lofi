import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from generate_drive_thumbnails import (
    build_ffmpeg_command,
    build_parser,
    process_project,
    select_thumbnail_source,
)


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
        self.assertIn("overlay=77:(H-h)/2+20", filters)

    def test_targeted_project_can_also_write_a_local_thumbnail(self):
        args = build_parser().parse_args(
            [
                "--mode",
                "day",
                "--project-folder-id",
                "drive-folder-id",
                "--output-file",
                "dist/thumbnail.jpg",
                "--force",
            ]
        )

        self.assertEqual(args.mode, "day")
        self.assertEqual(args.project_folder_id, "drive-folder-id")
        self.assertEqual(args.output_file, Path("dist/thumbnail.jpg"))
        self.assertTrue(args.force)

    def test_local_only_generates_file_without_drive_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "thumbnail.jpg"
            logo = Path(directory) / "logo.jpg"
            logo.write_bytes(b"logo")
            args = build_parser().parse_args(
                ["--mode", "night", "--local-only", "--output-file", str(output),
                 "--night-logo", str(logo)]
            )

            def fake_render(command, **kwargs):
                Path(command[-1]).write_bytes(b"rendered thumbnail")
                return type("Result", (), {"returncode": 0, "stderr": ""})()

            with patch("generate_drive_thumbnails.list_children", return_value=[
                {"id": "source", "name": "background.jpg", "mimeType": "image/jpeg"},
                {"id": "old", "name": "thumbnail.jpg", "mimeType": "image/jpeg"},
            ]), patch("generate_drive_thumbnails.download_file", side_effect=lambda service, file_id, destination: destination.write_bytes(b"source")), patch(
                "generate_drive_thumbnails.subprocess.run", side_effect=fake_render
            ), patch("generate_drive_thumbnails.upload_thumbnail") as upload:
                result = process_project(None, mode="night", project={"id": "folder", "name": "scene"}, args=args)

            self.assertEqual(result, "generated")
            self.assertEqual(output.read_bytes(), b"rendered thumbnail")
            upload.assert_not_called()


if __name__ == "__main__":
    unittest.main()
