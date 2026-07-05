#!/usr/bin/env python3
"""Download Tokyo ChillMatic FM video assets from Google Drive for GitHub Actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg"}
BACKGROUND_IMAGE_NAMES = {
    "background.png",
    "background.jpg",
    "background.jpeg",
}
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
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=SCOPES
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
    response = (
        service.files()
        .list(
            q=query,
            fields="files(id,name)",
            pageSize=10,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    folders = response.get("files", [])
    if not folders:
        raise FileNotFoundError(f"Google Driveフォルダが見つかりません: {name}")
    if len(folders) > 1:
        raise RuntimeError(f"同名フォルダが複数あります: {name}")
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
    if folder.get("mimeType") != FOLDER_MIME_TYPE:
        raise RuntimeError(f"Google Drive ID is not a folder: {folder_id}")
    return folder


def resolve_root_folder(
    service, root_folder_name: str, root_folder_id: str | None = None
) -> dict:
    if root_folder_id:
        return get_folder_by_id(service, root_folder_id)
    return find_single_folder(service, root_folder_name)


def find_optional_file(service, name: str, parent_id: str) -> dict | None:
    safe_name = quote_drive_query(name)
    safe_parent = quote_drive_query(parent_id)
    query = f"name = '{safe_name}' and '{safe_parent}' in parents and trashed = false"
    response = (
        service.files()
        .list(
            q=query,
            fields="files(id,name,mimeType,size)",
            pageSize=2,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
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
        response = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken,files(id,name,mimeType,size)",
                pageSize=100,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                orderBy="name",
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return files


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def drive_source_path(*parts: str) -> str:
    return "/".join(part.strip("/") for part in parts if part)


def is_background_image_file(item: dict) -> bool:
    """Return True for supported incoming background image filenames."""
    name = item.get("name", "").lower()
    if name not in BACKGROUND_IMAGE_NAMES:
        return False
    return item.get("mimeType") in IMAGE_MIME_TYPES or name.endswith(
        (".png", ".jpg", ".jpeg")
    )


def background_image_destination(output_dir: Path, drive_name: str) -> Path:
    """Normalize supported image names to generator-compatible destinations."""
    suffix = Path(drive_name).suffix.lower()
    normalized_suffix = ".png" if suffix == ".png" else ".jpg"
    return output_dir / f"background{normalized_suffix}"


def remove_stale_background_assets(output_dir: Path) -> None:
    """Remove prior background files so a failed/missing download cannot be masked."""
    for pattern in ("background.*", BACKGROUND_LOOP_NAME):
        for stale in output_dir.glob(pattern):
            if stale.is_file():
                stale.unlink()
                print(
                    f"Removed stale background asset before download: {stale.as_posix()}"
                )


def log_drive_download(
    file_record: dict, destination: Path, source_path: str | None = None
) -> None:
    drive_name = file_record.get("name", "<unknown>")
    drive_id = file_record.get("id", "<unknown>")
    source = source_path or drive_name
    sha256 = file_sha256(destination) if destination.exists() else "<missing>"
    print(
        "Downloaded from Google Drive: "
        f"source_name={drive_name} file_id={drive_id} "
        f"source_path={source} destination={destination.as_posix()} sha256={sha256}"
    )


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def write_background_manifest(
    file_record: dict, destination: Path, source_path: str
) -> None:
    manifest = destination.parent / "background_manifest.env"
    values = {
        "BACKGROUND_SOURCE_NAME": file_record.get("name", "<unknown>"),
        "BACKGROUND_DRIVE_FILE_ID": file_record.get("id", "<unknown>"),
        "BACKGROUND_SOURCE_PATH": source_path,
        "BACKGROUND_DESTINATION_PATH": destination.as_posix(),
        "BACKGROUND_SHA256": file_sha256(destination),
    }
    manifest.write_text(
        "".join(f"{key}={shell_quote(value)}\n" for key, value in values.items()),
        encoding="utf-8",
    )
    print(f"Wrote background manifest: {manifest.as_posix()}")


def download_file(service, file_id: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    with destination.open("wb") as handle:
        downloader = MediaIoBaseDownload(handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def download_legacy_video_folder(
    service, video_number: str, output_dir: Path, root_folder_id: str | None = None
) -> None:
    remove_stale_background_assets(output_dir)
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
            raise FileNotFoundError(
                f"必須トラックが見つかりません: {video_folder_name}/tracks/{filename}"
            )
        destination = tracks_dir / filename
        download_file(service, file_record["id"], destination)
        log_drive_download(
            file_record,
            destination,
            drive_source_path(
                ROOT_FOLDER, "Videos", video_folder_name, "tracks", filename
            ),
        )

    background_loop = find_optional_file(
        service, BACKGROUND_LOOP_NAME, video["id"]
    ) or find_optional_file(service, BACKGROUND_LOOP_NAME, videos["id"])
    background_png = find_optional_file(
        service, "background.png", video["id"]
    ) or find_optional_file(service, "background.png", videos["id"])
    if background_loop:
        destination = output_dir / BACKGROUND_LOOP_NAME
        download_file(service, background_loop["id"], destination)
        source_path = drive_source_path(
            ROOT_FOLDER, "Videos", video_folder_name, background_loop["name"]
        )
        log_drive_download(background_loop, destination, source_path)
        write_background_manifest(background_loop, destination, source_path)
    elif background_png:
        destination = output_dir / "background.png"
        download_file(service, background_png["id"], destination)
        source_path = drive_source_path(
            ROOT_FOLDER, "Videos", video_folder_name, background_png["name"]
        )
        log_drive_download(background_png, destination, source_path)
        write_background_manifest(background_png, destination, source_path)
    else:
        raise FileNotFoundError("background_loop.mp4 または background画像が必要です")

    for filename in ("rain.mp3", "rain_overlay.mp4"):
        file_record = find_optional_file(
            service, filename, video["id"]
        ) or find_optional_file(service, filename, videos["id"])
        if file_record:
            destination = output_dir / filename
            download_file(service, file_record["id"], destination)
            log_drive_download(
                file_record,
                destination,
                drive_source_path(
                    ROOT_FOLDER, "Videos", video_folder_name, file_record["name"]
                ),
            )
        else:
            print(f"Optional {filename} not found; continuing without it")


def download_incoming_work_folder(service, folder_id: str, output_dir: Path) -> None:
    remove_stale_background_assets(output_dir)
    tracks_dir = output_dir / "tracks"
    children = list_files(service, folder_id)
    mp3_files = [item for item in children if item["name"].lower().endswith(".mp3")]
    background_loop_files = [
        item for item in children if item["name"].lower() == BACKGROUND_LOOP_NAME
    ]
    image_files = [item for item in children if is_background_image_file(item)]
    if len(background_loop_files) > 1:
        raise FileNotFoundError(
            f"background_loop.mp4 は1つだけ必要です。検出数: {len(background_loop_files)}"
        )
    if len(image_files) > 1:
        raise FileNotFoundError(
            f"background画像は1枚だけ必要です。検出数: {len(image_files)}"
        )
    if not background_loop_files and not image_files:
        raise FileNotFoundError("background_loop.mp4 または background画像が必要です")
    if len(mp3_files) < 1:
        raise FileNotFoundError(
            "mp3音源が見つかりません。理想は20曲、最低1曲以上が必要です。"
        )
    if len(mp3_files) < 20:
        print(f"Warning: mp3音源は{len(mp3_files)}曲です。理想は20曲です。")

    if background_loop_files:
        background_loop = background_loop_files[0]
        destination = output_dir / BACKGROUND_LOOP_NAME
        download_file(service, background_loop["id"], destination)
        source_path = drive_source_path(f"folder:{folder_id}", background_loop["name"])
        log_drive_download(background_loop, destination, source_path)
        write_background_manifest(background_loop, destination, source_path)
    else:
        background = image_files[0]
        destination = background_image_destination(output_dir, background["name"])
        print(
            "Selected incoming background image: "
            f"source_name={background['name']} file_id={background['id']} "
            f"destination={destination.as_posix()}"
        )
        download_file(service, background["id"], destination)
        source_path = drive_source_path(f"folder:{folder_id}", background["name"])
        log_drive_download(background, destination, source_path)
        write_background_manifest(background, destination, source_path)

    for index, item in enumerate(mp3_files[:20], start=1):
        destination = tracks_dir / f"track{index:02d}.mp3"
        download_file(service, item["id"], destination)
        log_drive_download(
            item, destination, drive_source_path(f"folder:{folder_id}", item["name"])
        )

    if len(mp3_files) < 20:
        for index in range(len(mp3_files) + 1, 21):
            source = tracks_dir / f"track{((index - 1) % len(mp3_files)) + 1:02d}.mp3"
            destination = tracks_dir / f"track{index:02d}.mp3"
            destination.write_bytes(source.read_bytes())
            print(
                f"Duplicated {source.name} as {destination.name} to keep generator input compatible"
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--video-number", default="001", help="video_XXX の番号。例: 001"
    )
    parser.add_argument(
        "--drive-folder-id",
        help="incoming内の作品フォルダID。指定時はこのフォルダから直接取得します。",
    )
    parser.add_argument(
        "--root-folder-id",
        default=os.environ.get(ROOT_FOLDER_ID_ENV),
        help=f"DriveルートフォルダID（{ROOT_FOLDER_ID_ENV} が指定されていればID優先）",
    )
    parser.add_argument(
        "--output-dir", default="video_assets", help="ダウンロード先ディレクトリ"
    )
    args = parser.parse_args()

    service = get_drive_service()
    output_dir = Path(args.output_dir)
    if args.drive_folder_id:
        download_incoming_work_folder(service, args.drive_folder_id, output_dir)
    else:
        download_legacy_video_folder(
            service, args.video_number, output_dir, args.root_folder_id
        )


if __name__ == "__main__":
    main()
