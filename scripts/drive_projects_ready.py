#!/usr/bin/env python3
"""Move complete Google Drive Projects folders into incoming for processing."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

from drive_incoming_queue import (
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
        fields="files(id,name,mimeType)",
    )
    backgrounds = [
        item
        for item in children
        if item["name"].lower().startswith("background.") and item["name"].lower().endswith(IMAGE_EXTENSIONS)
    ]
    mp3s = [item for item in children if item["name"].lower().endswith(".mp3")]

    if len(backgrounds) == 0:
        return False, "background.* 画像がありません"
    if len(backgrounds) > REQUIRED_BACKGROUND_COUNT:
        return False, f"background.* 画像が複数あります（検出数: {len(backgrounds)}）"
    if len(mp3s) < REQUIRED_MP3_COUNT:
        return False, f"mp3音源が不足しています（検出数: {len(mp3s)} / {REQUIRED_MP3_COUNT}）"
    if len(mp3s) > REQUIRED_MP3_COUNT:
        return False, f"mp3音源が多すぎます（検出数: {len(mp3s)} / {REQUIRED_MP3_COUNT}）"
    return True, "素材OK（background.* 1枚、mp3 20曲）"


def move_folder(service, folder: dict, destination_id: str, dry_run: bool) -> None:
    if dry_run:
        print(f"DRY RUN: move {folder['name']} to incoming")
        return

    file_record = service.files().get(fileId=folder["id"], fields="id,name,parents", supportsAllDrives=True).execute()
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
        for label, parent_id in (("incoming", incoming["id"]), ("processed", processed["id"]), ("failed", failed["id"])):
            if folder_exists(service, parent_id, name):
                duplicate_parent = label
                break
        if duplicate_parent:
            skipped_count += 1
            print(f"SKIP: {name} - {duplicate_parent} に同名フォルダがあるため二重処理防止")
            continue

        print(f"READY: {name} - {reason}")
        move_folder(service, folder, incoming["id"], args.dry_run)
        moved_count += 1

    print(f"Summary: moved={moved_count}, skipped={skipped_count}, inspected={len(project_folders)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Move complete Projects folders into incoming.")
    parser.add_argument("--root-folder", default=ROOT_FOLDER)
    parser.add_argument("--root-folder-id", default=os.environ.get(ROOT_FOLDER_ID_ENV), help=f"DriveルートフォルダID（{ROOT_FOLDER_ID_ENV} が指定されていればID優先）")
    parser.add_argument("--projects-folder", default="Projects")
    parser.add_argument("--incoming-folder", default="incoming")
    parser.add_argument("--processed-folder", default="processed")
    parser.add_argument("--failed-folder", default="failed")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    check_projects(args)


if __name__ == "__main__":
    main()
