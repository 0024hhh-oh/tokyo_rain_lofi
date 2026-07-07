#!/usr/bin/env python3
"""Move complete Google Drive Projects folders into incoming for processing."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

from drive_incoming_queue import (
    BACKGROUND_LOOP_NAME,
    FOLDER_MIME,
    IMAGE_EXTENSIONS,
    ROOT_FOLDER,
    ROOT_FOLDER_ID_ENV,
    ensure_child_folder,
    find_single_folder,
    get_drive_service,
    resolve_root_folder,
    list_files,
    quote_drive_query,
)

REQUIRED_BACKGROUND_COUNT = 1
REQUIRED_MP3_COUNT = 20
VIDEO_MIME_PREFIX = "video/"
MP4_MIME_TYPES = {"video/mp4", "application/octet-stream"}
VIDEO_MIME_TYPES = {"video/mp4", "video/quicktime"}
VIDEO_EXTENSIONS = (".mp4", ".mov")
BACKGROUND_LOOP_MOV_NAME = "background_loop.mov"


def normalized_drive_name(item: dict) -> str:
    return item.get("name", "").strip().casefold()


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
        item for item in videos if normalized_drive_name(item) == BACKGROUND_LOOP_NAME
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
        and (mime_type.startswith("image/") or mime_type == "application/octet-stream")
    )


def describe_children(children: list[dict]) -> str:
    if not children:
        return "取得ファイルなし"
    return ", ".join(
        f"{item.get('name', '<no name>')} [{item.get('mimeType', '<no mime>')}]"
        for item in children
    )


def child_folders_query(parent_id: str) -> str:
    return f"mimeType = '{FOLDER_MIME}' and '{quote_drive_query(parent_id)}' in parents and trashed = false"


def folder_exists(service, parent_id: str, name: str) -> bool:
    query = (
        f"mimeType = '{FOLDER_MIME}' and name = '{quote_drive_query(name)}' "
        f"and '{quote_drive_query(parent_id)}' in parents and trashed = false"
    )
    return bool(list_files(service, query, fields="files(id,name)"))


def inspect_project_folder(service, folder: dict) -> tuple[bool, str]:
    children = list_files(
        service,
        f"'{quote_drive_query(folder['id'])}' in parents and trashed = false",
        fields="files(id,name,mimeType,shortcutDetails)",
    )
    background_loop, video_files = select_background_loop_file(children)
    background_loops = [background_loop] if background_loop else []
    backgrounds = [item for item in children if is_background_image(item)]
    mp3s = [item for item in children if normalized_drive_name(item).endswith(".mp3")]
    print(
        f"INSPECT: {folder['name']} - Google Drive files: {describe_children(children)}"
    )

    if not background_loop and len(video_files) > REQUIRED_BACKGROUND_COUNT:
        return (
            False,
            f"背景動画候補が複数あります（検出数: {len(video_files)}）。background_loop.mp4 または background_loop.mov を使ってください",
        )
    if len(backgrounds) > REQUIRED_BACKGROUND_COUNT:
        return False, f"background.* 画像が複数あります（検出数: {len(backgrounds)}）"
    if len(background_loops) == 0 and len(backgrounds) == 0:
        return (
            False,
            f"background_loop.mp4 または background.png が必要です（取得一覧: {describe_children(children)}）",
        )
    if len(mp3s) < REQUIRED_MP3_COUNT:
        return (
            False,
            f"mp3音源が不足しています（検出数: {len(mp3s)} / {REQUIRED_MP3_COUNT}）",
        )
    if len(mp3s) > REQUIRED_MP3_COUNT:
        return (
            False,
            f"mp3音源が多すぎます（検出数: {len(mp3s)} / {REQUIRED_MP3_COUNT}）",
        )
    if background_loops:
        return True, "素材OK（background_loop.mp4優先、mp3 20曲）"
    return True, "素材OK（background.*、mp3 20曲）"


def move_folder(service, folder: dict, destination_id: str, dry_run: bool) -> None:
    if dry_run:
        print(f"DRY RUN: move {folder['name']} to incoming")
        return

    file_record = (
        service.files()
        .get(fileId=folder["id"], fields="id,name,parents", supportsAllDrives=True)
        .execute()
    )
    previous_parents = ",".join(file_record.get("parents", []))
    body = {
        "description": "TokyoChillMatic Projects automation moved to incoming "
        f"at {datetime.now(timezone.utc).isoformat()}"
    }
    service.files().update(
        fileId=folder["id"],
        addParents=destination_id,
        removeParents=previous_parents,
        body=body,
        fields="id,name,parents",
        supportsAllDrives=True,
    ).execute()
    print(f"MOVED: {folder['name']} -> incoming")


def check_projects(args: argparse.Namespace) -> None:
    service = get_drive_service()
    root = resolve_root_folder(service, args.root_folder, args.root_folder_id)
    projects = find_single_folder(service, args.projects_folder, root["id"])
    incoming = ensure_child_folder(service, root["id"], args.incoming_folder)
    processed = ensure_child_folder(service, root["id"], args.processed_folder)
    failed = ensure_child_folder(service, root["id"], args.failed_folder)

    project_folders = list_files(service, child_folders_query(projects["id"]))
    if not project_folders:
        print(f"Projects folder is empty: {args.root_folder}/{args.projects_folder}")
        return

    moved_count = 0
    skipped_count = 0
    for folder in project_folders:
        name = folder["name"]
        ok, reason = inspect_project_folder(service, folder)
        if not ok:
            skipped_count += 1
            print(f"SKIP: {name} - {reason}")
            continue

        duplicate_parent = None
        for label, parent_id in (
            ("incoming", incoming["id"]),
            ("processed", processed["id"]),
            ("failed", failed["id"]),
        ):
            if folder_exists(service, parent_id, name):
                duplicate_parent = label
                break
        if duplicate_parent:
            skipped_count += 1
            print(
                f"SKIP: {name} - {duplicate_parent} に同名フォルダがあるため二重処理防止"
            )
            continue

        print(f"READY: {name} - {reason}")
        move_folder(service, folder, incoming["id"], args.dry_run)
        moved_count += 1

    print(
        f"Summary: moved={moved_count}, skipped={skipped_count}, inspected={len(project_folders)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Move complete Projects folders into incoming."
    )
    parser.add_argument("--root-folder", default=ROOT_FOLDER)
    parser.add_argument(
        "--root-folder-id",
        default=os.environ.get(ROOT_FOLDER_ID_ENV),
        help=f"DriveルートフォルダID（{ROOT_FOLDER_ID_ENV} が指定されていればID優先）",
    )
    parser.add_argument("--projects-folder", default="Projects")
    parser.add_argument("--incoming-folder", default="incoming")
    parser.add_argument("--processed-folder", default="processed")
    parser.add_argument("--failed-folder", default="failed")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    check_projects(args)


if __name__ == "__main__":
    main()
