#!/usr/bin/env python3
"""Upload a generated MP4 to YouTube as a private video."""

from __future__ import annotations

import argparse
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
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    return values


def get_youtube_service():
    env = required_env(("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"))
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
        print(f"YouTube API upload failed: {exc}")
        raise

    video_id = uploaded.get("id")
    print(f"Uploaded private YouTube video: {video_id}")
    if video_id:
        print(f"YouTube Studio URL: https://studio.youtube.com/video/{video_id}/edit")


if __name__ == "__main__":
    main()
