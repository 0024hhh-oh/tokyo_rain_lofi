#!/usr/bin/env python3
"""Generate and upload Tokyo ChillMatic thumbnails for Drive Projects/day and night."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
FOLDER_MIME = "application/vnd.google-apps.folder"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
IGNORED_IMAGE_MARKERS = ("logo", "overlay", "mask")
THUMBNAIL_NAME = "thumbnail.jpg"
ROOT_FOLDER = "Tokyo ChillMatic FM"
ROOT_FOLDER_ID_ENV = "TOKYO_CHILLMATIC_DRIVE_FOLDER_ID"
DEFAULT_NIGHT_LOGO = Path("assets/thumbnail/logo-night.jpg")
DEFAULT_DAY_LOGO = Path("assets/thumbnail/logo-day.jpg")


def normalized_name(item: dict) -> str:
    return item.get("name", "").strip().casefold()


def item_size(item: dict) -> int:
    try:
        return int(item.get("size") or 0)
    except (TypeError, ValueError):
        return 0


def is_image(item: dict) -> bool:
    name = normalized_name(item)
    suffix = Path(name).suffix
    mime = item.get("mimeType", "")
    return suffix in IMAGE_EXTENSIONS or mime.startswith("image/")


def is_video(item: dict) -> bool:
    name = normalized_name(item)
    suffix = Path(name).suffix
    mime = item.get("mimeType", "")
    return suffix in VIDEO_EXTENSIONS or mime.startswith("video/")


def select_thumbnail_source(items: list[dict]) -> dict | None:
    """Prefer an explicit source, then the largest safe image, then a video."""
    images = [
        item
        for item in items
        if is_image(item)
        and normalized_name(item) != THUMBNAIL_NAME
        and not any(
            marker in Path(normalized_name(item)).stem
            for marker in IGNORED_IMAGE_MARKERS
        )
    ]
    explicit = [
        item
        for item in images
        if Path(normalized_name(item)).stem == "thumbnail_source"
    ]
    if explicit:
        return sorted(explicit, key=lambda item: normalized_name(item))[0]
    if images:
        return sorted(
            images,
            key=lambda item: (-item_size(item), normalized_name(item)),
        )[0]

    videos = [item for item in items if is_video(item)]
    priorities = ("background.mp4", "background_loop.mp4", "background_loop.mov")
    for name in priorities:
        match = [item for item in videos if normalized_name(item) == name]
        if match:
            return match[0]
    return sorted(videos, key=lambda item: normalized_name(item))[0] if videos else None


def build_ffmpeg_command(
    *,
    ffmpeg: str,
    source: Path,
    logo: Path,
    output: Path,
    frame_second: float = 1.0,
) -> list[str]:
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    if source.suffix.casefold() in VIDEO_EXTENSIONS:
        command += ["-ss", str(frame_second)]
    command += [
        "-i",
        str(source),
        "-i",
        str(logo),
        "-filter_complex",
        (
            "[0:v]scale=1280:720:force_original_aspect_ratio=increase,"
            "crop=1280:720[bg];"
            "[1:v]scale=435:-1,format=rgba,"
            "colorkey=0x080808:0.24:0.10[logo];"
            "[bg][logo]overlay=77:(H-h)/2:format=auto[v]"
        ),
        "-map",
        "[v]",
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(output),
    ]
    return command


def get_drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    info_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    info_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_PATH")
    if info_json:
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(info_json), scopes=[DRIVE_SCOPE]
        )
    elif info_path:
        credentials = service_account.Credentials.from_service_account_file(
            info_path, scopes=[DRIVE_SCOPE]
        )
    else:
        raise RuntimeError("Google Drive service-account credentials are not configured")
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def quote_query(value: str) -> str:
    return value.replace("'", "\\'")


def list_children(service, parent_id: str) -> list[dict]:
    items: list[dict] = []
    page_token = None
    while True:
        response = (
            service.files()
            .list(
                q=f"'{quote_query(parent_id)}' in parents and trashed = false",
                fields="nextPageToken,files(id,name,mimeType,size,parents)",
                pageSize=100,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                orderBy="name",
            )
            .execute()
        )
        items.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return items


def find_folder(service, name: str, parent_id: str | None = None) -> dict:
    query = (
        f"mimeType = '{FOLDER_MIME}' and name = '{quote_query(name)}' "
        "and trashed = false"
    )
    if parent_id:
        query += f" and '{quote_query(parent_id)}' in parents"
    response = (
        service.files()
        .list(
            q=query,
            fields="files(id,name,mimeType)",
            pageSize=10,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    folders = response.get("files", [])
    if len(folders) != 1:
        raise RuntimeError(f"Drive folder {name!r} count is {len(folders)}, expected 1")
    return folders[0]


def resolve_root(service, root_id: str | None) -> dict:
    if root_id:
        return (
            service.files()
            .get(fileId=root_id, fields="id,name,mimeType", supportsAllDrives=True)
            .execute()
        )
    return find_folder(service, ROOT_FOLDER)


def download_file(service, file_id: str, destination: Path) -> None:
    from googleapiclient.http import MediaIoBaseDownload

    destination.parent.mkdir(parents=True, exist_ok=True)
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    with destination.open("wb") as handle:
        downloader = MediaIoBaseDownload(handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def upload_thumbnail(
    service, *, folder_id: str, existing_id: str | None, thumbnail: Path
) -> dict:
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(str(thumbnail), mimetype="image/jpeg", resumable=False)
    if existing_id:
        return (
            service.files()
            .update(
                fileId=existing_id,
                media_body=media,
                fields="id,name,size",
                supportsAllDrives=True,
            )
            .execute()
        )
    return (
        service.files()
        .create(
            body={"name": THUMBNAIL_NAME, "parents": [folder_id]},
            media_body=media,
            fields="id,name,size",
            supportsAllDrives=True,
        )
        .execute()
    )


def safe_stem(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-") or "project"


def process_project(
    service,
    *,
    mode: str,
    project: dict,
    args: argparse.Namespace,
) -> str:
    items = list_children(service, project["id"])
    existing = next(
        (item for item in items if normalized_name(item) == THUMBNAIL_NAME), None
    )
    if existing and not args.force:
        print(f"SKIP Projects/{mode}/{project['name']}: thumbnail.jpg already exists")
        return "skipped"
    source = select_thumbnail_source(items)
    if not source:
        print(f"SKIP Projects/{mode}/{project['name']}: no image or video")
        return "skipped"
    print(
        f"SOURCE Projects/{mode}/{project['name']}: "
        f"{source['name']} ({source.get('mimeType', '')})"
    )
    if args.dry_run:
        return "planned"

    logo = args.night_logo if mode == "night" else args.day_logo
    if not logo.is_file():
        raise FileNotFoundError(f"Logo not found: {logo}")
    with tempfile.TemporaryDirectory(prefix="thumbnail-") as directory:
        work = Path(directory)
        suffix = Path(normalized_name(source)).suffix or ".bin"
        local_source = work / f"source{suffix}"
        local_output = work / THUMBNAIL_NAME
        download_file(service, source["id"], local_source)
        command = build_ffmpeg_command(
            ffmpeg=args.ffmpeg,
            source=local_source,
            logo=logo,
            output=local_output,
            frame_second=args.frame_second,
        )
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0 or not local_output.is_file():
            raise RuntimeError(
                "FFmpeg failed: "
                + (completed.stderr.strip() or f"exit {completed.returncode}")
            )
        uploaded = upload_thumbnail(
            service,
            folder_id=project["id"],
            existing_id=existing["id"] if existing else None,
            thumbnail=local_output,
        )
        if args.preview_dir:
            args.preview_dir.mkdir(parents=True, exist_ok=True)
            preview = args.preview_dir / f"{mode}-{safe_stem(project['name'])}.jpg"
            preview.write_bytes(local_output.read_bytes())
        print(
            f"DONE Projects/{mode}/{project['name']}: "
            f"thumbnail_id={uploaded.get('id', '<unknown>')}"
        )
    return "generated"


def process(args: argparse.Namespace) -> int:
    service = get_drive_service()
    root = resolve_root(service, args.root_folder_id)
    projects = find_folder(service, "Projects", root["id"])
    modes = ("day", "night") if args.mode == "all" else (args.mode,)
    generated = skipped = failed = 0
    for mode in modes:
        mode_folder = find_folder(service, mode, projects["id"])
        project_folders = [
            item for item in list_children(service, mode_folder["id"])
            if item.get("mimeType") == FOLDER_MIME
        ]
        for project in project_folders:
            try:
                result = process_project(
                    service, mode=mode, project=project, args=args
                )
                if result == "generated":
                    generated += 1
                else:
                    skipped += 1
            except Exception as exc:  # keep other project folders moving
                failed += 1
                print(f"ERROR Projects/{mode}/{project['name']}: {exc}")
    print(f"SUMMARY generated={generated} skipped={skipped} failed={failed}")
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("all", "day", "night"), default="all")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ffmpeg", default=os.getenv("FFMPEG_BIN", "ffmpeg"))
    parser.add_argument("--frame-second", type=float, default=1.0)
    parser.add_argument("--night-logo", type=Path, default=DEFAULT_NIGHT_LOGO)
    parser.add_argument("--day-logo", type=Path, default=DEFAULT_DAY_LOGO)
    parser.add_argument("--preview-dir", type=Path)
    parser.add_argument(
        "--root-folder-id", default=os.getenv(ROOT_FOLDER_ID_ENV)
    )
    return parser


def main() -> int:
    return process(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
