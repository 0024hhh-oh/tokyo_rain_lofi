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
googleapiclient.http.MediaFileUpload = (
    lambda filename, mimetype=None, resumable=False: {
        "filename": filename,
        "mimetype": mimetype,
        "resumable": resumable,
    }
)
sys.modules.setdefault("google", google)
sys.modules.setdefault("google.oauth2", google.oauth2)
sys.modules.setdefault("google.oauth2.service_account", google.oauth2.service_account)
sys.modules.setdefault("googleapiclient", googleapiclient)
sys.modules.setdefault("googleapiclient.discovery", googleapiclient.discovery)
sys.modules.setdefault("googleapiclient.http", googleapiclient.http)

import night_test_drive as drive_night_test


def ready_items():
    return [
        {"id": "background", "name": "background.png", "mimeType": "image/png"},
        {"id": "track", "name": "one-song.mp3", "mimeType": "audio/mpeg"},
        {"id": "project", "name": "project.json", "mimeType": "application/json"},
    ]


def args():
    return types.SimpleNamespace(
        root_folder_id="root-id",
        projects_folder="Projects",
        night_test_folder="night-test",
        folder_id="",
        output_dir="video_assets",
    )


def test_inspect_accepts_exact_night_test_inputs(capsys):
    ok, reason, output = drive_night_test.inspect_night_test(ready_items())

    assert ok is True
    assert reason == "night-test input is ready"
    assert output is None
    assert "background=1 mp3=1 project_json=1" in capsys.readouterr().out


def test_inspect_rejects_twenty_track_production_input():
    items = ready_items()[:1] + [
        {"id": f"track-{index}", "name": f"track{index:02}.mp3", "mimeType": "audio/mpeg"}
        for index in range(1, 21)
    ] + ready_items()[2:]

    ok, reason, _ = drive_night_test.inspect_night_test(items)

    assert ok is False
    assert reason == "MP3 count must be 1; found 20"


def test_detect_marks_ready_folder_for_processing(capsys):
    with patch.object(drive_night_test, "get_drive_service", return_value=object()), patch.object(
        drive_night_test,
        "resolve_night_test",
        return_value=({"id": "night-id", "name": "night-test"}, ready_items()),
    ):
        drive_night_test.detect(args())

    output = capsys.readouterr().out
    assert "found=true" in output
    assert "folder_id=night-id" in output
    assert "reason=ready" in output


def test_detect_skips_existing_output_video(capsys):
    items = ready_items() + [
        {"id": "output-id", "name": "output", "mimeType": drive_night_test.FOLDER_MIME}
    ]
    existing = [{"id": "video-id", "name": "video.mp4", "mimeType": "video/mp4"}]
    with patch.object(drive_night_test, "get_drive_service", return_value=object()), patch.object(
        drive_night_test,
        "resolve_night_test",
        return_value=({"id": "night-id", "name": "night-test"}, items),
    ), patch.object(drive_night_test, "list_children", return_value=existing):
        drive_night_test.detect(args())

    output = capsys.readouterr().out
    assert "found=false" in output
    assert "reason=already-completed" in output
    assert "output/video.mp4 already exists" in output


def test_casefold_night_test_folder_name_is_accepted():
    items = [
        {"id": "night-id", "name": "Night-Test", "mimeType": drive_night_test.FOLDER_MIME}
    ]
    assert drive_night_test.find_casefold_folder(items, "night-test")["id"] == "night-id"
