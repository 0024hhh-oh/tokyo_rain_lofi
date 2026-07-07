import importlib
import sys
import types
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

google = types.ModuleType("google")
google.oauth2 = types.ModuleType("google.oauth2")
google.oauth2.service_account = types.ModuleType("google.oauth2.service_account")
google.oauth2.service_account.Credentials = types.SimpleNamespace(
    from_service_account_info=lambda info, scopes=None: {"info": info, "scopes": scopes},
    from_service_account_file=lambda path, scopes=None: {"path": path, "scopes": scopes},
)
googleapiclient = types.ModuleType("googleapiclient")
googleapiclient.discovery = types.ModuleType("googleapiclient.discovery")
googleapiclient.discovery.build = lambda *args, **kwargs: None
googleapiclient.http = types.ModuleType("googleapiclient.http")
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

upload_drive_output = importlib.import_module("upload_drive_output")


class FakeRequest:
    def __init__(self, result):
        self.result = result

    def execute(self):
        return self.result


class FakeFiles:
    def __init__(self):
        self.created_body = None
        self.updated_body = None
        self.updated_file_id = None

    def get(self, fileId, fields, supportsAllDrives):
        assert fileId == "folder-id"
        return FakeRequest({"id": "folder-id", "name": "Outputs", "mimeType": upload_drive_output.FOLDER_MIME_TYPE})

    def list(self, **kwargs):
        return FakeRequest({"files": []})

    def create(self, body, media_body, fields, supportsAllDrives):
        self.created_body = body
        return FakeRequest({"id": "new-file-id", "name": body["name"], "webViewLink": "https://drive/file"})

    def update(self, fileId, media_body, body, fields, supportsAllDrives):
        self.updated_file_id = fileId
        self.updated_body = body
        return FakeRequest({"id": fileId, "name": body["name"]})


class FakeService:
    def __init__(self):
        self.files_api = FakeFiles()

    def files(self):
        return self.files_api


def test_main_uploads_to_specified_folder_and_logs_ids(tmp_path, capsys, monkeypatch):
    mp4 = tmp_path / "done.mp4"
    mp4.write_bytes(b"video")
    service = FakeService()
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"client_email":"svc@example.com"}')
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "upload_drive_output.py",
            "--file",
            str(mp4),
            "--output-name",
            "done.mp4",
            "--output-folder-id",
            "folder-id",
        ],
    )

    with patch.object(upload_drive_output, "get_drive_service", return_value=service), patch.object(
        upload_drive_output,
        "MediaFileUpload",
        lambda filename, mimetype=None, resumable=False: {"filename": filename, "mimetype": mimetype, "resumable": resumable},
    ):
        upload_drive_output.main()

    assert service.files_api.created_body == {"name": "done.mp4", "parents": ["folder-id"]}
    output = capsys.readouterr().out
    assert "Creating new Drive file: file_name=done.mp4 folder_id=folder-id" in output
    assert "Google Drive upload completed: file_id=new-file-id file_name=done.mp4 folder_id=folder-id" in output
    assert "Drive URL: https://drive/file" in output


def test_main_logs_detailed_error_and_exits(tmp_path, capsys, monkeypatch):
    missing = tmp_path / "missing.mp4"
    monkeypatch.setattr(
        sys,
        "argv",
        ["upload_drive_output.py", "--file", str(missing), "--output-name", "missing.mp4", "--output-folder-id", "folder-id"],
    )

    try:
        upload_drive_output.main()
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("SystemExit was not raised")

    err = capsys.readouterr().err
    assert "Google Drive upload failed." in err
    assert "Error type: FileNotFoundError" in err
    assert "アップロード対象MP4が見つかりません" in err
    assert "Traceback" in err


def test_resolve_output_folder_id_requires_explicit_output_folder(monkeypatch):
    monkeypatch.delenv(upload_drive_output.OUTPUT_FOLDER_ID_ENV, raising=False)
    monkeypatch.setenv(upload_drive_output.LEGACY_ROOT_FOLDER_ID_ENV, "root-id")
    args = types.SimpleNamespace(output_folder_id="")

    try:
        upload_drive_output.resolve_output_folder_id(args)
    except RuntimeError as exc:
        assert upload_drive_output.OUTPUT_FOLDER_ID_ENV in str(exc)
        assert upload_drive_output.LEGACY_ROOT_FOLDER_ID_ENV in str(exc)
    else:
        raise AssertionError("RuntimeError was not raised")
