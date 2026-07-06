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
    assert (
        "各フォルダ内のファイル一覧: folder=SHIBUYA Rain id=work-folder-id count=3"
        in output
    )
    assert (
        "file[1]: name= background_loop.mp4  id=bg mimeType=application/octet-stream"
        in output
    )
    assert "検出したファイル数: 2" in output
    assert "検出したフォルダ数: 1" in output
    assert "background検出数: 1" in output
    assert "track検出数: 1" in output
    assert "判定内訳: background_loop.mp4=1, background画像=0, mp3=1" in output
    assert "background_loop.mp4 があるか: yes" in output
    assert "mp3 が何個あるか: 1" in output
    assert "有効判定の理由: mp3音源は1曲" in output


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
    assert "background_loop.mp4 があるか: no" in output
    assert "mp3 が何個あるか: 2" in output
    assert (
        "無効判定の理由: background_loop.mp4 または background.png が必要です" in output
    )


def test_move_destination_choices_are_completed_or_failed():
    # Verify the production parser contract by checking the source-level choices users can pass.
    source = Path(drive_incoming_queue.__file__).read_text()
    assert 'parser.add_argument("--completed-folder", default="completed")' in source
    assert (
        'parser.add_argument("--destination", choices=("completed", "failed"))'
        in source
    )
    assert "processed" not in source


def test_log_incoming_work_folders_includes_id_and_folder_list(capsys):
    incoming = {"id": "incoming-id", "name": "incoming"}
    work_folders = [
        {
            "id": "work-1",
            "name": "Night Rain",
            "mimeType": drive_incoming_queue.FOLDER_MIME,
        },
        {
            "id": "work-2",
            "name": "City Rain",
            "mimeType": drive_incoming_queue.FOLDER_MIME,
        },
    ]

    incoming_items = [
        *work_folders,
        {"id": "readme", "name": "README.txt", "mimeType": "text/plain"},
    ]

    drive_incoming_queue.log_incoming_items(incoming, incoming_items)
    drive_incoming_queue.log_incoming_work_folders(incoming, work_folders)
    output = capsys.readouterr().out

    assert "incoming folder id: incoming-id" in output
    assert "incoming内で取得できた全item一覧: count=3" in output
    assert "incoming item[3]: name=README.txt id=readme mimeType=text/plain" in output
    assert "フォルダ候補一覧: count=2" in output
    assert "incoming直下のフォルダ一覧: count=2" in output
    assert (
        "フォルダ候補[1]: name=Night Rain id=work-1 mimeType=application/vnd.google-apps.folder"
        in output
    )
    assert (
        "incoming直下フォルダ[1]: name=Night Rain id=work-1 mimeType=application/vnd.google-apps.folder"
        in output
    )
    assert (
        "incoming直下フォルダ[2]: name=City Rain id=work-2 mimeType=application/vnd.google-apps.folder"
        in output
    )
