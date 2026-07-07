#!/usr/bin/env python3
"""Upload generated LOFI MP4 outputs to a specified Google Drive folder."""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
OUTPUT_FOLDER_ID_ENV = "TOKYO_CHILLMATIC_DRIVE_OUTPUT_FOLDER_ID"
LEGACY_ROOT_FOLDER_ID_ENV = "TOKYO_CHILLMATIC_DRIVE_FOLDER_ID"


def get_drive_service():
    info_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    info_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_PATH")

    if info_json:
        info = json.loads(info_json)
        credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    elif info_path:
        credentials = service_account.Credentials.from_service_account_file(info_path, scopes=SCOPES)
    else:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON または GOOGLE_SERVICE_ACCOUNT_JSON_PATH を設定してください。"
        )

    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def get_folder_by_id(service, folder_id: str) -> dict:
    folder = service.files().get(
        fileId=folder_id,
        fields="id,name,mimeType",
        supportsAllDrives=True,
    ).execute()
    if folder.get("mimeType") != FOLDER_MIME_TYPE:
        raise RuntimeError(f"Google Drive ID is not a folder: {folder_id}")
    return folder


def quote_drive_query(value: str) -> str:
    return value.replace("'", "\\'")


def find_existing_file(service, name: str, parent_id: str) -> dict | None:
    safe_name = quote_drive_query(name)
    safe_parent = quote_drive_query(parent_id)
    query = f"name = '{safe_name}' and '{safe_parent}' in parents and trashed = false"
    response = service.files().list(
        q=query,
        fields="files(id,name,mimeType,size)",
        pageSize=10,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    files = response.get("files", [])
    if len(files) > 1:
        raise RuntimeError(f"同名ファイルが複数あります: {name}")
    return files[0] if files else None


def upload_output(service, source_path: Path, output_name: str, parent_id: str) -> dict:
    media = MediaFileUpload(str(source_path), mimetype="video/mp4", resumable=True)
    existing_file = find_existing_file(service, output_name, parent_id)

    if existing_file:
        print(f"Updating existing Drive file: file_id={existing_file['id']} file_name={output_name} folder_id={parent_id}")
        return service.files().update(
            fileId=existing_file["id"],
            media_body=media,
            body={"name": output_name},
            fields="id,name,webViewLink,parents",
            supportsAllDrives=True,
        ).execute()

    metadata = {"name": output_name, "parents": [parent_id]}
    print(f"Creating new Drive file: file_name={output_name} folder_id={parent_id}")
    return service.files().create(
        body=metadata,
        media_body=media,
        fields="id,name,webViewLink,parents",
        supportsAllDrives=True,
    ).execute()


def resolve_output_folder_id(args: argparse.Namespace) -> str:
    folder_id = args.output_folder_id or os.environ.get(OUTPUT_FOLDER_ID_ENV)
    if folder_id:
        return folder_id
    legacy = os.environ.get(LEGACY_ROOT_FOLDER_ID_ENV)
    if legacy:
        raise RuntimeError(
            f"出力先フォルダIDが未指定です。{OUTPUT_FOLDER_ID_ENV} または --output-folder-id に、"
            f"MP4保存先のGoogle DriveフォルダIDを指定してください（{LEGACY_ROOT_FOLDER_ID_ENV} はルート用です）。"
        )
    raise RuntimeError(f"{OUTPUT_FOLDER_ID_ENV} または --output-folder-id を設定してください。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="アップロードするMP4ファイルパス")
    parser.add_argument("--output-name", required=True, help="Google Drive上の保存ファイル名")
    parser.add_argument("--output-folder-id", default="", help=f"MP4保存先DriveフォルダID（{OUTPUT_FOLDER_ID_ENV} でも指定可）")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        source_path = Path(args.file)
        if not source_path.is_file():
            raise FileNotFoundError(f"アップロード対象MP4が見つかりません: {source_path}")

        output_folder_id = resolve_output_folder_id(args)
        service = get_drive_service()
        folder = get_folder_by_id(service, output_folder_id)
        uploaded = upload_output(service, source_path, args.output_name, folder["id"])

        print(
            "Google Drive upload completed: "
            f"file_id={uploaded['id']} file_name={uploaded['name']} folder_id={folder['id']}"
        )
        if uploaded.get("webViewLink"):
            print(f"Drive URL: {uploaded['webViewLink']}")
    except Exception as exc:
        print("Google Drive upload failed.", file=sys.stderr)
        print(f"Error type: {type(exc).__name__}", file=sys.stderr)
        print(f"Error detail: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
