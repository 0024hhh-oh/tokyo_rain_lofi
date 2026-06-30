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
ROOT_FOLDER = "TokyoChillMatic"
FOLDER_MIME = "application/vnd.google-apps.folder"
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")


def quote_drive_query(value: str) -> str:
    return value.replace("'", "\\'")


def get_drive_service():
    info_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    info_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_PATH")
    if info_json:
        credentials = service_account.Credentials.from_service_account_info(json.loads(info_json), scopes=SCOPES)
    elif info_path:
        credentials = service_account.Credentials.from_service_account_file(info_path, scopes=SCOPES)
    else:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON または GOOGLE_SERVICE_ACCOUNT_JSON_PATH を設定してください。")
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def list_files(service, query: str, fields: str = "files(id,name,mimeType,createdTime,modifiedTime,parents)") -> list[dict]:
    results: list[dict] = []
    page_token = None
    while True:
        response = service.files().list(
            q=query,
            fields=f"nextPageToken,{fields}",
            orderBy="createdTime",
            pageSize=100,
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
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
        raise RuntimeError(f"Google Driveフォルダ {name} の検出数が不正です: {len(folders)}")
    return folders[0]


def ensure_child_folder(service, parent_id: str, name: str) -> dict:
    query = f"mimeType = '{FOLDER_MIME}' and name = '{quote_drive_query(name)}' and '{quote_drive_query(parent_id)}' in parents and trashed = false"
    folders = list_files(service, query, fields="files(id,name)")
    if folders:
        return folders[0]
    return service.files().create(
        body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]},
        fields="id,name",
        supportsAllDrives=True,
    ).execute()


def validate_work_folder(service, folder_id: str) -> tuple[bool, str, int]:
    children = list_files(service, f"'{quote_drive_query(folder_id)}' in parents and trashed = false", fields="files(id,name,mimeType)")
    backgrounds = [item for item in children if item["name"].lower().startswith("background.") and item["name"].lower().endswith(IMAGE_EXTENSIONS)]
    mp3s = [item for item in children if item["name"].lower().endswith(".mp3")]
    if len(backgrounds) != 1:
        return False, f"background画像は1枚だけ必要です（検出数: {len(backgrounds)}）", len(mp3s)
    if len(mp3s) < 1:
        return False, "mp3音源がありません（理想は20曲）", 0
    if len(mp3s) < 20:
        return True, f"mp3音源は{len(mp3s)}曲です（理想は20曲）。不足分は生成前に複製して互換性を保ちます。", len(mp3s)
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
    root = find_single_folder(service, args.root_folder)
    incoming = ensure_child_folder(service, root["id"], args.incoming_folder)
    ensure_child_folder(service, root["id"], args.processed_folder)
    ensure_child_folder(service, root["id"], args.failed_folder)
    query = f"mimeType = '{FOLDER_MIME}' and '{quote_drive_query(incoming['id'])}' in parents and trashed = false"
    for folder in list_files(service, query):
        ok, message, track_count = validate_work_folder(service, folder["id"])
        print(f"検査: {folder['name']} - {message}")
        if not ok:
            continue
        stem = safe_file_stem(folder["name"])
        write_github_output({
            "found": "true",
            "work_folder_id": folder["id"],
            "work_folder_name": folder["name"],
            "track_count": str(track_count),
            "output_file": f"{stem}.mp4",
            "youtube_title": folder["name"].replace("_", " "),
        })
        return
    write_github_output({"found": "false"})


def move(args: argparse.Namespace) -> None:
    if not args.folder_id:
        raise RuntimeError("--folder-id is required for move")
    service = get_drive_service()
    root = find_single_folder(service, args.root_folder)
    destination = ensure_child_folder(service, root["id"], args.destination)
    file_record = service.files().get(fileId=args.folder_id, fields="id,name,parents", supportsAllDrives=True).execute()
    previous_parents = ",".join(file_record.get("parents", []))
    body = {"description": f"TokyoChillMatic automation moved to {args.destination} at {datetime.now(timezone.utc).isoformat()}"}
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
