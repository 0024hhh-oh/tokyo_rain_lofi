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
sys.modules.setdefault("google", google)
sys.modules.setdefault("google.oauth2", google.oauth2)
sys.modules.setdefault("google.oauth2.service_account", google.oauth2.service_account)
sys.modules.setdefault("googleapiclient", googleapiclient)
sys.modules.setdefault("googleapiclient.discovery", googleapiclient.discovery)

import drive_incoming_queue


def make_tracks(count):
    return [
        {"id": f"t{i}", "name": f"track{i:02}.MP3", "mimeType": "audio/mpeg"}
        for i in range(1, count + 1)
    ]


def validate_with_children(children, capsys):
    folder = {"id": "work-folder-id", "name": "SHIBUYA Rain"}
    with patch.object(drive_incoming_queue, "list_files", return_value=children):
        result = drive_incoming_queue.validate_work_folder(None, folder)
    return result, capsys.readouterr().out


def test_validate_work_folder_logs_counts_and_accepts_normalized_names(capsys):
    children = [
        {
            "id": "bg",
            "name": " background_loop.mp4 ",
            "mimeType": "application/octet-stream",
        },
        {"id": "nested", "name": "notes", "mimeType": drive_incoming_queue.FOLDER_MIME},
        *make_tracks(1),
    ]

    (ok, reason, track_count), output = validate_with_children(children, capsys)

    assert ok is True
    assert track_count == 1
    assert "mp3音源は1曲" in reason
    assert "対象フォルダ: name=SHIBUYA Rain id=work-folder-id" in output
    assert "検出したファイル数: 2" in output
    assert "検出したフォルダ数: 1" in output
    assert "判定内訳: background_loop.mp4=1, background画像=0, mp3=1" in output


def test_validate_work_folder_reports_actual_skip_condition(capsys):
    children = [
        {
            "id": "nested",
            "name": "assets",
            "mimeType": drive_incoming_queue.FOLDER_MIME,
        },
        *make_tracks(2),
    ]

    (ok, reason, track_count), output = validate_with_children(children, capsys)

    assert ok is False
    assert track_count == 2
    assert reason == "background_loop.mp4 または background.png が必要です"
    assert "検出したファイル数: 2" in output
    assert "検出したフォルダ数: 1" in output
    assert "判定内訳: background_loop.mp4=0, background画像=0, mp3=2" in output
