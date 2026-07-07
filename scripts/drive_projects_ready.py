#!/usr/bin/env python3
"""Stage complete Google Drive Projects assets into incoming for processing."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

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
VIDEO_MIME_PREFIX = "video/"
MP4_MIME_TYPES = {"video/mp4", "application/octet-stream"}
VIDEO_MIME_TYPES = {"video/mp4", "video/quicktime"}
VIDEO_EXTENSIONS = (".mp4", ".mov")
BACKGROUND_LOOP_MOV_NAME = "background_loop.mov"
BACKGROUND_LOOP_NAME = "background_loop.mp4"
PROJECT_NAMES_FILE = Path(__file__).resolve().parents[1] / "project_names.txt"
PROJECTS_BATCH_MARKER_PREFIX = "projects_batch_"


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


def is_projects_root_background(item: dict) -> bool:
    name = normalized_drive_name(item)
    mime_type = item.get("mimeType", "")
    return (
        name == "background.jpg"
        and (mime_type.startswith("image/") or mime_type == "application/octet-stream")
    ) or (
        name == "background.mp4"
        and (mime_type in MP4_MIME_TYPES or mime_type.startswith(VIDEO_MIME_PREFIX))
    )


def is_mp3(item: dict) -> bool:
    return normalized_drive_name(item).endswith(".mp3")


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


def direct_children_query(parent_id: str) -> str:
    return f"'{quote_drive_query(parent_id)}' in parents and trashed = false"


def direct_project_files(service, projects_id: str) -> list[dict]:
    return [
        item
        for item in list_files(
            service,
            direct_children_query(projects_id),
            fields="files(id,name,mimeType,createdTime,modifiedTime,shortcutDetails)",
        )
        if item.get("mimeType") != FOLDER_MIME
    ]


def inspect_projects_root_assets(
    children: list[dict],
) -> tuple[bool, str, list[dict], dict | None]:
    mp3s = [item for item in children if is_mp3(item)]
    backgrounds = [item for item in children if is_projects_root_background(item)]
    print(f"INSPECT: Projects直下 - Google Drive files: {describe_children(children)}")
    if len(backgrounds) < REQUIRED_BACKGROUND_COUNT:
        return (
            False,
            "Projects直下に background.jpg または background.mp4 が必要です",
            mp3s,
            None,
        )
    if len(backgrounds) > REQUIRED_BACKGROUND_COUNT:
        return (
            False,
            f"Projects直下の背景素材が複数あります（検出数: {len(backgrounds)}）",
            mp3s,
            None,
        )
    if len(mp3s) < REQUIRED_MP3_COUNT:
        return (
            False,
            f"Projects直下のmp3音源が不足しています（検出数: {len(mp3s)} / {REQUIRED_MP3_COUNT}）",
            mp3s,
            backgrounds[0],
        )
    if len(mp3s) > REQUIRED_MP3_COUNT:
        return (
            False,
            f"Projects直下のmp3音源が多すぎます（検出数: {len(mp3s)} / {REQUIRED_MP3_COUNT}）",
            mp3s,
            backgrounds[0],
        )
    return True, "Projects直下の素材OK（mp3 20曲、背景素材1つ）", mp3s, backgrounds[0]


def project_batch_marker_name(mp3s: list[dict], background: dict) -> str:
    source_ids = sorted(item["id"] for item in [*mp3s, background])
    digest = hashlib.sha256("\n".join(source_ids).encode("utf-8")).hexdigest()[:16]
    return f"{PROJECTS_BATCH_MARKER_PREFIX}{digest}"


def read_project_names(path: Path = PROJECT_NAMES_FILE) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def select_unused_project_name(
    service, names: list[str], parent_ids: list[str]
) -> str | None:
    for name in names:
        if not any(folder_exists(service, parent_id, name) for parent_id in parent_ids):
            return name
    return None


def download_file_to_path(service, file_id: str, destination: Path) -> None:
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    with destination.open("wb") as handle:
        downloader = MediaIoBaseDownload(handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def upload_file_from_path(
    service, source_path: Path, destination_folder_id: str, name: str, mime_type: str
) -> None:
    media = MediaFileUpload(str(source_path), mimetype=mime_type or None, resumable=True)
    service.files().create(
        body={"name": name, "parents": [destination_folder_id]},
        media_body=media,
        fields="id,name,parents",
        supportsAllDrives=True,
    ).execute()


def transfer_file_via_download_upload(
    service, item: dict, destination_folder_id: str, name: str, dry_run: bool
) -> None:
    if dry_run:
        print(f"DRY RUN: download/upload {item['id']} -> {name}")
        return
    suffix = Path(name).suffix or Path(item.get("name", "")).suffix
    with tempfile.TemporaryDirectory(prefix="drive-projects-") as temp_dir:
        temp_path = Path(temp_dir) / f"source{suffix}"
        download_file_to_path(service, item["id"], temp_path)
        upload_file_from_path(
            service, temp_path, destination_folder_id, name, item.get("mimeType", "")
        )


def create_marker_folder(
    service, processed_id: str, marker_name: str, dry_run: bool
) -> None:
    if dry_run:
        print(f"DRY RUN: create processed marker {marker_name}")
        return
    service.files().create(
        body={
            "name": marker_name,
            "mimeType": FOLDER_MIME,
            "parents": [processed_id],
            "description": "TokyoChillMatic Projects root batch copied to incoming "
            f"at {datetime.now(timezone.utc).isoformat()}",
        },
        fields="id,name",
        supportsAllDrives=True,
    ).execute()


def copy_projects_root_batch(
    service,
    incoming_id: str,
    processed_id: str,
    project_name: str,
    mp3s: list[dict],
    background: dict,
    marker_name: str,
    dry_run: bool,
) -> None:
    if dry_run:
        work_folder = {"id": f"dry-run-{project_name}", "name": project_name}
        print(f"DRY RUN: create incoming/{project_name}")
    else:
        work_folder = ensure_child_folder(service, incoming_id, project_name)
    for index, item in enumerate(
        sorted(mp3s, key=lambda entry: normalized_drive_name(entry)), start=1
    ):
        transfer_file_via_download_upload(
            service, item, work_folder["id"], f"track{index:02d}.mp3", dry_run
        )
    background_name = (
        "background.mp4"
        if normalized_drive_name(background).endswith(".mp4")
        else "background.jpg"
    )
    transfer_file_via_download_upload(
        service, background, work_folder["id"], background_name, dry_run
    )
    create_marker_folder(service, processed_id, marker_name, dry_run)
    print(f"COPIED: Projects直下素材 -> incoming/{project_name}")


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
    completed = ensure_child_folder(service, root["id"], args.completed_folder)
    failed = ensure_child_folder(service, root["id"], args.failed_folder)

    direct_files = direct_project_files(service, projects["id"])
    ok, reason, mp3s, background = inspect_projects_root_assets(direct_files)
    copied_count = 0
    skipped_count = 0
    if ok and background:
        marker_name = project_batch_marker_name(mp3s, background)
        if folder_exists(service, processed["id"], marker_name):
            skipped_count += 1
            print(
                f"SKIP: Projects直下素材 - processed marker {marker_name} があるため二重処理防止"
            )
        else:
            project_name = select_unused_project_name(
                service,
                read_project_names(),
                [incoming["id"], completed["id"], processed["id"], failed["id"]],
            )
            if not project_name:
                skipped_count += 1
                print("SKIP: project_names.txt に未使用の作品名がありません")
            else:
                print(f"READY: {project_name} - {reason}")
                copy_projects_root_batch(
                    service,
                    incoming["id"],
                    processed["id"],
                    project_name,
                    mp3s,
                    background,
                    marker_name,
                    args.dry_run,
                )
                copied_count += 1
    else:
        skipped_count += 1
        print(f"SKIP: Projects直下素材 - {reason}")

    project_folders = list_files(service, child_folders_query(projects["id"]))
    moved_count = 0
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
            ("completed", completed["id"]),
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
        f"Summary: copied={copied_count}, moved={moved_count}, skipped={skipped_count}, inspected_folders={len(project_folders)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage complete Projects root assets into incoming."
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
    parser.add_argument("--completed-folder", default="completed")
    parser.add_argument("--failed-folder", default="failed")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    check_projects(args)


if __name__ == "__main__":
    main()
