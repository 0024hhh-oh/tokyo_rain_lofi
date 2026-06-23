#!/usr/bin/env python3
"""Upload generated LOFI MP4 outputs to Google Drive for GitHub Actions."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


def quote_drive_query(value: str) -> str:
    return value.replace("'", "\\'")


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


def find_single_folder(service, name: str, parent_id: str | None = None) -> dict:
    safe_name = quote_drive_query(name)
    query = f"mimeType = '{FOLDER_MIME_TYPE}' and name = '{safe_name}' and trashed = false"
    if parent_id:
        safe_parent = quote_drive_query(parent_id)
        query += f" and '{safe_parent}' in parents"

    response = service.files().list(
        q=query,
        fields="files(id,name)",
        pageSize=10,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    folders = response.get("files", [])
    if not folders:
        raise FileNotFoundError(f"Google Driveフォルダが見つかりません: {name}")
    if len(folders) > 1:
        raise RuntimeError(f"同名フォルダが複数あります: {name}")
    return folders[0]


def find_or_create_folder(service, name: str, parent_id: str) -> dict:
    safe_name = quote_drive_query(name)
    safe_parent = quote_drive_query(parent_id)
    query = (
        f"mimeType = '{FOLDER_MIME_TYPE}' "
        f"and name = '{safe_name}' "
        f"and '{safe_parent}' in parents "
        "and trashed = false"
    )
    response = service.files().list(
        q=query,
        fields="files(id,name)",
        pageSize=10,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    folders = response.get("files", [])
    if len(folders) > 1:
        raise RuntimeError(f"同名フォルダが複数あります: {name}")
    if folders:
        return folders[0]

    metadata = {
        "name": name,
        "mimeType": FOLDER_MIME_TYPE,
        "parents": [parent_id],
    }
    return service.files().create(
        body=metadata,
        fields="id,name",
        supportsAllDrives=True,
    ).execute()


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
        print(f"Updating existing Drive file: {output_name} ({existing_file['id']})")
        return service.files().update(
            fileId=existing_file["id"],
            media_body=media,
            body={"name": output_name},
            fields="id,name,webViewLink",
            supportsAllDrives=True,
        ).execute()

    metadata = {
        "name": output_name,
        "parents": [parent_id],
    }
    print(f"Creating new Drive file: {output_name}")
    return service.files().create(
        body=metadata,
        media_body=media,
        fields="id,name,webViewLink",
        supportsAllDrives=True,
    ).execute()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="アップロードするMP4ファイルパス")
    parser.add_argument("--output-name", required=True, help="Google Drive上の保存ファイル名")
    parser.add_argument("--root-folder", default="Tokyo ChillMatic FM", help="Driveルートフォルダ名")
    parser.add_argument("--output-folder", default="Outputs", help="出力先フォルダ名")
    args = parser.parse_args()

    source_path = Path(args.file)
    if not source_path.is_file():
        raise FileNotFoundError(f"アップロード対象MP4が見つかりません: {source_path}")

    service = get_drive_service()
    root = find_single_folder(service, args.root_folder)
    outputs = find_or_create_folder(service, args.output_folder, root["id"])
    uploaded = upload_output(service, source_path, args.output_name, outputs["id"])

    print(f"Uploaded to Google Drive: {uploaded['name']}")
    if uploaded.get("webViewLink"):
        print(f"Drive URL: {uploaded['webViewLink']}")


if __name__ == "__main__":
    main()
