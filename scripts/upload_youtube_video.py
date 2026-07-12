#!/usr/bin/env python3
"""Upload a generated MP4 to YouTube as a private video."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_URI = "https://oauth2.googleapis.com/token"
YOUTUBE_SECRET_NAMES = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")


def parse_tags(raw_tags: str) -> list[str]:
    return [tag.strip() for tag in raw_tags.split(",") if tag.strip()]


def required_env(names: Iterable[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    missing: list[str] = []
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            values[name] = value
        else:
            missing.append(name)
    if missing:
        raise RuntimeError(f"Missing required YouTube GitHub Secrets: {', '.join(missing)}")
    return values


def get_youtube_service():
    env = required_env(YOUTUBE_SECRET_NAMES)
    credentials = Credentials(
        token=None,
        refresh_token=env["YOUTUBE_REFRESH_TOKEN"],
        token_uri=TOKEN_URI,
        client_id=env["YOUTUBE_CLIENT_ID"],
        client_secret=env["YOUTUBE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    credentials.refresh(Request())
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def upload_video(file_path: Path, title: str, description: str, tags: list[str]) -> dict:
    youtube = get_youtube_service()
    body = {
        "snippet": {
            "title": title,
            "description": description,
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
        },
    }
    if tags:
        body["snippet"]["tags"] = tags

    media = MediaFileUpload(str(file_path), mimetype="video/mp4", chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"YouTube upload progress: {int(status.progress() * 100)}%")
    return response


def google_api_error_reason(exc: HttpError) -> str:
    try:
        payload = json.loads(exc.content.decode("utf-8"))
    except Exception:
        return "unparseable_error_response"

    error = payload.get("error", {})
    errors = error.get("errors") or []
    reasons = [str(item.get("reason")) for item in errors if item.get("reason")]
    if reasons:
        return ", ".join(reasons)
    if error.get("status"):
        return str(error["status"])
    if error.get("message"):
        return str(error["message"])
    return "unknown"


def log_http_error(exc: HttpError) -> None:
    status = getattr(exc.resp, "status", "unknown")
    reason = google_api_error_reason(exc)
    print("YouTube API upload failed.")
    print(f"HTTP status: {status}")
    print(f"Google API error reason: {reason}")
    print(f"Exception type: {type(exc).__name__}")
    print(f"Exception detail: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload an MP4 to YouTube as private.")
    parser.add_argument("--file", required=True, help="Path to the generated MP4 file.")
    parser.add_argument("--title", required=True, help="YouTube video title.")
    parser.add_argument("--description", default="", help="YouTube video description.")
    parser.add_argument("--tags", default="", help="Comma-separated YouTube tags.")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.is_file():
        raise FileNotFoundError(f"MP4 file not found: {file_path}")

    try:
        uploaded = upload_video(file_path, args.title, args.description, parse_tags(args.tags))
    except HttpError as exc:
        log_http_error(exc)
        raise
    except Exception as exc:
        print("YouTube upload failed.")
        print("HTTP status: not_available")
        print("Google API error reason: not_available")
        print(f"Exception type: {type(exc).__name__}")
        print(f"Exception detail: {exc}")
        raise

    video_id = uploaded.get("id")
    print("アップロード成功")
    print(f"video ID: {video_id}")
    if video_id:
        print(f"YouTube Studio URL: https://studio.youtube.com/video/{video_id}/edit")
        print(f"Video URL: https://www.youtube.com/watch?v={video_id}")


if __name__ == "__main__":
    main()
