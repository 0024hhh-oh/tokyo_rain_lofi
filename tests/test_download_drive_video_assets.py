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


def test_log_drive_download_includes_drive_source_and_video_assets_destination(capsys):
    download_drive_video_assets.log_drive_download(
        {"id": "drive-file-id", "name": "Suno Original Name.mp3"},
        Path("video_assets/tracks/track01.mp3"),
    )

    assert capsys.readouterr().out == (
        "Downloaded from Google Drive: Suno Original Name.mp3 "
        "(id: drive-file-id) -> video_assets/tracks/track01.mp3\n"
    )


def test_incoming_download_logs_renamed_assets(tmp_path, capsys):
    children = [
        {"id": "bg-id", "name": "background.JPG", "mimeType": "image/jpeg"},
        {"id": "mp3-id", "name": "lofi take.mp3", "mimeType": "audio/mpeg"},
    ]

    def write_download(service, file_id, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"x")

    with (
        patch.object(download_drive_video_assets, "list_files", return_value=children),
        patch.object(
            download_drive_video_assets, "download_file", side_effect=write_download
        ),
    ):
        download_drive_video_assets.download_incoming_work_folder(
            None, "folder-id", tmp_path / "video_assets"
        )

    output = capsys.readouterr().out
    assert (
        f"Downloaded from Google Drive: background.JPG (id: bg-id) -> {(tmp_path / 'video_assets/background.jpg').as_posix()}"
        in output
    )
    assert (
        f"Downloaded from Google Drive: lofi take.mp3 (id: mp3-id) -> {(tmp_path / 'video_assets/tracks/track01.mp3').as_posix()}"
        in output
    )
