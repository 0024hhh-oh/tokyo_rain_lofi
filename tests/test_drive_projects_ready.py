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

import drive_projects_ready


def make_tracks(count):
    return [{"id": f"t{i}", "name": f"track{i:02}.mp3", "mimeType": "audio/mpeg"} for i in range(1, count + 1)]


def inspect_with_children(children):
    with patch.object(drive_projects_ready, "list_files", return_value=children):
        return drive_projects_ready.inspect_project_folder(None, {"id": "folder-id", "name": "YOYOGI"})


def test_background_loop_mp4_is_accepted_and_prioritized_over_background_png():
    children = [
        {"id": "loop", "name": "background_loop.mp4", "mimeType": "video/mp4"},
        {"id": "png", "name": "background.png", "mimeType": "image/png"},
        *make_tracks(20),
    ]

    ok, reason = inspect_with_children(children)

    assert ok is True
    assert "background_loop.mp4優先" in reason


def test_background_loop_name_is_normalized_before_matching():
    children = [
        {"id": "loop", "name": " background_loop.mp4 ", "mimeType": "application/octet-stream"},
        *make_tracks(20),
    ]

    ok, reason = inspect_with_children(children)

    assert ok is True
    assert "background_loop.mp4優先" in reason


def test_missing_background_message_includes_google_drive_file_list():
    children = make_tracks(20)

    ok, reason = inspect_with_children(children)

    assert ok is False
    assert "取得一覧:" in reason
    assert "track01.mp3 [audio/mpeg]" in reason
