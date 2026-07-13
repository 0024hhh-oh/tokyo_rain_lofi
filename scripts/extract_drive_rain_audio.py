#!/usr/bin/env python3
"""Extract the audio track from a CapCut MP4 stored in Google Drive."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_MIME = "application/vnd.google-apps.folder"
ROOT_FOLDER = "Tokyo ChillMatic FM"
ROOT_FOLDER_ID_ENV = "TOKYO_CHILLMATIC_DRIVE_FOLDER_ID"
SOURCE_FOLDER = "audio_source"
SOURCE_FILE = "rain_audio_source.mp4"
OUTPUT_FILE = "rain.m4a"


def quote_drive_query(value: str) -> str:
    return value.replace("'", "\\'")


def get_drive_service():
    info_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not info_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is required")
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(info_json), scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def list_files(service, query: str) -> list[dict]:
    response = (
        service.files()
        .list(
            q=query,
            fields="files(id,name,mimeType,size,parents)",
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    return response.get("files", [])


def get_root_folder(service) -> dict:
    root_id = os.environ.get(ROOT_FOLDER_ID_ENV)
    if root_id:
        folder = (
            service.files()
            .get(
                fileId=root_id,
                fields="id,name,mimeType",
                supportsAllDrives=True,
            )
            .execute()
        )
        if folder.get("mimeType") != FOLDER_MIME:
            raise RuntimeError(f"Configured Drive root is not a folder: {root_id}")
        return folder

    folders = list_files(
        service,
        f"mimeType = '{FOLDER_MIME}' and name = '{quote_drive_query(ROOT_FOLDER)}' "
        "and trashed = false",
    )
    if len(folders) != 1:
        raise RuntimeError(
            f"Expected exactly one Drive root named {ROOT_FOLDER}; found {len(folders)}"
        )
    return folders[0]


def find_source_folder(service, root_id: str) -> dict:
    folders = list_files(
        service,
        f"mimeType = '{FOLDER_MIME}' and name = '{quote_drive_query(SOURCE_FOLDER)}' "
        f"and '{quote_drive_query(root_id)}' in parents and trashed = false",
    )
    if len(folders) == 1:
        return folders[0]
    if len(folders) > 1:
        raise RuntimeError(
            f"Multiple {SOURCE_FOLDER} folders exist under {ROOT_FOLDER}"
        )

    # Compatibility fallback if audio_source was shared separately instead of
    # being created under the configured Tokyo ChillMatic FM folder.
    folders = list_files(
        service,
        f"mimeType = '{FOLDER_MIME}' and name = '{quote_drive_query(SOURCE_FOLDER)}' "
        "and trashed = false",
    )
    if len(folders) != 1:
        raise RuntimeError(
            f"Expected one accessible Drive folder named {SOURCE_FOLDER}; "
            f"found {len(folders)}"
        )
    return folders[0]


def find_exact_file(service, parent_id: str, name: str) -> dict | None:
    files = list_files(
        service,
        f"name = '{quote_drive_query(name)}' "
        f"and '{quote_drive_query(parent_id)}' in parents and trashed = false",
    )
    if len(files) > 1:
        raise RuntimeError(f"Multiple files named {name} exist in {SOURCE_FOLDER}")
    return files[0] if files else None


def download_file(service, file_id: str, destination: Path) -> None:
    request = service.files().get_media(
        fileId=file_id,
        supportsAllDrives=True,
    )
    with destination.open("wb") as handle:
        downloader = MediaIoBaseDownload(handle, request, chunksize=8 * 1024 * 1024)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"Download progress: {status.progress() * 100:.1f}%")


def probe(path: Path, *entries: str) -> str:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            ",".join(entries),
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def main() -> None:
    service = get_drive_service()
    root = get_root_folder(service)
    source_folder = find_source_folder(service, root["id"])
    print(
        f"Drive source folder: name={source_folder['name']} id={source_folder['id']}"
    )

    existing = find_exact_file(service, source_folder["id"], OUTPUT_FILE)
    if existing:
        print(
            f"{OUTPUT_FILE} already exists; skipping extraction: "
            f"id={existing['id']} size={existing.get('size', '<unknown>')}"
        )
        return

    source = find_exact_file(service, source_folder["id"], SOURCE_FILE)
    if not source:
        children = list_files(
            service,
            f"'{quote_drive_query(source_folder['id'])}' in parents and trashed = false",
        )
        names = ", ".join(item["name"] for item in children) or "<empty>"
        raise FileNotFoundError(
            f"Missing {SOURCE_FILE} in {SOURCE_FOLDER}. Current items: {names}"
        )

    print(
        f"Drive source file: name={source['name']} id={source['id']} "
        f"size={source.get('size', '<unknown>')}"
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        source_path = Path(temp_dir) / SOURCE_FILE
        output_path = Path(temp_dir) / OUTPUT_FILE
        download_file(service, source["id"], source_path)

        codec = probe(source_path, "stream=codec_name").splitlines()[0]
        source_duration = float(probe(source_path, "format=duration"))
        if source_duration <= 0:
            raise RuntimeError(f"Source duration is not positive: {source_duration}")

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-map",
            "0:a:0",
            "-vn",
        ]
        if codec == "aac":
            command.extend(["-c:a", "copy"])
            mode = "stream-copy"
        else:
            command.extend(["-c:a", "aac", "-b:a", "192k", "-ar", "48000"])
            mode = "aac-encode"
        command.append(str(output_path))

        print(f"Audio extraction mode: {mode}; source codec={codec}")
        subprocess.run(command, check=True)

        if not output_path.is_file() or output_path.stat().st_size <= 0:
            raise RuntimeError(f"Audio output was not created: {output_path}")
        output_duration = float(probe(output_path, "format=duration"))
        if output_duration <= 0:
            raise RuntimeError(f"Output duration is not positive: {output_duration}")

        print(
            f"Validated audio: duration={output_duration:.3f}s "
            f"size={output_path.stat().st_size}"
        )
        media = MediaFileUpload(
            str(output_path),
            mimetype="audio/mp4",
            resumable=True,
            chunksize=8 * 1024 * 1024,
        )
        uploaded = (
            service.files()
            .create(
                body={"name": OUTPUT_FILE, "parents": [source_folder["id"]]},
                media_body=media,
                fields="id,name,size,mimeType",
                supportsAllDrives=True,
            )
            .execute()
        )
        print(
            f"Uploaded Drive audio: name={uploaded['name']} id={uploaded['id']} "
            f"size={uploaded.get('size', '<unknown>')}"
        )


if __name__ == "__main__":
    main()
