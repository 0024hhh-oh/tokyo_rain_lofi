import hashlib
import sys
import types
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

google = types.ModuleType("google")
google.oauth2 = types.ModuleType("google.oauth2")
google.oauth2.service_account = types.ModuleType("google.oauth2.service_account")
googleapiclient = types.ModuleType("googleapiclient")
googleapiclient.discovery = types.ModuleType("googleapiclient.discovery")
googleapiclient.discovery.build = lambda *args, **kwargs: None
googleapiclient.http = types.ModuleType("googleapiclient.http")
googleapiclient.http.MediaIoBaseDownload = object
sys.modules.setdefault("google", google)
sys.modules.setdefault("google.oauth2", google.oauth2)
sys.modules.setdefault("google.oauth2.service_account", google.oauth2.service_account)
sys.modules.setdefault("googleapiclient", googleapiclient)
sys.modules.setdefault("googleapiclient.discovery", googleapiclient.discovery)
sys.modules.setdefault("googleapiclient.http", googleapiclient.http)

import download_drive_video_assets


def test_log_drive_download_includes_drive_source_destination_and_hash(
    tmp_path, capsys
):
    destination = tmp_path / "video_assets/tracks/track01.mp3"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"track-bytes")
    expected_hash = hashlib.sha256(b"track-bytes").hexdigest()

    download_drive_video_assets.log_drive_download(
        {"id": "drive-file-id", "name": "Suno Original Name.mp3"},
        destination,
        "Tokyo ChillMatic FM/Videos/video_001/tracks/Suno Original Name.mp3",
    )

    assert capsys.readouterr().out == (
        "Downloaded from Google Drive: "
        "source_name=Suno Original Name.mp3 file_id=drive-file-id "
        "source_path=Tokyo ChillMatic FM/Videos/video_001/tracks/Suno Original Name.mp3 "
        f"destination={destination.as_posix()} sha256={expected_hash}\n"
    )


def test_incoming_download_logs_and_manifests_selected_background(tmp_path, capsys):
    children = [
        {"id": "bg-id", "name": "background.JPG", "mimeType": "image/jpeg"},
        {"id": "mp3-id", "name": "lofi take.mp3", "mimeType": "audio/mpeg"},
    ]

    def write_download(service, file_id, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(file_id.encode())

    with (
        patch.object(download_drive_video_assets, "list_files", return_value=children),
        patch.object(
            download_drive_video_assets, "download_file", side_effect=write_download
        ),
    ):
        download_drive_video_assets.download_incoming_work_folder(
            None, "folder-id", tmp_path / "video_assets"
        )

    bg_path = tmp_path / "video_assets/background.jpg"
    bg_hash = hashlib.sha256(b"bg-id").hexdigest()
    output = capsys.readouterr().out
    assert (
        "Selected incoming background image: source_name=background.JPG file_id=bg-id "
        f"destination={bg_path.as_posix()}"
        in output
    )
    assert (
        "Downloaded from Google Drive: source_name=background.JPG file_id=bg-id "
        f"source_path=folder:folder-id/background.JPG destination={bg_path.as_posix()} sha256={bg_hash}"
        in output
    )
    assert (
        "Downloaded from Google Drive: source_name=lofi take.mp3 file_id=mp3-id"
        in output
    )
    manifest = (tmp_path / "video_assets/background_manifest.env").read_text()
    assert "BACKGROUND_SOURCE_NAME='background.JPG'" in manifest
    assert "BACKGROUND_DRIVE_FILE_ID='bg-id'" in manifest
    assert "BACKGROUND_SOURCE_PATH='folder:folder-id/background.JPG'" in manifest
    assert f"BACKGROUND_DESTINATION_PATH='{bg_path.as_posix()}'" in manifest
    assert f"BACKGROUND_SHA256='{bg_hash}'" in manifest


def test_incoming_download_removes_stale_background_before_selecting_latest(tmp_path):
    output_dir = tmp_path / "video_assets"
    output_dir.mkdir()
    stale = output_dir / "background.png"
    stale.write_bytes(b"old-background")
    (output_dir / "background_manifest.env").write_text("old")
    children = [
        {"id": "new-bg-id", "name": "background.jpg", "mimeType": "image/jpeg"},
        {"id": "mp3-id", "name": "lofi.mp3", "mimeType": "audio/mpeg"},
    ]

    def write_download(service, file_id, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(file_id.encode())

    with (
        patch.object(download_drive_video_assets, "list_files", return_value=children),
        patch.object(
            download_drive_video_assets, "download_file", side_effect=write_download
        ),
    ):
        download_drive_video_assets.download_incoming_work_folder(
            None, "folder-id", output_dir
        )

    assert not stale.exists()
    assert (output_dir / "background.jpg").read_bytes() == b"new-bg-id"
    assert "new-bg-id" in (output_dir / "background_manifest.env").read_text()


def test_incoming_background_image_detection_accepts_required_names():
    accepted_names = [
        "background.png",
        "background.jpg",
        "background.jpeg",
        "background.PNG",
        "background.JPG",
        "background.JPEG",
    ]

    for name in accepted_names:
        assert download_drive_video_assets.is_background_image_file(
            {"id": name, "name": name, "mimeType": "application/octet-stream"}
        )

    assert not download_drive_video_assets.is_background_image_file(
        {"id": "gif", "name": "background.gif", "mimeType": "image/gif"}
    )
    assert not download_drive_video_assets.is_background_image_file(
        {"id": "other", "name": "background-final.jpg", "mimeType": "image/jpeg"}
    )


def test_incoming_background_jpeg_is_normalized_to_background_jpg(tmp_path):
    children = [
        {"id": "jpeg-bg-id", "name": "background.JPEG", "mimeType": "image/jpeg"},
        {"id": "mp3-id", "name": "lofi.mp3", "mimeType": "audio/mpeg"},
    ]

    def write_download(service, file_id, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(file_id.encode())

    with (
        patch.object(download_drive_video_assets, "list_files", return_value=children),
        patch.object(
            download_drive_video_assets, "download_file", side_effect=write_download
        ),
    ):
        download_drive_video_assets.download_incoming_work_folder(
            None, "folder-id", tmp_path / "video_assets"
        )

    assert (tmp_path / "video_assets/background.jpg").read_bytes() == b"jpeg-bg-id"
    assert not (tmp_path / "video_assets/background.jpeg").exists()


def test_incoming_missing_background_error_mentions_background_image(tmp_path, capsys):
    children = [
        {"id": "mp3-id", "name": "lofi.mp3", "mimeType": "audio/mpeg"},
    ]

    with patch.object(download_drive_video_assets, "list_files", return_value=children):
        try:
            download_drive_video_assets.download_incoming_work_folder(
                None, "folder-id", tmp_path / "video_assets"
            )
        except FileNotFoundError as exc:
            assert str(exc) == "background_loop.mp4 または background画像が必要です"
        else:
            raise AssertionError("FileNotFoundError was not raised")

    output = capsys.readouterr().out
    assert "Starting download_incoming_work_folder: work_folder_id=folder-id" in output
    assert "Incoming work folder items: count=1" in output
    assert "Incoming work folder items[1]: name=lofi.mp3 id=mp3-id mimeType=audio/mpeg" in output
    assert "background_loop.mp4 candidates: count=0" in output
    assert "background_loop.mp4 candidates: <none>" in output
    assert "background image candidates: count=0" in output
    assert "background image candidates: <none>" in output
    assert "track audio candidates: count=1" in output
    assert "track audio candidates[1]: name=lofi.mp3 id=mp3-id mimeType=audio/mpeg" in output
    assert "No usable background asset detected before FileNotFoundError" in output
    assert "because no item name matched 'background_loop.mp4'" in output
    assert "because no item matched names=" in output
