#!/usr/bin/env python3
"""Create a personal Google Drive refresh token for GitHub Actions."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request


AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
REDIRECT_URI = "http://localhost/"


def ask(label: str) -> str:
    return input(f"{label}: ").strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Get a personal Google Drive OAuth refresh token")
    parser.add_argument("--client-id")
    parser.add_argument("--client-secret")
    parser.add_argument("--code")
    args = parser.parse_args()

    client_id = args.client_id or ask("GOOGLE_DRIVE_CLIENT_ID (the existing YouTube OAuth client ID is reusable)")
    client_secret = args.client_secret or ask("GOOGLE_DRIVE_CLIENT_SECRET (the existing YouTube OAuth client secret is reusable)")

    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": DRIVE_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    print("\n1) Open this URL and approve Google Drive access:\n")
    print(f"{AUTH_URL}?{urllib.parse.urlencode(params)}")
    print("\n2) Copy the code parameter from the localhost redirect URL.")
    code = args.code or ask("\nAuthorization code")

    data = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        }
    ).encode()
    request = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    try:
        with urllib.request.urlopen(request) as response:
            result = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        print(exc.read().decode())
        raise

    refresh_token = result.get("refresh_token")
    if not refresh_token:
        print(json.dumps(result, indent=2))
        raise SystemExit("No refresh_token returned. Retry and approve access with prompt=consent.")

    print("\nAdd these GitHub Repository Secrets:\n")
    print(f"GOOGLE_DRIVE_CLIENT_ID={client_id}")
    print(f"GOOGLE_DRIVE_CLIENT_SECRET={client_secret}")
    print(f"GOOGLE_DRIVE_REFRESH_TOKEN={refresh_token}")
    print("TOKYO_CHILLMATIC_DRIVE_OUTPUT_FOLDER_ID=<your completed MP4 folder ID>")


if __name__ == "__main__":
    main()
