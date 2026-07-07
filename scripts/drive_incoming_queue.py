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
BACKGROUND_MP4_NAME = "background.mp4"
VIDEO_MIME_PREFIX = "video/"
MP4_MIME_TYPES = {"video/mp4", "application/octet-stream"}
VIDEO_MIME_TYPES = {"video/mp4", "video/quicktime"}
VIDEO_EXTENSIONS = (".mp4", ".mov")
BACKGROUND_LOOP_MOV_NAME = "background_loop.mov"
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


def is_video_file(item: dict) -> bool:
    name = normalized_drive_name(item)
    mime_type = item.get("mimeType", "")
    return (
        name.endswith(VIDEO_EXTENSIONS)
        or mime_type in VIDEO_MIME_TYPES
        or mime_type.startswith(VIDEO_MIME_PREFIX)
    )


def select_background_loop_file(items: list[dict]) -> tuple[dict | None, list[dict]]:
    videos = [item for item in items if is_video_file(item)]
    exact_mp4 = [
        item
        for item in videos
        if normalized_drive_name(item) in {BACKGROUND_MP4_NAME, BACKGROUND_LOOP_NAME}
    ]
    if exact_mp4:
        return exact_mp4[0], videos
    exact_mov = [
        item
        for item in videos
        if normalized_drive_name(item) == BACKGROUND_LOOP_MOV_NAME
    ]
    if exact_mov:
        return exact_mov[0], videos
    if len(videos) == 1:
        return videos[0], videos
    return None, videos


def is_background_loop(item: dict) -> bool:
    selected, _ = select_background_loop_file([item])
    return selected is item


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


def describe_drive_item(item: dict) -> str:
    return (
        f"name={item.get('name', '<no name>')} "
        f"id={item.get('id', '<no id>')} "
        f"mimeType={item.get('mimeType', '<no mime>')}"
    )


def describe_children(children: list[dict]) -> str:
    if not children:
        return "取得アイテムなし"
    return ", ".join(
        f"{item.get('name', '<no name>')} [{item.get('mimeType', '<no mime>')}]"
        for item in children
    )


def log_incoming_items(incoming: dict, items: list[dict]) -> None:
    print(f"incoming folder id: {incoming['id']}")
    print(f"incomingフォルダ: name={incoming['name']} id={incoming['id']}")
    print(f"incoming内で取得できた全item一覧: count={len(items)}")
    if not items:
        print("incoming内で取得できた全item一覧: 取得アイテムなし")
        return
    for index, item in enumerate(items, start=1):
        print(f"incoming item[{index}]: {describe_drive_item(item)}")


def log_incoming_work_folders(incoming: dict, work_folders: list[dict]) -> None:
    print(f"incoming folder id: {incoming['id']}")
    print(f"incomingフォルダ: name={incoming['name']} id={incoming['id']}")
    print(f"フォルダ候補一覧: count={len(work_folders)}")
    print(f"incoming直下のフォルダ一覧: count={len(work_folders)}")
    if not work_folders:
        print("フォルダ候補一覧: 取得フォルダなし")
        print("incoming直下のフォルダ一覧: 取得フォルダなし")
        return
    for index, folder in enumerate(work_folders, start=1):
        description = describe_drive_item(folder)
        print(f"フォルダ候補[{index}]: {description}")
        print(f"incoming直下フォルダ[{index}]: {description}")



def folder_exists(service, parent_id: str, name: str) -> bool:
    query = (
        f"mimeType = '{FOLDER_MIME}' and name = '{quote_drive_query(name)}' "
        f"and '{quote_drive_query(parent_id)}' in parents and trashed = false"
    )
    return bool(list_files(service, query, fields="files(id,name)"))

def ensure_child_folder(service, parent_id: str, name: str) -> dict:
    query = f"mimeType = '{FOLDER_MIME}' and name = '{quote_drive_query(name)}' and '{quote_drive_query(parent_id)}' in parents and trashed = false"
    folders = list_files(service, query, fields="files(id,name)")
    if folders:
        return folders[0]
    raise FileNotFoundError(
        f"必須Driveフォルダが見つかりません: {name}。Drive上に新規フォルダは作成しません"
    )


def validate_work_folder(
    service, folder: dict, *, require_exactly_20_tracks: bool = False
) -> tuple[bool, str, int]:
    folder_id = folder["id"]
    children = list_files(
        service,
        f"'{quote_drive_query(folder_id)}' in parents and trashed = false",
        fields="files(id,name,mimeType,shortcutDetails)",
    )
    child_folders = [item for item in children if is_folder(item)]
    child_files = [item for item in children if not is_folder(item)]
    background_loop, video_files = select_background_loop_file(children)
    background_loops = [background_loop] if background_loop else []
    backgrounds = [item for item in children if is_background_image(item)]
    mp3s = [item for item in children if is_mp3(item)]

    print(f"対象フォルダ: name={folder.get('name', '<no name>')} id={folder_id}")
    print(
        f"各フォルダ内のファイル一覧: folder={folder.get('name', '<no name>')} id={folder_id} count={len(children)}"
    )
    if children:
        for index, child in enumerate(children, start=1):
            print(f"  file[{index}]: {describe_drive_item(child)}")
    else:
        print("  取得アイテムなし")
    print(f"検出したファイル数: {len(child_files)}")
    print(f"検出したフォルダ数: {len(child_folders)}")
    print(f"background検出数: {len(background_loops) + len(backgrounds)}")
    print(f"track検出数: {len(mp3s)}")
    print(
        "判定内訳: "
        f"background_loop.mp4={len(background_loops)}, "
        f"background画像={len(backgrounds)}, "
        f"mp3={len(mp3s)}"
    )
    print(f"background_loop.mp4 があるか: {'yes' if background_loops else 'no'}")
    print(f"mp3 が何個あるか: {len(mp3s)}")
    print(f"検出アイテム: {describe_children(children)}")

    if not background_loop and len(video_files) > 1:
        print(
            f"無効判定の理由: 背景動画候補が複数あります（検出数: {len(video_files)}）。background_loop.mp4 または background_loop.mov を使ってください"
        )
        return (
            False,
            f"背景動画候補が複数あります（検出数: {len(video_files)}）。background_loop.mp4 または background_loop.mov を使ってください",
            len(mp3s),
        )
    if len(backgrounds) > 1:
        print(
            f"無効判定の理由: background画像は1枚だけ必要です（検出数: {len(backgrounds)}）"
        )
        return (
            False,
            f"background画像は1枚だけ必要です（検出数: {len(backgrounds)}）",
            len(mp3s),
        )
    if not background_loops and not backgrounds:
        print("無効判定の理由: background_loop.mp4 または background.png が必要です")
        return False, "background_loop.mp4 または background.png が必要です", len(mp3s)
    if require_exactly_20_tracks and len(mp3s) != 20:
        print(f"無効判定の理由: mp3音源は20曲ちょうど必要です（検出数: {len(mp3s)} / 20）")
        return (
            False,
            f"mp3音源は20曲ちょうど必要です（検出数: {len(mp3s)} / 20）",
            len(mp3s),
        )
    if len(mp3s) < 1:
        print("無効判定の理由: mp3音源がありません（理想は20曲）")
        return False, "mp3音源がありません（理想は20曲）", 0
    if len(mp3s) < 20:
        print(
            f"有効判定の理由: mp3音源は{len(mp3s)}曲です（理想は20曲）。不足分は生成前に複製して互換性を保ちます。"
        )
        return (
            True,
            f"mp3音源は{len(mp3s)}曲です（理想は20曲）。不足分は生成前に複製して互換性を保ちます。",
            len(mp3s),
        )
    print("有効判定の理由: 素材OK")
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


def list_incoming_items(service, incoming: dict) -> list[dict]:
    """Return every non-trashed item directly under incoming."""
    incoming_items_query = (
        f"'{quote_drive_query(incoming['id'])}' in parents and trashed = false"
    )
    return list_files(
        service,
        incoming_items_query,
        fields="files(id,name,mimeType,createdTime,modifiedTime,parents,shortcutDetails)",
    )


def list_incoming_work_folders(
    service, incoming: dict
) -> tuple[list[dict], list[dict]]:
    """Return all direct incoming items and direct child folders as work candidates."""
    incoming_items = list_incoming_items(service, incoming)
    return incoming_items, [item for item in incoming_items if is_folder(item)]


def detect(args: argparse.Namespace) -> None:
    service = get_drive_service()
    root = resolve_root_folder(service, args.root_folder, args.root_folder_id)
    completed = ensure_child_folder(service, root["id"], args.completed_folder)
    ensure_child_folder(service, root["id"], args.failed_folder)
    projects = find_single_folder(service, args.projects_folder, root["id"])
    project_items = list_files(
        service,
        f"'{quote_drive_query(projects['id'])}' in parents and trashed = false",
        fields="files(id,name,mimeType,createdTime,modifiedTime,parents,shortcutDetails)",
    )
    project_folders = [item for item in project_items if is_folder(item)]
    print(f"Projects folder id: {projects['id']}")
    print(f"Projects内の作品フォルダ数: {len(project_folders)}")
    for item in project_items:
        if not is_folder(item):
            print(f"Projects直下ファイルは読み取り専用扱いでスキップ: {describe_drive_item(item)}")
    found_false_reasons: list[str] = []
    work_folders = project_folders
    if not work_folders:
        reason = "Projects内に作品フォルダがありません"
        found_false_reasons.append(reason)
        print(f"スキップ理由: {reason}")
    for folder in work_folders:
        if folder_exists(service, completed["id"], folder["name"]):
            reason = f"{folder['name']} - completed に同名フォルダがあるためスキップ"
            found_false_reasons.append(reason)
            print(f"スキップ理由: {reason}")
            continue
        ok, message, track_count = validate_work_folder(
            service, folder, require_exactly_20_tracks=True
        )
        if not ok:
            reason = f"{folder['name']} - {message}"
            found_false_reasons.append(reason)
            print(f"スキップ理由: {reason}")
            continue
        print(f"処理対象: {folder['name']} - {message}")
        print(f"最終的に選ばれた folder id: {folder['id']}")
        stem = safe_file_stem(folder["name"])
        write_github_output(
            {
                "found": "true",
                "work_folder_id": folder["id"],
                "work_folder_name": folder["name"],
                "track_count": str(track_count),
                "output_file": f"{stem}.mp4",
                "youtube_title": folder["name"].replace("_", " "),
                "source_queue": "projects",
            }
        )
        return
    if not found_false_reasons:
        found_false_reasons.append("有効なincoming作品フォルダがありません")
    print("found=false の理由:")
    for index, reason in enumerate(found_false_reasons, start=1):
        print(f"  {index}. {reason}")
    print("スキップ理由: 有効なincoming作品フォルダがありません")
    print("最終的に選ばれた folder id: <none>")
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
    parser.add_argument("--projects-folder", default="Projects")
    parser.add_argument("--incoming-folder", default="incoming")
    parser.add_argument("--completed-folder", default="completed")
    parser.add_argument("--failed-folder", default="failed")
    parser.add_argument("--folder-id")
    parser.add_argument("--destination", choices=("completed", "failed"))
    args = parser.parse_args()
    if args.command == "detect":
        detect(args)
    else:
        if not args.destination:
            raise RuntimeError("--destination is required for move")
        move(args)


if __name__ == "__main__":
    main()
