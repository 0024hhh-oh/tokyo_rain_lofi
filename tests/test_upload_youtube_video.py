import importlib
import json
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

google = sys.modules.setdefault("google", types.ModuleType("google"))
google.auth = sys.modules.setdefault("google.auth", types.ModuleType("google.auth"))
google.auth.transport = sys.modules.setdefault("google.auth.transport", types.ModuleType("google.auth.transport"))
google.auth.transport.requests = types.ModuleType("google.auth.transport.requests")
google.auth.transport.requests.Request = lambda: object()
google.oauth2 = sys.modules.setdefault("google.oauth2", types.ModuleType("google.oauth2"))
google.oauth2.credentials = types.ModuleType("google.oauth2.credentials")
google.oauth2.credentials.Credentials = lambda **kwargs: types.SimpleNamespace(refresh=lambda request: None)

googleapiclient = sys.modules.setdefault("googleapiclient", types.ModuleType("googleapiclient"))
googleapiclient.discovery = sys.modules.setdefault("googleapiclient.discovery", types.ModuleType("googleapiclient.discovery"))
googleapiclient.discovery.build = lambda *args, **kwargs: None
googleapiclient.http = sys.modules.setdefault("googleapiclient.http", types.ModuleType("googleapiclient.http"))
googleapiclient.http.MediaFileUpload = lambda *args, **kwargs: object()
googleapiclient.errors = types.ModuleType("googleapiclient.errors")


class HttpError(Exception):
    def __init__(self, resp, content):
        super().__init__(content)
        self.resp = resp
        self.content = content


googleapiclient.errors.HttpError = HttpError
sys.modules["google.auth.transport.requests"] = google.auth.transport.requests
sys.modules["google.oauth2.credentials"] = google.oauth2.credentials
sys.modules["googleapiclient.errors"] = googleapiclient.errors

upload_youtube_video = importlib.import_module("upload_youtube_video")


def test_required_env_accepts_all_youtube_credentials(monkeypatch):
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "client")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "refresh")

    assert upload_youtube_video.required_env(upload_youtube_video.YOUTUBE_SECRET_NAMES) == {
        "YOUTUBE_CLIENT_ID": "client",
        "YOUTUBE_CLIENT_SECRET": "secret",
        "YOUTUBE_REFRESH_TOKEN": "refresh",
    }


def test_required_env_reports_missing_youtube_secret_names(monkeypatch):
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "client")
    monkeypatch.delenv("YOUTUBE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("YOUTUBE_REFRESH_TOKEN", raising=False)

    with pytest.raises(RuntimeError) as excinfo:
        upload_youtube_video.required_env(upload_youtube_video.YOUTUBE_SECRET_NAMES)

    message = str(excinfo.value)
    assert "Missing required YouTube GitHub Secrets" in message
    assert "YOUTUBE_CLIENT_SECRET" in message
    assert "YOUTUBE_REFRESH_TOKEN" in message


def test_main_logs_success_video_id_and_urls(monkeypatch, tmp_path, capsys):
    video = tmp_path / "incoming_work.mp4"
    video.write_bytes(b"mp4")

    def fake_upload(file_path: Path, title: str, description: str, tags: list[str]):
        assert file_path == video
        assert title == "title"
        assert tags == ["lofi", "rain"]
        return {"id": "abc123"}

    monkeypatch.setattr(upload_youtube_video, "upload_video", fake_upload)
    monkeypatch.setattr(
        "sys.argv",
        ["upload_youtube_video.py", "--file", str(video), "--title", "title", "--tags", "lofi, rain"],
    )

    upload_youtube_video.main()

    output = capsys.readouterr().out
    assert "アップロード成功" in output
    assert "video ID: abc123" in output
    assert "https://studio.youtube.com/video/abc123/edit" in output
    assert "https://www.youtube.com/watch?v=abc123" in output


def test_main_logs_http_status_google_reason_and_exception_type(monkeypatch, tmp_path, capsys):
    video = tmp_path / "incoming_work.mp4"
    video.write_bytes(b"mp4")
    content = json.dumps({"error": {"errors": [{"reason": "quotaExceeded"}]}}).encode()
    error = upload_youtube_video.HttpError(types.SimpleNamespace(status=403), content)

    def fake_upload(*args, **kwargs):
        raise error

    monkeypatch.setattr(upload_youtube_video, "upload_video", fake_upload)
    monkeypatch.setattr("sys.argv", ["upload_youtube_video.py", "--file", str(video), "--title", "title"])

    with pytest.raises(upload_youtube_video.HttpError):
        upload_youtube_video.main()

    output = capsys.readouterr().out
    assert "HTTP status: 403" in output
    assert "Google API error reason: quotaExceeded" in output
    assert "Exception type: HttpError" in output
