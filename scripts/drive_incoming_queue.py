#!/usr/bin/env python3
"""Find and move Google Drive incoming work folders for automated Actions runs."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive"]
ROOT_FOLDER = "Tokyo ChillMatic FM"
ROOT_FOLDER_ID_ENV = "TOKYO_CHILLMATIC_DRIVE_FOLDER_ID"
FOLDER_MIME = "application/vnd.google-apps.folder"
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
BACKGROUND_LOOP_NAME = "background_loop.mp4"
VIDEO_MIME_PREFIX = "video/"
MP4_MIME_TYPES = {"video/mp4", "application/octet-stream"}
IMAGE_MIME_PREFIX = "image/"
IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "application/octet-stream"}
SHORTCUT_MIME = "application/vnd.google-apps.shortcut"


def quote_drive_query(value: str) -> str:
    return value.replace("'", "\\'")


def get_drive_service():
    info_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    info_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_PATH")
    if info_json:
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(info_json), scopes=SCOPES
        )
    elif info_path:
        credentials = service_account.Credentials.from_service_account_file(
            info_path, scopes=SCOPES
        )
    else:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON または GOOGLE_SERVICE_ACCOUNT_JSON_PATH を設定してください。"
        )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def list_files(
    service,
    query: str,
    fields: str = "files(id,name,mimeType,createdTime,modifiedTime,parents)",
) -> list[dict]:
    results: list[dict] = []
    page_token = None
    while True:
        response = (
            service.files()
            .list(
                q=query,
                fields=f"nextPageToken,{fields}",
                orderBy="createdTime",
                pageSize=100,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return results


def find_single_folder(service, name: str, parent_id: str | None = None) -> dict:
    query = f"mimeType = '{FOLDER_MIME}' and name = '{quote_drive_query(name)}' and trashed = false"
    if parent_id:
        query += f" and '{quote_drive_query(parent_id)}' in parents"
    folders = list_files(service, query, fields="files(id,name)")
    if len(folders) != 1:
        raise RuntimeError(
            f"Google Driveフォルダ {name} の検出数が不正です: {len(folders)}"
        )
    return folders[0]


def get_folder_by_id(service, folder_id: str) -> dict:
    folder = (
        service.files()
        .get(
            fileId=folder_id,
            fields="id,name,mimeType",
            supportsAllDrives=True,
        )
        .execute()
    )
    if folder.get("mimeType") != FOLDER_MIME:
        raise RuntimeError(f"Google Drive ID is not a folder: {folder_id}")
    return folder


def resolve_root_folder(
    service, root_folder_name: str, root_folder_id: str | None = None
) -> dict:
    if root_folder_id:
        return get_folder_by_id(service, root_folder_id)
    return find_single_folder(service, root_folder_name)


def normalized_drive_name(item: dict) -> str:
    return item.get("name", "").strip().casefold()


def is_folder(item: dict) -> bool:
    return item.get("mimeType") == FOLDER_MIME


def is_background_loop(item: dict) -> bool:
    if normalized_drive_name(item) != BACKGROUND_LOOP_NAME:
        return False
    mime_type = item.get("mimeType", "")
    return (
        mime_type.startswith(VIDEO_MIME_PREFIX)
        or mime_type in MP4_MIME_TYPES
        or mime_type == SHORTCUT_MIME
    )


def is_background_image(item: dict) -> bool:
    name = normalized_drive_name(item)
    mime_type = item.get("mimeType", "")
    return (
        name.startswith("background.")
        and name.endswith(IMAGE_EXTENSIONS)
        and (
            mime_type.startswith(IMAGE_MIME_PREFIX)
            or mime_type in IMAGE_MIME_TYPES
            or mime_type == SHORTCUT_MIME
        )
    )


def is_mp3(item: dict) -> bool:
    return normalized_drive_name(item).endswith(".mp3")


def describe_children(children: list[dict]) -> str:
    if not children:
        return "取得アイテムなし"
    return ", ".join(
        f"{item.get('name', '<no name>')} [{item.get('mimeType', '<no mime>')}]"
        for item in children
    )


def ensure_child_folder(service, parent_id: str, name: str) -> dict:
    query = f"mimeType = '{FOLDER_MIME}' and name = '{quote_drive_query(name)}' and '{quote_drive_query(parent_id)}' in parents and trashed = false"
    folders = list_files(service, query, fields="files(id,name)")
    if folders:
        return folders[0]
    return (
        service.files()
        .create(
            body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]},
            fields="id,name",
            supportsAllDrives=True,
        )
        .execute()
    )


def validate_work_folder(service, folder: dict) -> tuple[bool, str, int]:
    folder_id = folder["id"]
    children = list_files(
        service,
        f"'{quote_drive_query(folder_id)}' in parents and trashed = false",
        fields="files(id,name,mimeType,shortcutDetails)",
    )
    child_folders = [item for item in children if is_folder(item)]
    child_files = [item for item in children if not is_folder(item)]
    background_loops = [item for item in children if is_background_loop(item)]
    backgrounds = [item for item in children if is_background_image(item)]
    mp3s = [item for item in children if is_mp3(item)]

    print(f"対象フォルダ: name={folder.get('name', '<no name>')} id={folder_id}")
    print(f"検出したファイル数: {len(child_files)}")
    print(f"検出したフォルダ数: {len(child_folders)}")
    print(
        "判定内訳: "
        f"background_loop.mp4={len(background_loops)}, "
        f"background画像={len(backgrounds)}, "
        f"mp3={len(mp3s)}"
    )
    print(f"検出アイテム: {describe_children(children)}")

    if len(background_loops) > 1:
        return (
            False,
            f"background_loop.mp4 は1つだけ必要です（検出数: {len(background_loops)}）",
            len(mp3s),
        )
    if len(backgrounds) > 1:
        return (
            False,
            f"background画像は1枚だけ必要です（検出数: {len(backgrounds)}）",
            len(mp3s),
        )
    if not background_loops and not backgrounds:
        return False, "background_loop.mp4 または background.png が必要です", len(mp3s)
    if len(mp3s) < 1:
        return False, "mp3音源がありません（理想は20曲）", 0
    if len(mp3s) < 20:
        return (
            True,
            f"mp3音源は{len(mp3s)}曲です（理想は20曲）。不足分は生成前に複製して互換性を保ちます。",
            len(mp3s),
        )
    return True, "素材OK", len(mp3s)


def write_github_output(values: dict[str, str]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        for key, value in values.items():
            print(f"{key}={value}")
        return
    with Path(output_path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def safe_file_stem(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-") or "incoming_work"


def detect(args: argparse.Namespace) -> None:
    service = get_drive_service()
    root = resolve_root_folder(service, args.root_folder, args.root_folder_id)
    incoming = ensure_child_folder(service, root["id"], args.incoming_folder)
    ensure_child_folder(service, root["id"], args.processed_folder)
    ensure_child_folder(service, root["id"], args.failed_folder)
    query = f"mimeType = '{FOLDER_MIME}' and '{quote_drive_query(incoming['id'])}' in parents and trashed = false"
    work_folders = list_files(service, query)
    print(f"incomingフォルダ: name={incoming['name']} id={incoming['id']}")
    print(f"incoming内の作品フォルダ数: {len(work_folders)}")
    if not work_folders:
        print("スキップ理由: incoming内に作品フォルダがありません")
    for folder in work_folders:
        ok, message, track_count = validate_work_folder(service, folder)
        if not ok:
            print(f"スキップ理由: {folder['name']} - {message}")
            continue
        print(f"処理対象: {folder['name']} - {message}")
        stem = safe_file_stem(folder["name"])
        write_github_output(
            {
                "found": "true",
                "work_folder_id": folder["id"],
                "work_folder_name": folder["name"],
                "track_count": str(track_count),
                "output_file": f"{stem}.mp4",
                "youtube_title": folder["name"].replace("_", " "),
            }
        )
        return
    print("スキップ理由: 有効なincoming作品フォルダがありません")
    write_github_output({"found": "false"})


def move(args: argparse.Namespace) -> None:
    if not args.folder_id:
        raise RuntimeError("--folder-id is required for move")
    service = get_drive_service()
    root = resolve_root_folder(service, args.root_folder, args.root_folder_id)
    destination = ensure_child_folder(service, root["id"], args.destination)
    file_record = (
        service.files()
        .get(fileId=args.folder_id, fields="id,name,parents", supportsAllDrives=True)
        .execute()
    )
    previous_parents = ",".join(file_record.get("parents", []))
    body = {
        "description": f"TokyoChillMatic automation moved to {args.destination} at {datetime.now(timezone.utc).isoformat()}"
    }
    service.files().update(
        fileId=args.folder_id,
        addParents=destination["id"],
        removeParents=previous_parents,
        body=body,
        fields="id,name,parents",
        supportsAllDrives=True,
    ).execute()
    print(f"Moved {file_record['name']} to {args.destination}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("detect", "move"))
    parser.add_argument("--root-folder", default=ROOT_FOLDER)
    parser.add_argument(
        "--root-folder-id",
        default=os.environ.get(ROOT_FOLDER_ID_ENV),
        help=f"DriveルートフォルダID（{ROOT_FOLDER_ID_ENV} が指定されていればID優先）",
    )
    parser.add_argument("--incoming-folder", default="incoming")
    parser.add_argument("--processed-folder", default="processed")
    parser.add_argument("--failed-folder", default="failed")
    parser.add_argument("--folder-id")
    parser.add_argument("--destination", choices=("processed", "failed"))
    args = parser.parse_args()
    if args.command == "detect":
        detect(args)
    else:
        if not args.destination:
            raise RuntimeError("--destination is required for move")
        move(args)


if __name__ == "__main__":
    main()
