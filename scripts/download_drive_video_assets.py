#!/usr/bin/env python3
"""Download Tokyo ChillMatic FM video assets from Google Drive for GitHub Actions."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def quote_drive_query(value: str) -> str:
    return value.replace("'", "\\'")


def get_drive_service():
    info_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    info_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_PATH")

    if info_json:
        info = json.loads(info_json)
        credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    elif info_path:
        credentials = service_account.Credentials.from_service_account_file(info_path, scopes=SCOPES)
    else:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON または GOOGLE_SERVICE_ACCOUNT_JSON_PATH を設定してください。"
        )

    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def find_single_folder(service, name: str, parent_id: str | None = None) -> dict:
    safe_name = quote_drive_query(name)
    query = (
        "mimeType = 'application/vnd.google-apps.folder' "
        f"and name = '{safe_name}' "
        "and trashed = false"
    )
    if parent_id:
        safe_parent = quote_drive_query(parent_id)
        query += f" and '{safe_parent}' in parents"
    response = service.files().list(
        q=query,
        fields="files(id,name)",
        pageSize=10,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    folders = response.get("files", [])
    if not folders:
        raise FileNotFoundError(f"Google Driveフォルダが見つかりません: {name}")
    if len(folders) > 1:
        raise RuntimeError(f"同名フォルダが複数あります: {name}")
    return folders[0]


def find_optional_file(service, name: str, parent_id: str) -> dict | None:
    safe_name = quote_drive_query(name)
    safe_parent = quote_drive_query(parent_id)
    query = f"name = '{safe_name}' and '{safe_parent}' in parents and trashed = false"
    response = service.files().list(
        q=query,
        fields="files(id,name,mimeType,size)",
        pageSize=2,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    files = response.get("files", [])
    if len(files) > 1:
        raise RuntimeError(f"同名ファイルが複数あります: {name}")
    return files[0] if files else None


def download_file(service, file_id: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    with destination.open("wb") as handle:
        downloader = MediaIoBaseDownload(handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-number", default="001", help="video_XXX の番号。例: 001")
    parser.add_argument("--output-dir", default="video_assets", help="ダウンロード先ディレクトリ")
    args = parser.parse_args()

    video_folder_name = f"video_{str(args.video_number).zfill(3)}"
    output_dir = Path(args.output_dir)
    tracks_dir = output_dir / "tracks"

    service = get_drive_service()
    root = find_single_folder(service, "Tokyo ChillMatic FM")
    videos = find_single_folder(service, "Videos", root["id"])
    video = find_single_folder(service, video_folder_name, videos["id"])
    tracks = find_single_folder(service, "tracks", video["id"])

    for index in range(1, 21):
        filename = f"track{index:02d}.mp3"
        file_record = find_optional_file(service, filename, tracks["id"])
        if not file_record:
            raise FileNotFoundError(f"必須トラックが見つかりません: {video_folder_name}/tracks/{filename}")
        download_file(service, file_record["id"], tracks_dir / filename)
        print(f"Downloaded {filename}")

    background_filenames = ("background.png", "background.jpg", "background.jpeg")
    for filename in background_filenames:
        file_record = find_optional_file(service, filename, video["id"]) or find_optional_file(service, filename, videos["id"])
        if file_record:
            download_file(service, file_record["id"], output_dir / filename)
            print(f"Downloaded {filename}")
            break
    else:
        raise FileNotFoundError(f"必須背景素材が見つかりません: {', '.join(background_filenames)}")

    for filename in ("rain.mp3", "rain_overlay.mp4"):
        file_record = find_optional_file(service, filename, video["id"]) or find_optional_file(service, filename, videos["id"])
        if file_record:
            download_file(service, file_record["id"], output_dir / filename)
            print(f"Downloaded {filename}")
        else:
            print(f"Optional {filename} not found; continuing without it")


if __name__ == "__main__":
    main()
