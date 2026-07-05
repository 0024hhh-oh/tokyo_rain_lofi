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
IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg"}
BACKGROUND_LOOP_NAME = "background_loop.mp4"
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
ROOT_FOLDER = "Tokyo ChillMatic FM"
ROOT_FOLDER_ID_ENV = "TOKYO_CHILLMATIC_DRIVE_FOLDER_ID"


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
        f"mimeType = '{FOLDER_MIME_TYPE}' "
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


def get_folder_by_id(service, folder_id: str) -> dict:
    folder = service.files().get(
        fileId=folder_id,
        fields="id,name,mimeType",
        supportsAllDrives=True,
    ).execute()
    if folder.get("mimeType") != FOLDER_MIME_TYPE:
        raise RuntimeError(f"Google Drive ID is not a folder: {folder_id}")
    return folder


def resolve_root_folder(service, root_folder_name: str, root_folder_id: str | None = None) -> dict:
    if root_folder_id:
        return get_folder_by_id(service, root_folder_id)
    return find_single_folder(service, root_folder_name)


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


def list_files(service, parent_id: str) -> list[dict]:
    files: list[dict] = []
    page_token = None
    safe_parent = quote_drive_query(parent_id)
    query = f"'{safe_parent}' in parents and trashed = false"
    while True:
        response = service.files().list(
            q=query,
            fields="nextPageToken,files(id,name,mimeType,size)",
            pageSize=100,
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            orderBy="name",
        ).execute()
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return files


def download_file(service, file_id: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    with destination.open("wb") as handle:
        downloader = MediaIoBaseDownload(handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def download_legacy_video_folder(service, video_number: str, output_dir: Path, root_folder_id: str | None = None) -> None:
    video_folder_name = f"video_{str(video_number).zfill(3)}"
    tracks_dir = output_dir / "tracks"
    root = resolve_root_folder(service, ROOT_FOLDER, root_folder_id)
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

    background_loop = find_optional_file(service, BACKGROUND_LOOP_NAME, video["id"]) or find_optional_file(service, BACKGROUND_LOOP_NAME, videos["id"])
    background_png = find_optional_file(service, "background.png", video["id"]) or find_optional_file(service, "background.png", videos["id"])
    if background_loop:
        download_file(service, background_loop["id"], output_dir / BACKGROUND_LOOP_NAME)
        print(f"Downloaded {BACKGROUND_LOOP_NAME}")
    elif background_png:
        download_file(service, background_png["id"], output_dir / "background.png")
        print("Downloaded background.png")
    else:
        raise FileNotFoundError("background_loop.mp4 または background.png が必要です")

    for filename in ("rain.mp3", "rain_overlay.mp4"):
        file_record = find_optional_file(service, filename, video["id"]) or find_optional_file(service, filename, videos["id"])
        if file_record:
            download_file(service, file_record["id"], output_dir / filename)
            print(f"Downloaded {filename}")
        else:
            print(f"Optional {filename} not found; continuing without it")


def download_incoming_work_folder(service, folder_id: str, output_dir: Path) -> None:
    tracks_dir = output_dir / "tracks"
    children = list_files(service, folder_id)
    mp3_files = [item for item in children if item["name"].lower().endswith(".mp3")]
    background_loop_files = [item for item in children if item["name"].lower() == BACKGROUND_LOOP_NAME]
    image_files = [
        item for item in children
        if item["name"].lower().startswith("background.")
        and (item.get("mimeType") in IMAGE_MIME_TYPES or item["name"].lower().endswith((".png", ".jpg", ".jpeg")))
    ]
    if len(background_loop_files) > 1:
        raise FileNotFoundError(f"background_loop.mp4 は1つだけ必要です。検出数: {len(background_loop_files)}")
    if len(image_files) > 1:
        raise FileNotFoundError(f"background画像は1枚だけ必要です。検出数: {len(image_files)}")
    if not background_loop_files and not image_files:
        raise FileNotFoundError("background_loop.mp4 または background.png が必要です")
    if len(mp3_files) < 1:
        raise FileNotFoundError("mp3音源が見つかりません。理想は20曲、最低1曲以上が必要です。")
    if len(mp3_files) < 20:
        print(f"Warning: mp3音源は{len(mp3_files)}曲です。理想は20曲です。")

    if background_loop_files:
        background_loop = background_loop_files[0]
        download_file(service, background_loop["id"], output_dir / BACKGROUND_LOOP_NAME)
        print(f"Downloaded {background_loop['name']} as {BACKGROUND_LOOP_NAME}")
    else:
        background = image_files[0]
        suffix = Path(background["name"]).suffix.lower() or ".png"
        download_file(service, background["id"], output_dir / f"background{suffix}")
        print(f"Downloaded {background['name']} as background{suffix}")

    for index, item in enumerate(mp3_files[:20], start=1):
        destination = tracks_dir / f"track{index:02d}.mp3"
        download_file(service, item["id"], destination)
        print(f"Downloaded {item['name']} as {destination.name}")

    if len(mp3_files) < 20:
        for index in range(len(mp3_files) + 1, 21):
            source = tracks_dir / f"track{((index - 1) % len(mp3_files)) + 1:02d}.mp3"
            destination = tracks_dir / f"track{index:02d}.mp3"
            destination.write_bytes(source.read_bytes())
            print(f"Duplicated {source.name} as {destination.name} to keep generator input compatible")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-number", default="001", help="video_XXX の番号。例: 001")
    parser.add_argument("--drive-folder-id", help="incoming内の作品フォルダID。指定時はこのフォルダから直接取得します。")
    parser.add_argument("--root-folder-id", default=os.environ.get(ROOT_FOLDER_ID_ENV), help=f"DriveルートフォルダID（{ROOT_FOLDER_ID_ENV} が指定されていればID優先）")
    parser.add_argument("--output-dir", default="video_assets", help="ダウンロード先ディレクトリ")
    args = parser.parse_args()

    service = get_drive_service()
    output_dir = Path(args.output_dir)
    if args.drive_folder_id:
        download_incoming_work_folder(service, args.drive_folder_id, output_dir)
    else:
        download_legacy_video_folder(service, args.video_number, output_dir, args.root_folder_id)


if __name__ == "__main__":
    main()
