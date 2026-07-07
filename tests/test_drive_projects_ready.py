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
googleapiclient.http = types.ModuleType("googleapiclient.http")


class FakeMediaIoBaseDownload:
    def __init__(self, handle, request):
        self.handle = handle
        self.request = request
        self.done = False

    def next_chunk(self):
        if not self.done:
            self.handle.write(f"downloaded:{self.request}".encode("utf-8"))
            self.done = True
        return None, True


googleapiclient.http.MediaIoBaseDownload = FakeMediaIoBaseDownload
googleapiclient.http.MediaFileUpload = (
    lambda filename, mimetype=None, resumable=False: {
        "filename": filename,
        "mimetype": mimetype,
        "resumable": resumable,
    }
)
googleapiclient.discovery.build = lambda *args, **kwargs: None
sys.modules.setdefault("google", google)
sys.modules.setdefault("google.oauth2", google.oauth2)
sys.modules.setdefault("google.oauth2.service_account", google.oauth2.service_account)
sys.modules.setdefault("googleapiclient", googleapiclient)
sys.modules.setdefault("googleapiclient.discovery", googleapiclient.discovery)
sys.modules.setdefault("googleapiclient.http", googleapiclient.http)

import drive_projects_ready


def make_tracks(count):
    return [
        {"id": f"t{i}", "name": f"track{i:02}.mp3", "mimeType": "audio/mpeg"}
        for i in range(1, count + 1)
    ]


def inspect_with_children(children):
    with patch.object(drive_projects_ready, "list_files", return_value=children):
        return drive_projects_ready.inspect_project_folder(
            None, {"id": "folder-id", "name": "YOYOGI"}
        )


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
        {
            "id": "loop",
            "name": " background_loop.mp4 ",
            "mimeType": "application/octet-stream",
        },
        *make_tracks(20),
    ]

    ok, reason = inspect_with_children(children)

    assert ok is True
    assert "background_loop.mp4優先" in reason


def test_single_video_file_with_quicktime_mime_is_ready():
    children = [
        {"id": "video", "name": "capcut export", "mimeType": "video/quicktime"},
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


def test_projects_root_assets_are_skipped_without_drive_copy_or_upload(capsys):
    direct_files = [
        {"id": f"song-{i:02}", "name": f"song{i:02}.mp3", "mimeType": "audio/mpeg"}
        for i in range(1, 21)
    ] + [{"id": "bg", "name": "background.mp4", "mimeType": "video/mp4"}]

    def fake_list_files(
        _service,
        query,
        fields="files(id,name,mimeType,createdTime,modifiedTime,parents)",
    ):
        if "'projects-id' in parents" in query and "mimeType =" not in query:
            return direct_files
        return []

    args = types.SimpleNamespace(
        root_folder="Tokyo ChillMatic FM",
        root_folder_id=None,
        projects_folder="Projects",
        incoming_folder="incoming",
        processed_folder="processed",
        completed_folder="completed",
        failed_folder="failed",
        dry_run=False,
    )

    with patch.object(
        drive_projects_ready, "get_drive_service", return_value=object()
    ), patch.object(
        drive_projects_ready,
        "resolve_root_folder",
        return_value={"id": "root-id", "name": "root"},
    ), patch.object(
        drive_projects_ready,
        "find_single_folder",
        return_value={"id": "projects-id", "name": "Projects"},
    ), patch.object(
        drive_projects_ready,
        "ensure_child_folder",
        side_effect=lambda _s, _p, name: {"id": f"{name}-id", "name": name},
    ), patch.object(
        drive_projects_ready, "list_files", side_effect=fake_list_files
    ):
        drive_projects_ready.check_projects(args)

    output = capsys.readouterr().out
    assert "Projects直下ファイル方式は読み取り専用扱い" in output
    assert "Drive上ではcopy/create/uploadを行わない" in output


def test_projects_root_batch_marker_prevents_duplicate_copy(capsys):
    mp3s = [
        {"id": f"song-{i:02}", "name": f"song{i:02}.mp3", "mimeType": "audio/mpeg"}
        for i in range(1, 21)
    ]
    background = {"id": "bg", "name": "background.jpg", "mimeType": "image/jpeg"}
    direct_files = [*mp3s, background]
    marker = drive_projects_ready.project_batch_marker_name(mp3s, background)

    def fake_list_files(
        _service,
        query,
        fields="files(id,name,mimeType,createdTime,modifiedTime,parents)",
    ):
        if "'projects-id' in parents" in query and "mimeType =" not in query:
            return direct_files
        if f"name = '{marker}'" in query and "'processed-id' in parents" in query:
            return [{"id": "marker-id", "name": marker}]
        return []

    args = types.SimpleNamespace(
        root_folder="Tokyo ChillMatic FM",
        root_folder_id=None,
        projects_folder="Projects",
        incoming_folder="incoming",
        processed_folder="processed",
        completed_folder="completed",
        failed_folder="failed",
        dry_run=False,
    )

    with patch.object(
        drive_projects_ready, "get_drive_service", return_value=object()
    ), patch.object(
        drive_projects_ready,
        "resolve_root_folder",
        return_value={"id": "root-id", "name": "root"},
    ), patch.object(
        drive_projects_ready,
        "find_single_folder",
        return_value={"id": "projects-id", "name": "Projects"},
    ), patch.object(
        drive_projects_ready,
        "ensure_child_folder",
        side_effect=lambda _s, _p, name: {"id": f"{name}-id", "name": name},
    ), patch.object(
        drive_projects_ready, "list_files", side_effect=fake_list_files
    ):
        drive_projects_ready.check_projects(args)

    output = capsys.readouterr().out
    assert "Projects直下ファイル方式は読み取り専用扱い" in output
    assert "Drive上ではcopy/create/uploadを行わない" in output
