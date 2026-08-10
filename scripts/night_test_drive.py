#!/usr/bin/env python3
"""Detect and download the isolated Google Drive Remotion night test."""

from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_MIME = "application/vnd.google-apps.folder"
ROOT_FOLDER = "Tokyo ChillMatic FM"
ROOT_FOLDER_ID_ENV = "TOKYO_CHILLMATIC_DRIVE_FOLDER_ID"
PROJECTS_FOLDER = "Projects"
NIGHT_TEST_FOLDER = "night-test"
OUTPUT_FOLDER = "output"
OUTPUT_FILE = "video.mp4"
PROJECT_FILE = "project.json"
IMAGE_NAMES = {"background.png", "background.jpg", "background.jpeg"}


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


def list_children(service, parent_id: str) -> list[dict]:
    query = f"'{quote_drive_query(parent_id)}' in parents and trashed = false"
    response = (
        service.files()
        .list(
            q=query,
            fields="files(id,name,mimeType,size,parents,appProperties)",
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    return response.get("files", [])


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


def find_named_folder(service, parent_id: str | None, name: str) -> dict:
    query = (
        f"mimeType = '{FOLDER_MIME}' and "
        f"name = '{quote_drive_query(name)}' and trashed = false"
    )
    if parent_id:
        query += f" and '{quote_drive_query(parent_id)}' in parents"
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
        raise RuntimeError(f"Google Drive folder {name} count is {len(folders)}; expected 1")
    return folders[0]


def resolve_root(service, root_folder_id: str | None) -> dict:
    if root_folder_id:
        return get_folder_by_id(service, root_folder_id)
    return find_named_folder(service, None, ROOT_FOLDER)


def find_casefold_folder(items: list[dict], name: str) -> dict | None:
    matches = [
        item
        for item in items
        if item.get("mimeType") == FOLDER_MIME
        and item.get("name", "").strip().casefold() == name.casefold()
    ]
    if len(matches) > 1:
        raise RuntimeError(f"Google Drive folder {name} is duplicated")
    return matches[0] if matches else None


def inspect_night_test(items: list[dict]) -> tuple[bool, str, dict | None]:
    files = [item for item in items if item.get("mimeType") != FOLDER_MIME]
    folders = [item for item in items if item.get("mimeType") == FOLDER_MIME]
    images = [item for item in files if item.get("name", "").casefold() in IMAGE_NAMES]
    mp3s = [item for item in files if item.get("name", "").casefold().endswith(".mp3")]
    project_files = [
        item for item in files if item.get("name", "").casefold() == PROJECT_FILE
    ]
    output_folders = [
        item
        for item in folders
        if item.get("name", "").strip().casefold() == OUTPUT_FOLDER
    ]

    print(
        "night-test input validation: "
        f"background={len(images)} mp3={len(mp3s)} "
        f"project_json={len(project_files)} output_folder={len(output_folders)}"
    )
    if len(images) != 1:
        return False, f"background image count must be 1; found {len(images)}", None
    if len(mp3s) != 1:
        return False, f"MP3 count must be 1; found {len(mp3s)}", None
    if len(project_files) != 1:
        return False, f"project.json count must be 1; found {len(project_files)}", None
    if len(output_folders) > 1:
        return False, "output folder is duplicated", None
    return True, "night-test input is ready", output_folders[0] if output_folders else None


def write_github_output(values: dict[str, str]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        for key, value in values.items():
            print(f"{key}={value}")
        return
    with Path(output_path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def resolve_night_test(service, args: argparse.Namespace) -> tuple[dict | None, list[dict]]:
    root = resolve_root(service, args.root_folder_id)
    projects = find_named_folder(service, root["id"], args.projects_folder)
    night_test = find_casefold_folder(list_children(service, projects["id"]), args.night_test_folder)
    if not night_test:
        return None, []
    return night_test, list_children(service, night_test["id"])


def detect(args: argparse.Namespace) -> None:
    print("night-test stage=detect")
    service = get_drive_service()
    night_test, items = resolve_night_test(service, args)
    if not night_test:
        print("night-test skipped: Projects/night-test was not found")
        write_github_output({"found": "false", "reason": "folder-not-found"})
        return

    ok, reason, output_folder = inspect_night_test(items)
    if not ok:
        print(f"night-test skipped: {reason}")
        write_github_output({"found": "false", "reason": "input-validation"})
        return

    if output_folder:
        outputs = list_children(service, output_folder["id"])
        completed = [
            item
            for item in outputs
            if item.get("mimeType") != FOLDER_MIME
            and item.get("name", "").casefold() == OUTPUT_FILE
        ]
        if completed:
            print("night-test skipped: output/video.mp4 already exists")
            write_github_output({"found": "false", "reason": "already-completed"})
            return

    print(f"night-test selected: folder_id={night_test['id']}")
    write_github_output(
        {
            "found": "true",
            "folder_id": night_test["id"],
            "output_folder_id": output_folder["id"] if output_folder else "",
            "reason": "ready",
        }
    )


def download_file(service, file_id: str, destination: Path) -> None:
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    with io.FileIO(destination, "wb") as handle:
        downloader = MediaIoBaseDownload(handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def download(args: argparse.Namespace) -> None:
    print("night-test stage=input-download")
    service = get_drive_service()
    folder = get_folder_by_id(service, args.folder_id)
    items = list_children(service, folder["id"])
    ok, reason, _ = inspect_night_test(items)
    if not ok:
        raise RuntimeError(f"night-test input validation failed: {reason}")
    image = next(item for item in items if item.get("name", "").casefold() in IMAGE_NAMES)
    track = next(
        item for item in items if item.get("name", "").casefold().endswith(".mp3")
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(image["name"]).suffix.casefold()
    destination = output_dir / ("background.png" if suffix == ".png" else "background.jpg")
    download_file(service, image["id"], destination)
    if not destination.is_file() or destination.stat().st_size == 0:
        raise RuntimeError("night-test background download produced an empty file")
    print(f"night-test background downloaded: {destination}")

    track_dir = output_dir / "tracks"
    track_dir.mkdir(parents=True, exist_ok=True)
    track_destination = track_dir / "night-test.mp3"
    download_file(service, track["id"], track_destination)
    if not track_destination.is_file() or track_destination.stat().st_size == 0:
        raise RuntimeError("night-test MP3 download produced an empty file")
    print(f"night-test MP3 downloaded: {track_destination}")


def ensure_output(args: argparse.Namespace) -> None:
    print("night-test stage=output-folder")
    service = get_drive_service()
    parent = get_folder_by_id(service, args.folder_id)
    output = find_casefold_folder(list_children(service, parent["id"]), OUTPUT_FOLDER)
    if not output:
        output = (
            service.files()
            .create(
                body={
                    "name": OUTPUT_FOLDER,
                    "mimeType": FOLDER_MIME,
                    "parents": [parent["id"]],
                },
                fields="id,name,mimeType",
                supportsAllDrives=True,
            )
            .execute()
        )
        print(f"night-test output folder created: folder_id={output['id']}")
    else:
        print(f"night-test output folder reused: folder_id={output['id']}")
    write_github_output({"output_folder_id": output["id"]})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("detect", "download", "ensure-output"))
    parser.add_argument("--root-folder-id", default=os.environ.get(ROOT_FOLDER_ID_ENV))
    parser.add_argument("--projects-folder", default=PROJECTS_FOLDER)
    parser.add_argument("--night-test-folder", default=NIGHT_TEST_FOLDER)
    parser.add_argument("--folder-id", default="")
    parser.add_argument("--output-dir", default="video_assets")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "detect":
        detect(args)
    elif args.command == "download":
        if not args.folder_id:
            raise RuntimeError("--folder-id is required for download")
        download(args)
    else:
        if not args.folder_id:
            raise RuntimeError("--folder-id is required for ensure-output")
        ensure_output(args)


if __name__ == "__main__":
    main()
